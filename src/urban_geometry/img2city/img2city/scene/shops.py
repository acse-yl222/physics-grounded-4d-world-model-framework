"""img2city/scene/shops.py -- STREET-SIDE SHOP UNITS as a parameterised layer.

Until now "shopfront" was a single BOOLEAN knob on a building (mined 07-14 from
the checklist statistics): the ground floor got one continuous glass band + a
dark fascia strip + stone piers, with no unit division, no identity, no signage.
This module turns that band into real, individually parameterised SHOP UNITS
carrying the businesses that are actually there.

Deterministic pipeline, cached like every other scene layer (trees / vehicles /
traffic):

  1. poi      Places API (New) searchNearby over the block with RETAIL types
              (the function layer's type table deliberately has none of these --
              building_function.py answers "what IS this building", this answers
              "what trades on its ground floor"). Cached: shops_raw.json.
  2. assign   POI -> host BUILDING and host WALL EDGE. Containment first
              (building_function.py's rule), then projection onto the nearest
              wall: unconditional within ASSIGN_NEAR, and out to ASSIGN_FAR only
              when no frontage FACES BACK from across the street (Google drops a
              shop pin on the pavement, so a hard radius either loses real shops
              or picks a side of the street by coin flip). A POI with no modelled
              frontage in reach is dropped, never snapped -- 2026-07-27's lesson:
              POI density alone over-detects, the South Kensington shop pins land
              in the pedestrian plaza, not on a roof. Only STREET-FACING edges
              qualify (the outward normal must look at a drivable ribbon) --
              "street-side" is a geometric test, not a guess.
  3. layout   each edge's ground-floor frontage is divided into units: one per
              POI at its projected position, width from a typed per-category
              default, overlaps resolved by a sweep, and remaining frontage on a
              parade edge filled with anonymous units (Places does not return
              every unit on a street).
  4. params   every unit is a typed parameter vector (width / stallriser /
              glazing height / fascia + sign colour / awning / door position)
              with per-parameter `src` + `conf`, the same provenance pattern as
              the building schema and road_graph's lanes_src. Category defaults
              land at low confidence ON PURPOSE, so the street-view agent pass
              (shop_agent.py, source "streetview", conf 0.8) overrides them
              while never fighting a measured value.

Output shops.json: {"units": [...], "hosts": [...]} -- an editable semantic
layer; components.polygon_terrace renders it in place of the boolean band.

  python -m img2city.scene.shops --out data/city_sk            # cached
  python -m img2city.scene.shops --out data/city_sk --force    # re-query Places
  python -m img2city.scene.shops --out data/city_sk --report   # cross-check vs specs
"""
from __future__ import annotations
import argparse
import glob
import json
import math
import os

from img2city.imagery.maps_fetch import places_nearby

# ---------------------------------------------------------------- categories
# Places(New) Table A types -> our coarse SHOP CATEGORY. Only types that trade
# from a street unit belong here; a bad type 400s the WHOLE searchNearby call
# (building_function.py's `place_of_worship` lesson), so this list is tested as
# a unit -- if a query suddenly returns nothing, suspect a newly added type.
CATEGORY = {}
for _cat, _types in {
    "restaurant": ("restaurant", "italian_restaurant", "japanese_restaurant",
                   "chinese_restaurant", "french_restaurant", "indian_restaurant",
                   "thai_restaurant", "vietnamese_restaurant", "korean_restaurant",
                   "mexican_restaurant", "spanish_restaurant", "greek_restaurant",
                   "lebanese_restaurant", "mediterranean_restaurant",
                   "middle_eastern_restaurant", "seafood_restaurant",
                   "steak_house", "sushi_restaurant", "pizza_restaurant",
                   "hamburger_restaurant", "brunch_restaurant", "breakfast_restaurant",
                   "fast_food_restaurant", "meal_takeaway", "meal_delivery",
                   "sandwich_shop", "ramen_restaurant"),
    "cafe": ("cafe", "coffee_shop", "bakery", "ice_cream_shop", "dessert_shop",
             "tea_house", "juice_shop"),
    "bar": ("bar", "pub", "wine_bar", "night_club"),
    "grocery": ("supermarket", "grocery_store", "convenience_store",
                "liquor_store", "butcher_shop", "food_store"),
    "pharmacy": ("pharmacy", "drugstore"),
    "bank": ("bank", "atm"),
    "salon": ("hair_care", "hair_salon", "beauty_salon", "barber_shop", "spa",
              "nail_salon"),
    "clothing": ("clothing_store", "shoe_store", "jewelry_store", "boutique"),
    "books": ("book_store", "gift_shop", "florist", "pet_store", "toy_store"),
    "homeware": ("furniture_store", "home_goods_store", "hardware_store",
                 "electronics_store", "cell_phone_store", "bicycle_store"),
    "services": ("real_estate_agency", "travel_agency", "laundry",
                 "post_office", "dental_clinic", "optician", "veterinary_care"),
    "store": ("store", "department_store", "shopping_mall"),
}.items():
    for _t in _types:
        CATEGORY[_t] = _cat

