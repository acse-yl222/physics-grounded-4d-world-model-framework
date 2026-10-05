"""img2city/webapp/jobs.py -- background job runner for the web app.

Two-phase make_city flow, mirroring the CLI contract:
  phase "quote":  img2city.city.make_city --bbox --out          (free stages + token quote)
  phase "run":    img2city.city.make_city --bbox --out --yes    (paid stages; needs live
                  Blender+BlenderMCP on :9876 for assembly -- auto-launched)
plus single-purpose jobs (photo agent refine) on the same table.

Jobs persist to cache/jobs/<id>.json so a server restart keeps the history:
a job whose process is still alive is re-adopted (pid watcher); a dead one is
repaired from disk artifacts (report -> done, parsable quote ->
awaiting_confirm, otherwise interrupted).  make_city is resumable, so an
interrupted/failed generate job can be resumed (run --yes again).
"""
import json
import os
import re
import shlex
import socket
import subprocess
import threading
import time
import uuid

from img2city import config
from img2city.webapp import areas

JOBS_DIR = areas.CACHE / "jobs"
BLENDER_LAUNCH = [areas.BLENDER, "--python-expr",
                  "import bpy; bpy.ops.preferences.addon_enable(module='addon'); "
                  "bpy.ops.blendermcp.start_server()"]

_jobs = {}
_guard = threading.Lock()


def blender_alive():
    try:
        s = socket.create_connection((config.MCP_HOST, config.MCP_PORT), timeout=1.5)
        s.close()
        return True
    except OSError:
        return False


def launch_blender(wait=90):
    """Start GUI Blender with the MCP server and wait for :9876."""
    if blender_alive():
        return True
    subprocess.Popen(BLENDER_LAUNCH, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)
    t0 = time.time()
    while time.time() - t0 < wait:
        if blender_alive():
            return True
        time.sleep(2)
    return False


def _pid_alive(pid):
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


# the token figure is printed to two decimals: a cheap --skip-refine run is
# 0.70M, and an integer format would round it to "1M" or, worse, "0M"
QUOTE_RX = (r"\[make-city\] scope: (\d+) buildings; (\d+) specs to\s*"
            r"write; paid stages ~(\d+(?:\.\d+)?)M tokens")


