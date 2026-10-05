"""Tool layer + executors for the harness.

An Executor turns an Action into a new scene state and a render:
    Executor.execute(action, state) -> (render_path, new_state)

  * MockExecutor       -- offline. Renders a parametric tower silhouette from a
                          few numeric params, so the whole loop runs without
                          Blender (development / CI / this demo).
  * MCPBlenderExecutor -- wiring point. Sends the action (a registered tool call
                          or bpy code) to Blender through the BlenderMCP bridge,
                          then renders from the locked worm's-eye compare camera
                          (see ../blender_compare_render.py).

The ToolRegistry holds the typed operations the agent is allowed to call, each
with a JSON schema. That registry IS the "tool layer" the project plan calls for
(import / repair / edit / render / export); here we expose a couple as examples.
"""
from __future__ import annotations
import copy
import json
import os
import socket
from dataclasses import dataclass
from typing import Any, Callable, Dict, Tuple

from PIL import Image, ImageDraw

from img2city import config


@dataclass
class Tool:
    name: str
    description: str
    schema: Dict[str, Any]                 # JSON schema of the arguments
    fn: Callable = None


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool):
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        return self._tools[name]

    def names(self):
        return list(self._tools)

    def schemas(self):
        """Anthropic-style tool schemas, ready to pass to the planner."""
        return [{"name": t.name, "description": t.description,
                 "input_schema": t.schema} for t in self._tools.values()]


def example_registry() -> ToolRegistry:
    """A minimal illustrative tool layer for the Blender path."""
    r = ToolRegistry()
    r.register(Tool("import_mesh", "Import a generated mesh (.obj/.glb) into the scene.",
                    {"type": "object", "properties": {"path": {"type": "string"}},
                     "required": ["path"]}))
    r.register(Tool("edit_geometry", "Run a constrained bpy edit on the active object.",
                    {"type": "object", "properties": {"bpy_code": {"type": "string"}},
                     "required": ["bpy_code"]}))
    r.register(Tool("render_compare", "Render from the locked worm's-eye compare camera.",
                    {"type": "object", "properties": {}}))
    r.register(Tool("export_mesh", "Export the cleaned mesh.",
                    {"type": "object", "properties": {"path": {"type": "string"}},
                     "required": ["path"]}))
    return r


class Executor:
    def reset(self) -> Dict[str, Any]:
        raise NotImplementedError

    def execute(self, action, state) -> Tuple[str, Dict[str, Any]]:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Offline mock executor: a parametric tower silhouette.
# ---------------------------------------------------------------------------
PARAMS = ["base_w", "shaft_w", "belfry_w", "dome_r", "spire_h"]
_FILL = (115, 105, 88)        # tower colour (not black -> survives the mask)


def _draw_tower(p, path, size=(300, 640)):
    W, H = size
    im = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(im)
    cx = W // 2
    base_w = p["base_w"] * W * 0.9
    shaft_w = p["shaft_w"] * W * 0.7
    belfry_w = p["belfry_w"] * W * 0.8
    dome_r = p["dome_r"] * W * 0.35
    spire = p["spire_h"] * H * 0.12
    y = H - 10
    bh = H * 0.10
    d.rectangle([cx - base_w / 2, y - bh, cx + base_w / 2, y], fill=_FILL); y -= bh
    sh = H * 0.50
    d.polygon([(cx - shaft_w / 2, y), (cx + shaft_w / 2, y),
               (cx + shaft_w * 0.42, y - sh), (cx - shaft_w * 0.42, y - sh)], fill=_FILL); y -= sh
    fh = H * 0.12
    d.rectangle([cx - belfry_w / 2, y - fh, cx + belfry_w / 2, y], fill=_FILL); y -= fh
    d.pieslice([cx - dome_r, y - dome_r, cx + dome_r, y + dome_r], 180, 360, fill=_FILL); y -= dome_r
    d.polygon([(cx - 3, y), (cx + 3, y), (cx, y - spire)], fill=_FILL)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path)
    return path


class MockExecutor(Executor):
    """Renders a parametric tower; exercises the loop offline. The 'target' is a
    hidden ground-truth param set the agent tries to match (its reference render
    is produced by make_reference())."""
    def __init__(self, out_dir, target=None):
        self.out_dir = out_dir
        self.target = target or {"base_w": 0.85, "shaft_w": 0.55,
                                 "belfry_w": 0.70, "dome_r": 0.42, "spire_h": 0.70}
        self._i = 0

    def make_reference(self):
        return _draw_tower(self.target, os.path.join(self.out_dir, "mock_reference.png"))

    def reset(self):
        return {"base_w": 0.40, "shaft_w": 0.90, "belfry_w": 0.40,
                "dome_r": 0.15, "spire_h": 0.10}

    def execute(self, action, state):
        st = copy.deepcopy(state)
        for k, dv in getattr(action, "params_delta", {}).items():
            if k in st:
                st[k] = min(1.0, max(0.05, st[k] + dv))
        self._i += 1
        path = _draw_tower(st, os.path.join(self.out_dir, f"render_{self._i:03d}.png"))
        return path, st


