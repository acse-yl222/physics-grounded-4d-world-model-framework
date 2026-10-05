"""img2city/imagery/maps_fetch.py -- fetch Google Maps inputs for one building.

  satellite.png   -- top-down (footprint / plan + scale)
  streetview.png  -- ground-level facade (height / floors / style)

Setup (you do once; this code never sees or stores the key):
  Cloud project + billing; enable Maps Static, Street View Static, Geocoding;
  create + restrict an API key; export GOOGLE_MAPS_API_KEY=...

Street view tips:
  * By default the camera = the nearest panorama to the building, aimed
    automatically AT the building. For buildings set back from the road
    (Queen's Tower), pass a VANTAGE point that has line-of-sight with
    --sv-lat/--sv-lng (read it off Google Maps Street View in the browser),
    and raise --pitch because the building is tall.
  * --sweep grabs 8 headings so you can pick the best one.

Examples:
  python -m img2city.imagery.maps_fetch --query "Queen's Tower, Imperial College London" --pitch 25 --out data/queens_tower
  python -m img2city.imagery.maps_fetch --query "Queen's Tower, Imperial College London" \
      --sv-lat 51.4987 --sv-lng -0.1746 --pitch 25 --out data/queens_tower   # vantage from browser
  python -m img2city.imagery.maps_fetch --query "Queen's Tower, Imperial College London" \
      --sv-lat 51.4987 --sv-lng -0.1746 --sweep --pitch 25 --out data/qt_sweep
"""
from __future__ import annotations
import argparse
import json
import math
import os
import re
import urllib.parse
import urllib.request

GEOCODE = "https://maps.googleapis.com/maps/api/geocode/json"
STATICMAP = "https://maps.googleapis.com/maps/api/staticmap"
STREETVIEW = "https://maps.googleapis.com/maps/api/streetview"
STREETVIEW_META = "https://maps.googleapis.com/maps/api/streetview/metadata"



# Places returns business names in the local script: a Paris restaurant came
# back with CJK characters, and the log line carried them into the run record.
# The repository and the demo site are English-only, so names are folded to
# Latin before they are printed. Only the printed form changes -- the stored
# name is untouched, because the shop really is called that.
_NON_LATIN = re.compile(r'[\u2e80-\u9fff\uac00-\ud7ff\u3040-\u30ff\uff00-\uffef]+')


def latin_only(name, n=28):
    """A log-safe form of an external name: non-Latin scripts dropped,
    accented Latin (DEJEUNER -> DEJEUNER, Muller) kept."""
    t = _NON_LATIN.sub('', str(name or '')).strip()
    return (t[:n] or '(non-Latin name)')


def _key():
    k = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not k:
        raise SystemExit("Set GOOGLE_MAPS_API_KEY in your environment first.")
    return k


def _get(url, params, out_path=None):
    full = f"{url}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(full, timeout=30) as r:
        data = r.read()
    if out_path:
        with open(out_path, "wb") as f:
            f.write(data)
        return out_path
    return data


PLACES_NEARBY = "https://places.googleapis.com/v1/places:searchNearby"


