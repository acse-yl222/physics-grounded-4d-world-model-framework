"""img2city/imagery/facade_facts.py -- deterministic window/door FACTS from the street-view photo,
injected into the BRIEF like the OSM dimensions (related_work_methods.md L/O item 3:
"run a facade parser on the street-view crop -> window grid counts/spacing/type into
the BRIEF as facts -- removes the checks the agent chronically misjudges by eye").

RTFP (the research pick) ships no pretrained weights, so the detector here is
OWLv2 (zero-shot open-vocabulary detection, pip weights, deterministic in eval
mode): boxes for "a window" / "a door", NMS + nested-box cleanup, then 1-D row
clustering of window centres -> visible storeys, windows per storey, median
window aspect, door count. Validated on Victorian terrace street views: threshold
0.10 finds every window incl. dormers and basement lightwells (0.25 found 3).

The facts are worded as OBSERVATIONS OF THE PHOTO (visible storeys can include
attic dormers and basement rows that OSM height does not; the photo may show
neighbouring terrace houses), so the agent reconciles rather than blindly copies.

Usage:
  python -m img2city.imagery.facade_facts --image data/city_sk/buildings/869772993/streetview.png
  python -m img2city.imagery.facade_facts --out data/city_sk            # all buildings, cached
  python -m img2city.imagery.facade_facts --out data/city_sk --force --annotate
"""
from __future__ import annotations
import argparse
import glob
import json
import os

_MODEL = {}


def _detector():
    if not _MODEL:
        from transformers import Owlv2Processor, Owlv2ForObjectDetection
        _MODEL["proc"] = Owlv2Processor.from_pretrained(
            "google/owlv2-base-patch16-ensemble")
        _MODEL["model"] = Owlv2ForObjectDetection.from_pretrained(
            "google/owlv2-base-patch16-ensemble").eval()
    return _MODEL["proc"], _MODEL["model"]


def detect(image_path, threshold=0.10):
    """-> (windows, doors): lists of [x0, y0, x1, y1] in pixels, deduplicated.
    Vehicles are detected as a THIRD class purely to subtract them: car/van windows
    on parked vehicles read as building windows to the detector (seen on real
    junction shots), so any window/door whose centre falls inside a vehicle box is
    dropped before clustering."""
    import torch
    from PIL import Image
    proc, model = _detector()
    im = Image.open(image_path).convert("RGB")
    inputs = proc(text=[["a window", "a door", "a car", "a van or bus"]],
                  images=im, return_tensors="pt")
    with torch.no_grad():
        out = model(**inputs)
    res = proc.post_process_grounded_object_detection(
        out, threshold=threshold, target_sizes=torch.Tensor([im.size[::-1]]))[0]
    win, door, veh = [], [], []
    for box, lab, sc in zip(res["boxes"], res["labels"], res["scores"]):
        lab = int(lab)
        if lab == 0:
            win.append((box.tolist(), float(sc)))
        elif lab == 1:
            door.append((box.tolist(), float(sc)))
        elif sc > 0.15:                          # vehicles: higher bar, they only veto
            veh.append(box.tolist())

    def _in_vehicle(b):
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        return any(v[0] <= cx <= v[2] and v[1] <= cy <= v[3] for v in veh)
    win = [(b, s) for b, s in win if not _in_vehicle(b)]
    door = [(b, s) for b, s in door if not _in_vehicle(b)]
    return _dedup(win), _dedup(door)