class MCPBlenderExecutor(Executor):
    """Drive a live Blender (BlenderMCP addon on localhost:9876) to rebuild + render
    the model each iteration. The agent emits a bpy edit in Action.bpy_code.

    Protocol (see ../addon.py): connect to the socket, send
    {"type":"execute_code","params":{"code": <bpy>}} as raw JSON bytes, read until
    the JSON reply parses; reply is {"status":"success","result":{...}} or error.

    Determinism: Blender is stateful, but the harness's accept/reject needs every
    iteration to start from the *best accepted* state. So each call rebuilds from
    scratch -- clear meshes -> import the base model -> replay the accepted edits
    -> apply this iteration's new edit -> render. The state we hand back is just
    the list of edits, which the harness keeps only when the score improves.

    Prereq: Blender open with the BlenderMCP addon's server running on `port`.
    """
    def __init__(self, out_dir, obj_path, host=None, port=None,
                 cam_loc=(40.902, -210.423, -5.989), cam_rot_deg=(103.0, 0.0, 11.0),
                 lens=60.0, res=(600, 1720), timeout=180):
        self.out_dir = out_dir
        self.obj_path = obj_path
        self.host = host or config.MCP_HOST
        self.port = port or config.MCP_PORT
        self.timeout = timeout
        self.cam_loc, self.cam_rot_deg, self.lens, self.res = cam_loc, cam_rot_deg, lens, res
        self._i = 0

    def _send(self, code):
        """One execute_code round-trip to the BlenderMCP socket; returns the result
        dict, raises on a Blender-side error."""
        payload = json.dumps({"type": "execute_code",
                              "params": {"code": code}}).encode("utf-8")
        buf, resp = b"", None
        with socket.create_connection((self.host, self.port), timeout=self.timeout) as s:
            s.settimeout(self.timeout)
            s.sendall(payload)
            while True:
                chunk = s.recv(8192)
                if not chunk:
                    break
                buf += chunk
                try:
                    resp = json.loads(buf.decode("utf-8"))
                    break
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue            # reply not fully received yet
        if resp is None:
            raise RuntimeError("Blender closed the connection before replying "
                               "(is the BlenderMCP server running?)")
        if resp.get("status") != "success":
            raise RuntimeError(f"Blender error: {resp.get('message')}")
        return resp.get("result", {})

    def _reset_code(self):
        return (
            "import bpy\n"
            "for _o in list(bpy.data.objects):\n"
            "    if _o.type=='MESH': bpy.data.objects.remove(_o, do_unlink=True)\n"
            "try:\n"
            f"    bpy.ops.wm.obj_import(filepath=r'{self.obj_path}', forward_axis='Y', up_axis='Z')\n"
            "except TypeError:\n"
            f"    bpy.ops.wm.obj_import(filepath=r'{self.obj_path}')\n"
        )

    def _render_code(self, out_png):
        cx, cy, cz = self.cam_loc
        rx, ry, rz = self.cam_rot_deg
        W, H = self.res
        return (
            "import bpy, math\n"
            "cam = bpy.data.objects.get('CmpCam') or "
            "bpy.data.objects.new('CmpCam', bpy.data.cameras.new('CmpCam'))\n"
            "if cam.name not in bpy.context.scene.collection.objects:\n"
            "    bpy.context.scene.collection.objects.link(cam)\n"
            f"cam.location=({cx},{cy},{cz})\n"
            f"cam.rotation_euler=tuple(math.radians(a) for a in ({rx},{ry},{rz}))\n"
            f"cam.data.lens={self.lens}; cam.data.sensor_fit='VERTICAL'\n"
            "bpy.context.scene.camera=cam\n"
            "sun = bpy.data.objects.get('CmpSun') or "
            "bpy.data.objects.new('CmpSun', bpy.data.lights.new('CmpSun','SUN'))\n"
            "if sun.name not in bpy.context.scene.collection.objects:\n"
            "    bpy.context.scene.collection.objects.link(sun)\n"
            "sun.data.energy=3.0; sun.rotation_euler=tuple(math.radians(a) for a in (55,10,40))\n"
            "w=bpy.context.scene.world or bpy.data.worlds.new('W'); bpy.context.scene.world=w\n"
            "w.use_nodes=True; bg=w.node_tree.nodes.get('Background')\n"
            "if bg: bg.inputs[0].default_value=(1,1,1,1); bg.inputs[1].default_value=1.0\n"
            "sc=bpy.context.scene\n"
            "try: sc.render.engine='BLENDER_EEVEE_NEXT'\n"
            "except Exception: sc.render.engine='BLENDER_EEVEE'\n"
            f"sc.render.resolution_x,sc.render.resolution_y={W},{H}; sc.render.resolution_percentage=100\n"
            "sc.render.image_settings.file_format='PNG'\n"
            f"sc.render.filepath=r'{out_png}'\n"
            "bpy.ops.render.render(write_still=True)\n"
        )

    def reset(self):
        return {"edits": []}

    def execute(self, action, state):
        edits = list(state.get("edits", []))
        if getattr(action, "bpy_code", None):
            edits.append(action.bpy_code)
        self._i += 1
        os.makedirs(self.out_dir, exist_ok=True)
        out_png = os.path.join(self.out_dir, f"render_{self._i:03d}.png")
        # rebuild deterministically, then render from the locked camera (one round-trip)
        code = self._reset_code() + "\n".join(edits) + "\n" + self._render_code(out_png)
        self._send(code)
        return out_png, {"edits": edits}