class Job:
    def __init__(self, kind, area, bbox=None, meta=None, jid=None):
        self.id = jid or uuid.uuid4().hex[:10]
        self.kind = kind          # "generate" | "refine_photo" | ...
        self.area = area
        self.bbox = bbox
        self.meta = meta or {}
        # created|quoting|awaiting_confirm|running|done|failed|cancelled|interrupted
        self.status = "created"
        self.quote = None
        self.error = None
        self.created = time.time()
        self.proc = None
        self.pid = None
        JOBS_DIR.mkdir(parents=True, exist_ok=True)
        self.log_path = JOBS_DIR / f"{self.id}.log"

    # ---- persistence ------------------------------------------------------
    def _save(self):
        doc = {"id": self.id, "kind": self.kind, "area": self.area,
               "bbox": self.bbox, "meta": self.meta, "status": self.status,
               "quote": self.quote, "error": self.error,
               "created": self.created, "pid": self.pid}
        (JOBS_DIR / f"{self.id}.json").write_text(json.dumps(doc))

    # ---- process handling -------------------------------------------------
    def _run(self, cmd, on_exit, caffeinate=False, env_extra=None):
        if caffeinate:
            cmd = ["caffeinate", "-i"] + cmd
        env = dict(os.environ)
        if env_extra:
            env.update(env_extra)
        logf = open(self.log_path, "a")
        logf.write(f"\n$ {shlex.join(cmd)}\n")
        logf.flush()
        self.proc = subprocess.Popen(cmd, stdout=logf, stderr=subprocess.STDOUT,
                                     cwd=str(areas.HARNESS),
                                     env=config.subprocess_env(env),
                                     start_new_session=True)
        self.pid = self.proc.pid
        self._save()

        def waiter():
            rc = self.proc.wait()
            logf.close()
            on_exit(rc)
            self._save()
        threading.Thread(target=waiter, daemon=True).start()

    def cancel(self):
        if self.proc and self.proc.poll() is None:
            try:
                os.killpg(os.getpgid(self.proc.pid), 15)
            except Exception:
                self.proc.terminate()
        elif _pid_alive(self.pid):        # adopted after a server restart
            try:
                os.killpg(os.getpgid(self.pid), 15)
            except Exception:
                pass
        self.status = "cancelled"
        self._save()

    # ---- generate flow ----------------------------------------------------
    def start_quote(self):
        self.status = "quoting"
        self._save()
        out = str(areas.DATA / self.area)
        bbox_s = ",".join(f"{v:.6f}" for v in self.bbox)
        # with a live Blender the free pass also assembles an LoD1 white-box
        # preview; without one, skip export so the quote ends cleanly
        skip = [] if blender_alive() else ["--skip-export"]

        def done(rc):
            if self.status == "cancelled":
                return
            text = self.log_path.read_text(errors="ignore")
            m = re.search(QUOTE_RX, text)
            if rc != 0 and "REFUSING" in text:
                self.status = "failed"
                self.error = "stale-dir: directory already covers a different bbox"
                return
            if m:
                self.quote = {"buildings": int(m.group(1)),
                              "specs_todo": int(m.group(2)),
                              "tokens_M_upper": float(m.group(3))}
                self.status = "awaiting_confirm"
            elif rc == 0:
                self.quote = {"raw": text[-600:]}
                self.status = "awaiting_confirm"
            else:
                self.status = "failed"
                self.error = f"quote stage exited rc={rc}, see log"
            if self.status == "awaiting_confirm" and \
                    list((areas.DATA / self.area).glob("*_textured.blend")):
                try:
                    areas.ensure_glb(self.area)
                    self.meta["preview"] = True
                except Exception:
                    pass
        self._run(config.module_cmd("city.make_city", "--bbox", bbox_s, "--out", out)
                  + skip + self._refine_flag(), done)

    def _refine_flag(self):
        """Refinement is 500k tokens a building against 50k for the spec, so
        skipping it is the one order-of-magnitude lever on the cost of a run.
        The quote leg has to carry the same flag or it quotes ten times what
        the run will actually spend."""
        return ["--skip-refine"] if self.meta.get("skip_refine") else []

    def confirm_run(self):
        if not launch_blender():
            raise RuntimeError("could not start Blender+BlenderMCP on :9876")
        self.status = "running"
        self.error = None
        self._save()
        out = str(areas.DATA / self.area)
        bbox_s = ",".join(f"{v:.6f}" for v in self.bbox)

        def done(rc):
            if self.status == "cancelled":
                return
            self._finish_generate(rc)
        self._run(config.module_cmd("city.make_city", "--bbox", bbox_s, "--out", out,
                                    "--yes") + self._refine_flag(), done, caffeinate=True)

    def _finish_generate(self, rc):
        # the report must be FRESH: a stale one from an earlier quote pass
        # must not turn a failed run into "done" (bit us 08-20: assembly
        # timed out, rc=1, but the quote-phase report existed)
        report = areas.DATA / self.area / "pipeline_report.json"
        fresh = report.exists() and report.stat().st_mtime > self.created
        if rc == 0 or fresh:
            try:
                areas.ensure_glb(self.area)
                self.status = "done"
            except Exception as e:
                self.status = "done"
                self.error = f"glb export failed after generation: {e}"
        else:
            self.status = "failed"
            self.error = f"make_city exited rc={rc}, see log"

    def resume(self):
        """Re-run the paid leg; make_city's stages are all resumable."""
        if self.kind != "generate":
            raise RuntimeError("only generate jobs can resume")
        if self.status not in ("failed", "cancelled", "interrupted"):
            raise RuntimeError(f"job is {self.status}")
        self.confirm_run()

    # ---- adoption after a server restart ----------------------------------
    def adopt(self):
        """Called on reload for jobs that were quoting/running: re-attach if
        the process survived, otherwise repair the status from disk."""
        if _pid_alive(self.pid):
            def watch():
                while _pid_alive(self.pid):
                    time.sleep(5)
                if self.status == "running":
                    self._finish_generate(rc=-1)
                elif self.status == "quoting":
                    text = self.log_path.read_text(errors="ignore") \
                        if self.log_path.exists() else ""
                    m = re.search(QUOTE_RX, text)
                    if m:
                        self.quote = {"buildings": int(m.group(1)),
                                      "specs_todo": int(m.group(2)),
                                      "tokens_M_upper": float(m.group(3))}
                        self.status = "awaiting_confirm"
                    else:
                        self.status = "interrupted"
                self._save()
            threading.Thread(target=watch, daemon=True).start()
            return
        # process is gone -- repair from artifacts
        if self.status == "running":
            report = areas.DATA / self.area / "pipeline_report.json"
            if report.exists():
                self.status = "done"
            else:
                self.status = "interrupted"
                self.error = "server restarted while the job was running"
        elif self.status == "quoting":
            text = self.log_path.read_text(errors="ignore") \
                if self.log_path.exists() else ""
            m = re.search(QUOTE_RX, text)
            if m:
                self.quote = {"buildings": int(m.group(1)),
                              "specs_todo": int(m.group(2)),
                              "tokens_M_upper": float(m.group(3))}
                self.status = "awaiting_confirm"
            else:
                self.status = "interrupted"
                self.error = "server restarted during the quote stage"
        self._save()

    # ---- progress ---------------------------------------------------------
    def progress(self):
        d = areas.DATA / self.area
        p = {"bootstrap": (d / "buildings.json").exists(),
             "total": 0, "specs": 0, "refined": 0,
             "scene_layers": (d / "roads_raw.json").exists(),
             "assembled": bool(list(d.glob("*_textured.blend"))),
             "verdict": None}
        bj = d / "buildings.json"
        if bj.exists():
            try:
                p["total"] = len(json.loads(bj.read_text())["buildings"])
            except Exception:
                pass
        p["specs"] = len(list(d.glob("buildings/*/spec.json")))
        p["refined"] = len(list(d.glob("buildings/*/refine/result.json")))
        rp = d / "pipeline_report.json"
        if rp.exists():
            try:
                p["verdict"] = json.loads(rp.read_text()).get("verdict")
            except Exception:
                pass
        return p

    def stage_of(self, p):
        """Coarse 'what is it doing right now' label key."""
        if self.status == "quoting":
            return "quote"
        if self.status != "running":
            return None
        if not p["bootstrap"]:
            return "quote"
        if p["total"] and p["specs"] < p["total"]:
            return "specs"
        # NOTE: "assembled" may reflect a stale LoD1 preview blend, so it
        # cannot separate refine from final assembly; the verdict can.
        if not p["verdict"]:
            return "refine"
        return "verify"

    def _log_tail(self, n):
        if n <= 0 or not self.log_path.exists():
            return ""
        try:
            lines = self.log_path.read_text(errors="ignore").splitlines()
            return "\n".join(lines[-n:])
        except Exception:
            return ""

    def last_line(self):
        tail = self._log_tail(12)
        for ln in reversed(tail.splitlines()):
            ln = ln.strip()
            if ln and not ln.startswith("$"):
                return ln[:180]
        return ""

    def to_dict(self, log_lines=18):
        p = self.progress()
        return {"id": self.id, "kind": self.kind, "area": self.area,
                "bbox": self.bbox, "status": self.status, "quote": self.quote,
                "error": self.error, "created": self.created,
                "progress": p, "stage": self.stage_of(p),
                "last_line": self.last_line(),
                "log_tail": self._log_tail(log_lines),
                "blender_alive": blender_alive(),
                "maps_key": bool(os.environ.get("GOOGLE_MAPS_API_KEY")),
                "meta": self.meta}