# the query list, in GROUPS. Two hard Places(New) limits shape this: at most 50
# includedTypes per call (52 in one list 400s the whole request -- and
# places_nearby swallows the error, so the symptom is a silent 0 POIs), and at
# most 20 results per call. Querying group by group therefore also RAISES recall:
# the 20-result cap applies per call, so a street's cafes can no longer be
# crowded out by its restaurants.
QUERY_GROUPS = [
    ["restaurant", "meal_takeaway", "sandwich_shop", "fast_food_restaurant",
     "italian_restaurant", "japanese_restaurant", "chinese_restaurant",
     "indian_restaurant", "thai_restaurant", "vietnamese_restaurant",
     "mediterranean_restaurant", "pizza_restaurant", "hamburger_restaurant"],
    ["cafe", "coffee_shop", "bakery", "ice_cream_shop", "juice_shop",
     "bar", "pub", "wine_bar",
     "supermarket", "grocery_store", "convenience_store", "liquor_store"],
    ["pharmacy", "drugstore", "bank", "atm",
     "hair_care", "beauty_salon", "spa", "nail_salon",
     "clothing_store", "shoe_store", "jewelry_store",
     "book_store", "gift_shop", "florist", "pet_store"],
    ["furniture_store", "home_goods_store", "hardware_store",
     "electronics_store", "cell_phone_store", "bicycle_store",
     "real_estate_agency", "travel_agency", "laundry", "post_office",
     "store", "department_store", "shopping_mall"],
]

# typed default frontage per category (metres) -- a Tesco Express holds a wider
# unit than a coffee shop. Refined by the layout sweep, overridable per unit.
UNIT_W = {"restaurant": 7.0, "cafe": 5.5, "bar": 8.5, "grocery": 10.0,
          "pharmacy": 6.5, "bank": 8.0, "salon": 5.0, "clothing": 6.5,
          "books": 5.5, "homeware": 7.0, "services": 5.0, "store": 6.5,
          "unknown": 5.5}
UNIT_W_MIN, UNIT_W_MAX = 3.2, 15.0

# fascia palettes in LINEAR rgb (London high-street shopfront paint: deep,
# desaturated, near-black greens/reds/blues + off-whites). One palette per
# category, the entry picked by a stable hash of the name so a shop keeps its
# colour across regenerations. source "category_default", conf 0.30 -- the
# street-view pass is meant to overwrite these.
PALETTE = {
    "restaurant": [(0.045, 0.055, 0.048), (0.075, 0.030, 0.028), (0.030, 0.045, 0.070),
                   (0.140, 0.110, 0.075)],
    "cafe": [(0.085, 0.060, 0.040), (0.045, 0.055, 0.048), (0.180, 0.160, 0.130)],
    "bar": [(0.030, 0.048, 0.038), (0.060, 0.022, 0.024), (0.028, 0.030, 0.040)],
    "grocery": [(0.035, 0.070, 0.045), (0.045, 0.055, 0.130), (0.140, 0.030, 0.030)],
    "pharmacy": [(0.030, 0.075, 0.055), (0.040, 0.060, 0.110)],
    "bank": [(0.030, 0.040, 0.080), (0.045, 0.050, 0.055)],
    "salon": [(0.055, 0.045, 0.060), (0.150, 0.140, 0.135), (0.030, 0.032, 0.036)],
    "clothing": [(0.035, 0.036, 0.040), (0.150, 0.145, 0.135), (0.070, 0.055, 0.045)],
    "books": [(0.055, 0.040, 0.030), (0.035, 0.050, 0.045)],
    "homeware": [(0.045, 0.048, 0.052), (0.090, 0.075, 0.055)],
    "services": [(0.035, 0.045, 0.075), (0.130, 0.125, 0.120)],
    "store": [(0.040, 0.042, 0.046), (0.100, 0.090, 0.080)],
    "unknown": [(0.048, 0.050, 0.052), (0.120, 0.115, 0.108)],
}
# categories whose units get a projecting awning by default (cafes/greengrocers
# NOTE these probabilities were derived from LONDON street photos; a canvas
# awning is a cultural element, so the default applies only in regions whose
# own imagery corpus shows them (EURO_AWNING_REGIONS). Everywhere else an
# awning appears ONLY when the street-photo pass (shop_agent) measured one --
# the no-fabrication rule (Delhi audit, 2026-08-24: 35/317 units had London
# default awnings with zero photo evidence).
# put one out; a bank does not)
AWNING_CATS = {"cafe": 0.7, "restaurant": 0.35, "grocery": 0.5, "books": 0.3}
EURO_AWNING_REGIONS = {"london", "amsterdam", "paris"}