def _iou(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    aa = (a[2] - a[0]) * (a[3] - a[1])
    ab = (b[2] - b[0]) * (b[3] - b[1])
    return inter / max(1e-6, aa + ab - inter)


def _dedup(dets, iou_thr=0.4):
    """Score-ordered NMS, then drop 'panel' boxes that fully contain >=2 kept boxes
    (OWLv2 often adds one box around a window PAIR beside the per-window boxes)."""
    dets = sorted(dets, key=lambda d: -d[1])
    kept = []
    for box, sc in dets:
        if all(_iou(box, k) < iou_thr for k in kept):
            kept.append(box)

    def _contains(a, b):
        return (a[0] <= b[0] + 2 and a[1] <= b[1] + 2
                and a[2] >= b[2] - 2 and a[3] >= b[3] - 2)
    return [b for b in kept
            if sum(1 for o in kept if o is not b and _contains(b, o)) < 2]


def facts(image_path, threshold=0.10):
    """-> dict of deterministic facade observations, or None if too few windows."""
    win, door = detect(image_path, threshold)
    if len(win) < 3:
        return None
    # Row clustering by y-INTERVAL OVERLAP (union-find): two windows share a row if
    # their vertical extents overlap >= 45% of the smaller one. Centre-gap
    # thresholds (global or local) both failed on real terrace photos: worm's-eye
    # perspective tilts a storey across the frame, so same-row centres drift apart
    # while their intervals still overlap -- and chaining absorbs the drift.
    parent = list(range(len(win)))

    def _find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(len(win)):
        for j in range(i + 1, len(win)):
            a, b = win[i], win[j]
            ov = min(a[3], b[3]) - max(a[1], b[1])
            if ov > 0.45 * min(a[3] - a[1], b[3] - b[1]):
                parent[_find(i)] = _find(j)
    groups = {}
    for i, b in enumerate(win):
        groups.setdefault(_find(i), []).append(b)
    rows = sorted(groups.values(), key=lambda r: sum((b[1] + b[3]) / 2 for b in r) / len(r))
    ws = sorted((b[2] - b[0]) for b in win)
    hs = sorted((b[3] - b[1]) for b in win)
    med_h = hs[len(hs) // 2]
    counts = [len(r) for r in rows]
    # reliability gate: a usable facade reads as a GRID -- at least two rows with
    # >= 2 windows, and multi-window rows must dominate. Wide junction shots (the
    # target building small and far, detections scattered over several buildings
    # and parked cars) degenerate to one mega-row or many singletons -> no facts,
    # the BRIEF falls back to OSM dims only.
    multi = [c for c in counts if c >= 2]
    if len(multi) < 2 or len(multi) / len(counts) < 0.5:
        return None
    med_w = ws[len(ws) // 2]
    counts_mid = sorted(counts)[len(counts) // 2]
    from PIL import Image
    img_w, img_h = Image.open(image_path).size
    # underscore keys are pixel-space data for facade_project.py (vertical
    # alignment of the photo projection); _facade_facts strips them from the BRIEF
    rows_px = [{"y": round(sum((b[1] + b[3]) / 2 for b in r) / len(r), 1),
                "n": len(r),
                "h": round(sum(b[3] - b[1] for b in r) / len(r), 1)} for r in rows]
    return {
        "_rows_px": rows_px,
        "_img_wh": [img_w, img_h],
        # raw detector boxes (px, ints) for facade_colors.py -- window rings give
        # the frame colour, interiors the glazing tint, the rest the wall
        "_win_boxes": [[int(v) for v in b] for b in win],
        "_door_boxes": [[int(v) for v in b] for b in door],
        "visible_window_rows": len(rows),
        "windows_per_row": counts,          # top row first (image top = row 0)
        "typical_windows_per_row": counts_mid,
        "window_aspect_h_over_w": round(med_h / max(1.0, med_w), 2),
        "doors_visible": len(door),
        "n_windows_total": len(win),
        "note": ("counted by an object detector on the street-view photo; rows are "
                 "TOP-FIRST and can include attic dormers and basement lightwells, "
                 "and the photo may include neighbouring buildings"),
    }


def _annotate(image_path, out_path, threshold=0.10):
    from PIL import Image, ImageDraw
    win, door = detect(image_path, threshold)
    im = Image.open(image_path).convert("RGB")
    d = ImageDraw.Draw(im)
    for b in win:
        d.rectangle(b, outline=(255, 60, 60), width=3)
    for b in door:
        d.rectangle(b, outline=(60, 120, 255), width=3)
    im.save(out_path)


def for_building(bdir, force=False):
    """Cached facts for one building dir (streetview.png inside)."""
    cache = os.path.join(bdir, "facade_facts.json")
    if os.path.exists(cache) and not force:
        return json.load(open(cache))
    img = os.path.join(bdir, "streetview.png")
    try:                                  # cleaned reference when gate-accepted
        from img2city.city.generate import ref_photo
        img = ref_photo(bdir)
    except Exception:
        pass
    if not os.path.exists(img):
        return None
    f = facts(img)
    with open(cache, "w") as fh:
        json.dump(f, fh, indent=1)
    return f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image")
    ap.add_argument("--out", help="city dir: run over every buildings/*/streetview.png")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--annotate", action="store_true",
                    help="also save facade_facts_boxes.png next to each photo")
    a = ap.parse_args()
    if a.image:
        print(json.dumps(facts(a.image), indent=1))
        if a.annotate:
            _annotate(a.image, a.image.replace(".png", "_boxes.png"))
        return
    done = skipped = 0
    for bdir in sorted(glob.glob(os.path.join(a.out, "buildings", "*"))):
        f = for_building(bdir, a.force)
        if f is None:
            skipped += 1
            continue
        done += 1
        if a.annotate:
            _annotate(os.path.join(bdir, "streetview.png"),
                      os.path.join(bdir, "facade_facts_boxes.png"))
        print(f"[{os.path.basename(bdir)}] rows={f['visible_window_rows']} "
              f"per-row={f['windows_per_row']} doors={f['doors_visible']}")
    print(f"[facade] {done} ok, {skipped} skipped (no photo / <3 windows)")


if __name__ == "__main__":
    main()