def places_nearby(lat, lng, radius=60.0, included_types=None, max_results=10):
    """Places API (New) searchNearby around a point. Returns a list of
    {name, primary_type, types, lat, lng}. included_types=None uses a curated
    set of building-FUNCTION types (station/museum/worship/school/...)."""
    # NOTE: types must be from Places(New) Table A -- e.g. worship is
    # church/mosque/synagogue/hindu_temple (NO generic "place_of_worship"), and
    # one bad type 400s the whole request.
    if included_types is None:
        included_types = ["subway_station", "train_station", "light_rail_station",
                          "transit_station", "bus_station", "museum",
                          "church", "mosque", "synagogue", "hindu_temple",
                          "school", "university", "hospital", "hotel", "stadium",
                          "library", "city_hall", "movie_theater", "gas_station"]
    body = json.dumps({
        "includedTypes": included_types,
        "maxResultCount": max_results,
        "locationRestriction": {"circle": {
            "center": {"latitude": lat, "longitude": lng},
            "radius": float(radius)}}}).encode()
    req = urllib.request.Request(PLACES_NEARBY, data=body, method="POST", headers={
        "Content-Type": "application/json", "X-Goog-Api-Key": _key(),
        "X-Goog-FieldMask": "places.displayName,places.types,"
                            "places.primaryType,places.location"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            j = json.load(r)
    except Exception:
        return []
    out = []
    for p in j.get("places", []):
        loc = p.get("location", {})
        out.append({"name": p.get("displayName", {}).get("text", ""),
                    "primary_type": p.get("primaryType", ""),
                    "types": p.get("types", []),
                    "lat": loc.get("latitude"), "lng": loc.get("longitude")})
    return out


def _bearing(lat1, lng1, lat2, lng2):
    """Compass bearing in degrees from point 1 toward point 2."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lng2 - lng1)
    x = math.sin(dl) * math.cos(p2)
    y = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def geocode(query):
    j = json.loads(_get(GEOCODE, {"address": query, "key": _key()}))
    if not j.get("results"):
        raise SystemExit(f"Geocode failed: {j.get('status')} {j.get('error_message','')}")
    loc = j["results"][0]["geometry"]["location"]
    return loc["lat"], loc["lng"]


def sv_metadata(lat, lng, radius, key):
    return json.loads(_get(STREETVIEW_META,
                           {"location": f"{lat},{lng}", "radius": radius, "key": key}))


def fetch(lat, lng, out_dir, heading=None, zoom=19, sv_lat=None, sv_lng=None,
          pitch=15.0, fov=90.0, radius=80, sweep=False):
    os.makedirs(out_dir, exist_ok=True)
    k = _key()

    sat = _get(STATICMAP, {"center": f"{lat},{lng}", "zoom": zoom, "size": "640x640",
                           "scale": 2, "maptype": "satellite", "key": k},
               os.path.join(out_dir, "satellite.png"))
    print("saved:", sat)

    cam_lat = sv_lat if sv_lat is not None else lat
    cam_lng = sv_lng if sv_lng is not None else lng
    meta = sv_metadata(cam_lat, cam_lng, radius, k)
    if meta.get("status") != "OK":
        print(f"  [street view] no panorama within {radius} m of ({cam_lat},{cam_lng}): "
              f"{meta.get('status')} -- move the vantage or raise --radius")
        return sat, None
    pano = meta["location"]
    print(f"  [street view] pano at {pano['lat']:.5f},{pano['lng']:.5f} (date {meta.get('date','?')})")

    def shot(hd, name):
        return _get(STREETVIEW, {"location": f"{pano['lat']},{pano['lng']}", "size": "640x640",
                                 "heading": round(hd, 1), "pitch": pitch, "fov": fov,
                                 "source": "outdoor", "key": k},
                    os.path.join(out_dir, name))

    if sweep:
        files = [shot(h, f"streetview_h{h:03d}.png") for h in range(0, 360, 45)]
        print("saved sweep:", ", ".join(os.path.basename(f) for f in files))
        return sat, files

    hd = heading if heading is not None else _bearing(pano["lat"], pano["lng"], lat, lng)
    sv = shot(hd, "streetview.png")
    print(f"  [street view] heading {hd:.0f}deg, pitch {pitch:.0f} -> {sv}")
    return sat, sv


def main():
    ap = argparse.ArgumentParser(description="Fetch Google Maps satellite + street view for one building")
    ap.add_argument("--query", help="address / place name to geocode")
    ap.add_argument("--lat", type=float)
    ap.add_argument("--lng", type=float)
    ap.add_argument("--heading", type=float, default=None,
                    help="street-view heading (deg); default = auto-aim at the building")
    ap.add_argument("--sv-lat", type=float, default=None, help="street-view vantage lat (a line-of-sight spot)")
    ap.add_argument("--sv-lng", type=float, default=None, help="street-view vantage lng")
    ap.add_argument("--pitch", type=float, default=15.0, help="street-view pitch up (deg); tall buildings need more")
    ap.add_argument("--fov", type=float, default=90.0, help="field of view (smaller = zoom in)")
    ap.add_argument("--radius", type=int, default=80, help="panorama search radius (m)")
    ap.add_argument("--zoom", type=int, default=19, help="satellite zoom (18-20)")
    ap.add_argument("--sweep", action="store_true", help="grab 8 headings so you can pick the best")
    ap.add_argument("--out", required=True, help="building directory (data/<building>)")
    a = ap.parse_args()

    if a.lat is not None and a.lng is not None:
        lat, lng = a.lat, a.lng
    elif a.query:
        lat, lng = geocode(a.query)
        print(f"geocoded '{a.query}' -> {lat},{lng}")
    else:
        raise SystemExit("Give --query or both --lat and --lng")

    fetch(lat, lng, a.out, a.heading, a.zoom, a.sv_lat, a.sv_lng,
          a.pitch, a.fov, a.radius, a.sweep)


if __name__ == "__main__":
    main()