def _area_region(out):
    """region.json tag, default london (same rule as generate.area_region;
    duplicated to keep shop_assets import-light)."""
    try:
        return json.load(open(os.path.join(out, "region.json")))["region"]
    except Exception:
        return "london"
AWNING_RGB = [(0.055, 0.055, 0.058), (0.070, 0.025, 0.026), (0.030, 0.050, 0.038),
              (0.140, 0.130, 0.115)]

ASSIGN_NEAR = 5.0        # m: a pin this far OUTSIDE a wall always belongs to it
ASSIGN_FAR = 16.0        # m: ... and up to here IF the assignment is unambiguous
ASSIGN_MARGIN = 4.0      # m: nearest wall must beat the runner-up building by this
STREET_REACH = 14.0      # m: wall-to-carriageway-centre reach for "street-side"
MIN_EDGE = 4.0           # m: an edge shorter than this holds no shop unit
FILL_MIN = 3.6           # m: gaps in a parade at least this wide become units


# ------------------------------------------------------------------ geometry
def _point_in_poly(x, y, pts):
    inside = False
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def _proj(px, py, x1, y1, x2, y2):
    """Project onto a segment: returns (t in 0..1, distance, foot x, foot y)."""
    dx, dy = x2 - x1, y2 - y1
    ll = dx * dx + dy * dy
    t = 0.0 if ll < 1e-9 else max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / ll))
    fx, fy = x1 + t * dx, y1 + t * dy
    return t, math.hypot(px - fx, py - fy), fx, fy


def _dang(a, b):
    return abs((a - b + math.pi) % (2 * math.pi) - math.pi)


def frontage_runs(pts, max_turn=0.20, max_dev=0.7):
    """Merge consecutive near-collinear edges into one FRONTAGE RUN.

    OSM traces a terrace with as many vertices as the survey had: 847120664 is a
    49-point polygon whose Bute Street frontage arrives as a dozen 1-4 m edges.
    Treating those as separate walls put six shops on one 5.2 m stub, stacked on
    top of each other. A run absorbs the next edge while it stays within
    max_turn of the run's own chord AND every intermediate vertex hugs that
    chord within max_dev, so a genuine corner still ends the run.

    Returns [{ks: [original edge indices], a: (x, y), b: (x, y)}]."""
    n = len(pts)

    def bear(i):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        return math.atan2(y2 - y1, x2 - x1)

    start = 0
    for i in range(n):                        # begin at a real corner
        if _dang(bear(i), bear((i - 1) % n)) > max_turn:
            start = i
            break
    runs, i = [], 0
    while i < n:
        k0 = (start + i) % n
        ks, a = [k0], pts[k0]
        j = i + 1
        while j < n:
            k = (start + j) % n
            b = pts[(k + 1) % n]
            ch = math.atan2(b[1] - a[1], b[0] - a[0])
            if _dang(bear(k), ch) > max_turn:
                break
            if any(_proj(pts[(start + t) % n][0], pts[(start + t) % n][1],
                         a[0], a[1], b[0], b[1])[1] > max_dev
                   for t in range(i + 1, j + 1)):
                break
            ks.append(k)
            j += 1
        runs.append({"ks": ks, "a": a, "b": pts[(ks[-1] + 1) % n]})
        i = j
    return runs


def street_runs(pts, segs):
    """Frontage runs whose OUTWARD normal looks at a drivable carriageway within
    STREET_REACH -- the geometric definition of street-side. Returns
    {run index: (ang, nx, ny, length, a, ks)}."""
    out = {}
    for ri, run in enumerate(frontage_runs(pts)):
        (x1, y1), (x2, y2) = run["a"], run["b"]
        L = math.hypot(x2 - x1, y2 - y1)
        if L < MIN_EDGE:
            continue
        ang = math.atan2(y2 - y1, x2 - x1)
        nx, ny = -math.sin(ang), math.cos(ang)
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        if _point_in_poly(mx + nx * 0.6, my + ny * 0.6, pts):
            nx, ny = -nx, -ny                       # flip to point OUT of the mass
        hit = False
        for (rx1, ry1), (rx2, ry2), w in segs:
            _t, d, fx, fy = _proj(mx, my, rx1, ry1, rx2, ry2)
            if d > w / 2 + STREET_REACH:
                continue
            # the carriageway must lie on the OUTWARD side: a road behind the
            # building (its back wall) is not this frontage's street
            if (fx - mx) * nx + (fy - my) * ny <= 0:
                continue
            hit = True
            break
        if hit:
            out[ri] = (ang, nx, ny, L, run["a"], run["ks"])
    return out