def create(kind, area, bbox=None, meta=None):
    with _guard:
        for j in _jobs.values():
            if j.area == area and j.status in ("quoting", "awaiting_confirm", "running"):
                raise RuntimeError(f"area {area} already has an active job {j.id}")
        j = Job(kind, area, bbox, meta)
        _jobs[j.id] = j
        j._save()
        return j


def get(jid):
    return _jobs.get(jid)


def all_jobs():
    return sorted(_jobs.values(), key=lambda j: -j.created)


def active_count():
    return sum(1 for j in _jobs.values()
               if j.status in ("quoting", "awaiting_confirm", "running"))


def _load_persisted():
    if not JOBS_DIR.is_dir():
        return
    for p in JOBS_DIR.glob("*.json"):
        try:
            doc = json.loads(p.read_text())
        except Exception:
            continue
        if doc.get("id") in _jobs:
            continue
        j = Job(doc.get("kind", "generate"), doc.get("area", ""),
                doc.get("bbox"), doc.get("meta"), jid=doc["id"])
        j.status = doc.get("status", "interrupted")
        j.quote = doc.get("quote")
        j.error = doc.get("error")
        j.created = doc.get("created", 0)
        j.pid = doc.get("pid")
        _jobs[j.id] = j
        if j.status in ("quoting", "running"):
            j.adopt()
        elif j.status == "created":
            j.status = "interrupted"
            j._save()


_load_persisted()