# ------------------------------------------------------------------- sources
def fetch_pois(out, bbox_pts, force=False):
    """3x3 grid of searchNearby calls over the block (Places(New) caps each call
    at 20 results), deduped by name+coord. Cached in shops_raw.json."""
    cache = os.path.join(out, "shops_raw.json")
    if os.path.exists(cache) and not force:
        return json.load(open(cache))
    lats = [p[0] for p in bbox_pts]
    lngs = [p[1] for p in bbox_pts]
    seen, pois = {}, []
    for i in range(3):
        for j in range(3):
            la = min(lats) + (max(lats) - min(lats)) * (i + 0.5) / 3
            ln = min(lngs) + (max(lngs) - min(lngs)) * (j + 0.5) / 3
            for grp in QUERY_GROUPS:
                for p in places_nearby(la, ln, radius=180.0,
                                       included_types=grp, max_results=20):
                    if p["lat"] is None:
                        continue
                    k = "%.5f,%.5f,%s" % (p["lat"], p["lng"], p["name"])
                    if k in seen:
                        continue
                    seen[k] = 1
                    pois.append(p)
    with open(cache, "w") as f:
        json.dump(pois, f, indent=1)
    print(f"[shops] {len(pois)} retail POIs from Places(New) -> shops_raw.json")
    return pois


def poi_category(p):
    for t in [p.get("primary_type", "")] + list(p.get("types", [])):
        if t in CATEGORY:
            return CATEGORY[t]
    return None


# -------------------------------------------------------------------- params
def _hpick(name, seq):
    """Stable pick from a list -- the same shop keeps its colour on every run
    (Date/random are banned from the deterministic tier anyway)."""
    h = 0
    for ch in name or "":
        h = (h * 131 + ord(ch)) & 0xFFFFFFF
    return seq[h % len(seq)]


def sign_text(name):
    """What the FASCIA says, which is not the Places display name: Google returns
    the branch ("Cacciari's South Kensington", "Little Waitrose & Partners"), the
    painted board carries the business. Trim the trailing locality and clip what
    is left to a length a shopfront can actually letter."""
    if not name:
        return ""
    t = " ".join(name.split())
    for tail in ("South Kensington", "Kensington", "South Ken", "London",
                 "Chelsea", "Knightsbridge", "SW7", "SW3", "UK"):
        for sep in (" - ", " – ", ", ", " "):
            if t.lower().endswith((sep + tail).lower()) and len(t) > len(tail) + 3:
                t = t[:-(len(tail) + len(sep))].rstrip(" -,–")
    if len(t) > 26:
        t = t[:25].rstrip() + "…"
    return t


def unit_params(name, cat, width, floor_h, awning_default_ok=True):
    """Typed defaults for one unit. Every entry carries a source + confidence so
    the street-view pass can override the guessed ones and leave the measured
    ones alone (the refine rule: never fight a measured value)."""
    fh = float(floor_h)
    stall = 0.42 if cat in ("restaurant", "cafe", "bar", "books") else 0.30
    fascia_h = min(0.62, max(0.42, fh * 0.16))
    glaz_h = max(1.6, fh - stall - fascia_h - 0.35)
    aw_p = AWNING_CATS.get(cat, 0.0) if awning_default_ok else 0.0
    awning = _hpick((name or cat) + "aw", list(range(10))) < aw_p * 10
    p = {"width": round(width, 2),
         "stall_h": stall,                        # stallriser (kerb-level plinth)
         "glaz_h": round(glaz_h, 2),              # clear glazing height
         "fascia_h": round(fascia_h, 2),          # signboard band height
         "mullions": max(0, int(width / 1.9) - 1),
         "door_t": 0.5 if cat in ("bank", "grocery", "store") else 0.78,
         "door_w": 1.15,
         "recess": 0.18,                          # door set back from the glass line
         "fascia_rgb": [round(c, 4) for c in _hpick(name or cat, PALETTE.get(cat, PALETTE["unknown"]))],
         "sign_text": sign_text(name),
         "sign_rgb": [0.72, 0.70, 0.64],          # painted/illuminated lettering
         "awning": awning,
         "awning_rgb": [round(c, 4) for c in _hpick((name or cat) + "a", AWNING_RGB)],
         "awning_proj": 1.25}
    src = {k: "category_default" for k in p}
    src["width"] = "category_default"
    src["sign_text"] = "places" if name else "inferred"
    conf = {k: 0.30 for k in p}
    conf["width"] = 0.40
    conf["sign_text"] = 0.90 if name else 0.10
    return p, src, conf


# -------------------------------------------------------------------- layout
def layout_edge(units, L):
    """Place the edge's units along its length without overlap.

    Each unit wants its own width centred on the POI's projected position; a
    left-to-right sweep pushes collisions apart, a right-to-left pass pulls the
    tail back inside the wall, and if the demand exceeds the frontage every
    width is scaled down together (a 4-shop parade on a 20 m wall gives 5 m
    each, not four 7 m units spilling past the corner)."""
    units.sort(key=lambda u: u["_t"])
    pad = 0.35                                     # pier gap between units
    # a frontage cannot hold more units than its length at the minimum width.
    # Without this the sweep + tail pull-back stacked six shops on one 5.2 m
    # stub, all at the same t0/t1. Excess is DROPPED and reported, never hidden
    # (silent truncation reads as "we placed them all").
    cap = max(1, int((L + pad) / (UNIT_W_MIN + pad)))
    dropped = []
    if len(units) > cap:
        dropped = units[cap:]
        units = units[:cap]
    total = sum(u["_w"] for u in units) + pad * (len(units) - 1)
    if total > L * 0.98:
        sc = (L * 0.98 - pad * (len(units) - 1)) / max(1e-6, sum(u["_w"] for u in units))
        for u in units:
            u["_w"] = max(UNIT_W_MIN, u["_w"] * sc)
    cur = 0.0
    for u in units:                                # forward sweep
        s = max(cur, u["_t"] * L - u["_w"] / 2)
        u["_s"] = s
        cur = s + u["_w"] + pad
    over = cur - pad - L
    if over > 0:                                   # pull the tail back inside
        cur = L
        for u in reversed(units):
            e = min(cur, u["_s"] + u["_w"])
            u["_s"] = max(0.0, e - u["_w"])
            cur = u["_s"] - pad
    return units, dropped


def fill_gaps(units, L, host, k):
    """A parade is continuous: Places returns the named businesses, not every
    unit. Gaps wider than FILL_MIN on an edge that already carries a shop become
    ANONYMOUS units (no sign) -- marked src.name="inferred" so nothing claims a
    business that was never observed."""
    spans = sorted([(u["_s"], u["_s"] + u["_w"]) for u in units])   # may be empty
    gaps, cur = [], 0.0
    for s, e in spans:
        if s - cur >= FILL_MIN:
            gaps.append((cur, s))
        cur = max(cur, e)
    if L - cur >= FILL_MIN:
        gaps.append((cur, L))
    out = []
    for gi, (a, b) in enumerate(gaps):
        span = b - a - 0.35
        nsub = max(1, int(round(span / UNIT_W["unknown"])))
        w = span / nsub
        if w < UNIT_W_MIN:
            nsub = max(1, int(span / UNIT_W_MIN))
            w = span / nsub
        for j in range(nsub):
            out.append({"_t": 0.0, "_w": w, "_s": a + 0.175 + j * w,
                        "name": None, "cat": "unknown", "poi_type": None,
                        "host": host, "edge": k, "fill": True, "sub": "%d_%d" % (gi, j)})
    return out


# --------------------------------------------------------------------- build
def built_outlines(out, buildings):
    """The footprint each building is ACTUALLY BUILT ON -- not always the OSM
    polygon. Assembly routes a building with OBB fill >= 0.72 through
    build_building(), which raises a rotated RECTANGLE (desc.footprint = the OBB
    L x W, posed at cx/cy/rot); only fill < 0.72 keeps the true polygon
    (polygon_terrace). 45 of this block's 56 shop hosts are rectangles, so
    projecting shop units onto OSM edges would leave them floating a metre off
    the wall that gets rendered.

    Returns {id: (pts, mode)}; special forms (station shed / open canopy) are
    omitted -- they have no ground-floor wall to hang a shopfront on."""
    outlines = {}
    place = {}
    f = os.path.join(out, "agent_placements.json")
    if os.path.exists(f):
        place = {e["id"]: e for e in json.load(open(f))}
    for m in buildings:
        if m.get("func") in ("station", "canopy") or \
           m.get("btype") in ("train_station", "roof"):
            continue
        e = place.get(m["id"])
        if e is None or "poly" in e:
            outlines[m["id"]] = ([tuple(q) for q in (e["poly"] if e else m["pts"])],
                                 "poly" if e else "lod1")
            continue
        L, W = (float(v) for v in e["desc"].get("footprint", [10.0, 10.0])[:2])
        cx, cy, rot = e["cx"], e["cy"], e["rot"]
        ca, sa = math.cos(rot), math.sin(rot)
        pts = [(cx + ca * (sx * L / 2) - sa * (sy * W / 2),
                cy + sa * (sx * L / 2) + ca * (sy * W / 2))
               for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        outlines[m["id"]] = (pts, "obb")
    return outlines


def _spec_shopfront(out, hid):
    """The agent's OWN street-view judgement, made when it wrote the spec."""
    f = os.path.join(out, "buildings", str(hid), "spec.json")
    try:
        return bool((json.load(open(f)).get("terrace") or {}).get("shopfront"))
    except Exception:
        return False


def _floor_h(out, hid):
    """The host's own storey height, so a unit's glazing/fascia split matches the
    ground floor the building actually has (specs vary 2.9-4.2 m)."""
    f = os.path.join(out, "buildings", str(hid), "spec.json")
    try:
        return float(json.load(open(f)).get("floor_h", 3.2))
    except Exception:
        return 3.2


def build(out, force=False):
    d = json.load(open(os.path.join(out, "buildings.json")))
    anchor, buildings = d["anchor"], d["buildings"]
    kx = 111320.0 * math.cos(math.radians(anchor["lat0"]))
    ky = 110540.0

    from img2city.scene import assets as scene_assets
    roads = scene_assets.load_or_build(out)[1]
    segs = [(r["pts"][i], r["pts"][i + 1], r["width"])
            for r in roads if r["class"] in scene_assets.DRIVABLE
            for i in range(len(r["pts"]) - 1)]

    pois = fetch_pois(out, [m["center_latlng"] for m in buildings], force)

    # POI -> scene metres, keeping only ones that map to a shop category
    cands = []
    for p in pois:
        cat = poi_category(p)
        if not cat:
            continue
        cands.append({"x": (p["lng"] - anchor["lon0"]) * kx,
                      "y": (p["lat"] - anchor["lat0"]) * ky,
                      "name": p["name"], "cat": cat,
                      "poi_type": p.get("primary_type") or ""})

    # buildings that do not trade over a street counter (08-17: shop
    # units were papering the Natural History Museum's frontage — 136 units
    # across NHM/V&A/Science Museum). Their retail POIs are INTERIOR
    # concessions (gift shops, gallery cafés); hosting them as street
    # shopfronts is categorically wrong, and a parade-fill on such a host
    # multiplies the error down the whole facade.
    NO_SHOPFRONT_FUNC = {"museum", "worship", "education", "hospital"}
    banned = {m["id"] for m in buildings
              if (m.get("func") or "") in NO_SHOPFRONT_FUNC}
    outlines = built_outlines(out, buildings)
    outlines = {i: v for i, v in outlines.items() if i not in banned}
    st = {i: street_runs(pts, segs) for i, (pts, _md) in outlines.items()}

    # assign each POI to (host building, street edge).
    #
    # Containment first (building_function.py's rule). A pin OUTSIDE every
    # footprint is the common case for shops -- Google drops the pin on the
    # pavement or the road centreline, not on the roof -- so a hard radius is the
    # wrong instrument: 5 m loses GAIL's Bakery (pin 5.8 m out) while 16 m would
    # let a pin in the middle of a narrow street pick a side by coin flip.
    # Instead: always accept within ASSIGN_NEAR, accept out to ASSIGN_FAR ONLY
    # when the assignment is UNAMBIGUOUS (the runner-up BUILDING is ASSIGN_MARGIN
    # further away), drop otherwise. Everything dropped is reported by reason --
    # a shop on a street we do not model looks exactly like the 07-27 plaza pin
    # unless you separate them.
    per_edge = {}
    stats = {"inside": 0, "near": 0, "far_ok": 0, "ambiguous": 0,
             "unhosted": 0, "no_street": 0, "spilled": 0}
    for c in cands:
        home = next((i for i, (pts, _md) in outlines.items()
                     if _point_in_poly(c["x"], c["y"], pts)), None)
        cand = []                                     # (dist, host, edge, t, nx, ny)
        for hid, (pts, _md) in outlines.items():
            if home is not None and hid != home:
                continue
            mbest = None
            for k, (ang, nx, ny, L, (x1, y1), _ks) in st[hid].items():
                x2, y2 = x1 + math.cos(ang) * L, y1 + math.sin(ang) * L
                t, dist, _fx, _fy = _proj(c["x"], c["y"], x1, y1, x2, y2)
                if mbest is None or dist < mbest[0]:
                    mbest = (dist, hid, k, t, nx, ny)
            if mbest is not None:
                cand.append(mbest)
        cand.sort(key=lambda q: q[0])
        best = cand[0] if cand else None
        # AMBIGUOUS means "which SIDE of the street", not "which house": the
        # runner-up in a terrace is the neighbour next door, whose frontage faces
        # the same way -- picking the nearer one is right and the layout sweep
        # sorts the position out. Real ambiguity is a frontage FACING BACK at us
        # from across the street, equally close.
        facing = best is not None and any(
            q[0] < best[0] + ASSIGN_MARGIN and q[1] != best[1]
            and q[4] * best[4] + q[5] * best[5] < -0.3 for q in cand[1:])
        if home is not None:
            if best is None:
                stats["no_street"] += 1               # inner-courtyard footprint
                continue
            stats["inside"] += 1
        elif best is None or best[0] > ASSIGN_FAR:
            # no modelled street frontage within reach: a business on a street
            # beyond the block, or a pin standing in the open (the 07-27 plaza
            # case). Either way there is nothing to attach it to -- dropped, and
            # counted separately from a real ambiguity so the two never blur.
            stats["unhosted"] += 1
            continue
        elif best[0] <= ASSIGN_NEAR:
            stats["near"] += 1
        elif facing:
            stats["ambiguous"] += 1                   # two facing frontages, no evidence
            continue
        else:
            stats["far_ok"] += 1
        _dist, hid, k, t, _nx, _ny = best
        per_edge.setdefault((hid, k), []).append(
            {"_t": t, "_w": UNIT_W.get(c["cat"], UNIT_W["unknown"]),
             "_px": c["x"], "_py": c["y"],
             "name": c["name"], "cat": c["cat"], "poi_type": c["poi_type"],
             "host": hid, "edge": k, "fill": False})

    # SPILL: a POI sitting inside a big block says which BUILDING it trades from,
    # not which of its frontages. 847120664 is a 49-vertex terrace whose Bute
    # Street side arrives as saw-tooth stubs, so eight shops all picked the same
    # 5.2 m run and the layout had to throw five away. When a run is over
    # capacity the excess moves to the same building's emptiest street frontage
    # (re-projected onto it) instead, and is only dropped if the whole building
    # is full.
    def _cap(L):
        return max(1, int((L + 0.35) / (UNIT_W_MIN + 0.35)))

    for hid in {h for h, _k in per_edge}:
        runs = st[hid]
        free = {k: _cap(runs[k][3]) - len(per_edge.get((hid, k), [])) for k in runs}
        for k in sorted(runs, key=lambda q: free[q]):
            us = per_edge.get((hid, k)) or []
            while free[k] < 0 and us:
                tgt = max(free, key=lambda q: free[q])
                if free[tgt] <= 0:
                    break
                # move the unit whose pin is FURTHEST from this run -- it had the
                # weakest claim to it in the first place
                ang2, _nx2, _ny2, L2, (ax, ay), _ks2 = runs[k]
                bx, by = ax + math.cos(ang2) * L2, ay + math.sin(ang2) * L2
                us.sort(key=lambda u: _proj(u["_px"], u["_py"], ax, ay, bx, by)[1])
                mv = us.pop()
                a2, _n2x, _n2y, L3, (cxr, cyr), _k3 = runs[tgt]
                dxr, dyr = cxr + math.cos(a2) * L3, cyr + math.sin(a2) * L3
                mv["_t"] = _proj(mv["_px"], mv["_py"], cxr, cyr, dxr, dyr)[0]
                mv["edge"] = tgt
                per_edge.setdefault((hid, tgt), []).append(mv)
                free[k] += 1
                free[tgt] -= 1
                stats["spilled"] += 1
            if us:
                per_edge[(hid, k)] = us
            else:
                # never leave an EMPTY frontage in the table: fill_gaps would
                # then dress a whole blank wall with anonymous shopfronts
                per_edge.pop((hid, k), None)

    # buildings the AGENT judged to have a shopfront (spec terrace.shopfront, read
    # off the street-view photo during generation) but for which Places returned
    # no business: dress their longest street frontage with ANONYMOUS units, so a
    # parade does not turn back into the old undivided glass band halfway down the
    # street. Their identity is unknown, not invented -- no sign is lettered.
    flagged = 0
    for hid, runs in st.items():
        if not runs or any(h == hid for h, _k in per_edge):
            continue
        if not _spec_shopfront(out, hid):
            continue
        k = max(runs, key=lambda q: runs[q][3])
        per_edge[(hid, k)] = []                    # empty -> fill_gaps dresses it
        flagged += 1
    if flagged:
        print(f"[shops] {flagged} buildings flagged shopfront by the agent with no "
              f"POI -> anonymous parade on their longest frontage")

    # lay each frontage out, fill the parade, then freeze to typed unit records
    _region = _area_region(out)
    _aw_ok = _region in EURO_AWNING_REGIONS
    if not _aw_ok:
        print(f"[shops] region '{_region}': category-default awnings OFF "
              "(photo-measured awnings only)")
    units, dropped_units = [], []
    for (hid, k), us in sorted(per_edge.items()):
        pts, mode = outlines[hid]
        ang, nx, ny, L, (x1, y1), ks = st[hid][k]
        fh = _floor_h(out, hid)
        for u in us:
            u["_w"] = max(UNIT_W_MIN, min(UNIT_W_MAX, min(u["_w"], L * 0.9)))
        us, cut = layout_edge(us, L)
        dropped_units += [(hid, u["name"], round(L, 1)) for u in cut]
        us = us + fill_gaps(us, L, hid, k)
        ex, ey = math.cos(ang), math.sin(ang)
        for u in sorted(us, key=lambda q: q["_s"]):
            s, w = u["_s"], u["_w"]
            cx, cy = x1 + ex * (s + w / 2), y1 + ey * (s + w / 2)
            p, src, conf = unit_params(u["name"], u["cat"], w, fh,
                                       awning_default_ok=_aw_ok)
            units.append({
                "id": "%s_e%d_%s" % (hid, k, u.get("sub") or ("%.0f" % (s * 10))),
                "host": hid, "edge": k, "edges": ks,
                "t0": round(s / L, 4), "t1": round((s + w) / L, 4),
                "x": round(cx, 2), "y": round(cy, 2),
                "ang": round(ang, 4),                 # edge bearing (unit runs along it)
                "nx": round(nx, 4), "ny": round(ny, 4),   # outward normal
                "name": u["name"], "category": u["cat"], "poi_type": u["poi_type"],
                "mode": mode,                         # which outline it sits on
                "params": p, "src": src, "conf": conf})

    for hid, nm, L in dropped_units:
        print(f"[shops]   dropped {nm!r} on {hid}: frontage {L} m already full")
    hosts = sorted({u["host"] for u in units})
    print(f"[shops] POIs: {stats['inside']} inside a footprint, {stats['near']} "
          f"projected from <{ASSIGN_NEAR:.0f} m, {stats['far_ok']} unambiguous "
          f"to {ASSIGN_FAR:.0f} m | dropped: {stats['unhosted']} with no modelled "
          f"frontage within {ASSIGN_FAR:.0f} m, {stats['ambiguous']} ambiguous "
          f"(facing frontages), {stats['no_street']} inside a footprint that has "
          f"no street edge")
    print(f"[shops] {len(units)} units ({sum(1 for u in units if u['name'])} named, "
          f"{sum(1 for u in units if not u['name'])} parade fill) on "
          f"{len(hosts)} buildings, {len(per_edge)} street edges")
    return {"units": units, "hosts": hosts}


def load_or_build(out, force=False):
    cache = os.path.join(out, "shops.json")
    if os.path.exists(cache) and not force:
        return json.load(open(cache))
    d = build(out, force)
    with open(cache, "w") as f:
        json.dump(d, f, indent=1)
    return d


def by_host(shops):
    """{building id: {edge index: [units]}} -- the form the renderer wants."""
    out = {}
    for u in shops["units"]:
        out.setdefault(u["host"], {}).setdefault(u["edge"], []).append(u)
    return out


def report(out):
    """Cross-check the POI layer against the agent's own street-view judgement
    (spec terrace.shopfront) -- two independent signals for the same question."""
    shops = load_or_build(out)
    hosts = {str(h) for h in shops["hosts"]}
    flagged = set()
    for f in glob.glob(os.path.join(out, "buildings", "*", "spec.json")):
        try:
            s = json.load(open(f))
        except Exception:
            continue
        if (s.get("terrace") or {}).get("shopfront"):
            flagged.add(os.path.basename(os.path.dirname(f)))
    print(f"[shops] agree (POI + agent): {len(hosts & flagged)}")
    print(f"[shops] POI only (agent missed the shopfront): {sorted(hosts - flagged)}")
    print(f"[shops] agent only (no POI returned): {len(flagged - hosts)} buildings")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="area directory (data/<area>)")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    if a.report:
        report(out)
        return
    d = load_or_build(out, a.force)
    print(f"[shops] shops.json: {len(d['units'])} units on {len(d['hosts'])} buildings")


if __name__ == "__main__":
    main()
