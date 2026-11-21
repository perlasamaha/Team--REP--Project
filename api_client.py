"""
api_client.py -- ALL calls to the Overpass API live here.
Raw OpenStreetMap data goes in, clean dictionaries come out.
"""
import logging
import re
import time

import requests

OVERPASS_SERVERS = [
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass-api.de/api/interpreter",
]
TIMEOUT = 9  # seconds per server; 3 x 9 = 27 s worst case, under gunicorn's 30 s
HEADERS = {"User-Agent": "Tari2na-student-project/1.0"}

log = logging.getLogger(__name__)

MAIN_ROAD_TYPES = ["motorway", "trunk", "primary", "secondary",
                   "tertiary", "unclassified", "residential"]
SERVICE_TYPE = "service"

REGIONS = {
    "naccache":   {"label": "Naccache",          "bbox": (33.905, 35.570, 33.935, 35.600)},
    "jounieh":    {"label": "Jounieh",           "bbox": (33.960, 35.590, 34.000, 35.650)},
    "jbeil":      {"label": "Jbeil (Byblos)",    "bbox": (34.105, 35.630, 34.145, 35.675)},
    "batroun":    {"label": "Batroun",           "bbox": (34.240, 35.645, 34.270, 35.675)},
    "zahle":      {"label": "Zahle",             "bbox": (33.830, 35.880, 33.865, 35.925)},
    "achrafieh":  {"label": "Achrafieh",         "bbox": (33.880, 35.510, 33.900, 35.535)},
    "tripoli":    {"label": "Trablos (Tripoli)", "bbox": (34.425, 35.825, 34.450, 35.860)},
    "saida":      {"label": "Saida (Sidon)",     "bbox": (33.545, 35.355, 33.575, 35.395)},
    "sour":       {"label": "Sour (Tyre)",       "bbox": (33.260, 35.180, 33.285, 35.215)},
    "baalbek":    {"label": "Baalbek",           "bbox": (33.995, 36.195, 34.015, 36.225)},
    "beit_chaar": {"label": "Beit el Chaar",     "bbox": (33.920, 35.610, 33.935, 35.630)},
}

SURFACES = {
    "asphalt":  {"en": "Asphalt",    "ar": "زفت"},
    "concrete": {"en": "Concrete",   "ar": "بيتون"},
    "paved":    {"en": "Paved",      "ar": "طريق مزفّتة"},
    "unpaved":  {"en": "Unpaved",    "ar": "طريق ترابية"},
    "gravel":   {"en": "Gravel",     "ar": "بحص"},
    "unknown":  {"en": "Not tagged", "ar": "غير محدد"},
}

SMOOTHNESS = {
    "good":         {"en": "Good",         "ar": "منيحة"},
    "intermediate": {"en": "Intermediate", "ar": "وسط"},
    "bad":          {"en": "Bad",          "ar": "سيئة"},
    "unknown":      {"en": "Not tagged",   "ar": "غير محدد"},
}

CACHE_TTL = 30 * 60   # seconds an entry counts as fresh
_cache = {}           # key (region, include_service) -> (saved_at, roads)

ARABIC_LETTERS = re.compile(r"[\u0600-\u06FF]")


class OverpassError(Exception):
    """Raised when Overpass fails (timeout, bad status, bad JSON, remark, empty)."""


class BadQueryError(OverpassError):
    """Our own query was rejected (HTTP 400). Another server won't help."""


def build_query(bbox, include_service=False):
    """Build an Overpass QL string. Only validated values go in here."""
    types = MAIN_ROAD_TYPES + ([SERVICE_TYPE] if include_service else [])
    type_regex = "|".join(types)
    south, west, north, east = bbox
    return (
        "[out:json][timeout:25];\n"
        f'way["highway"~"^({type_regex})$"]({south},{west},{north},{east});\n'
        "out geom;"
    )


def _ask_server(url, query, allow_empty=False):
    """Send the query to ONE server. Raise OverpassError on any failure."""
    try:
        r = requests.post(url, data={"data": query},
                          headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
    except requests.Timeout as e:
        log.warning("Overpass timeout after %ss (%s): %r", TIMEOUT, url, e)
        raise OverpassError("The map data service took too long to respond.")
    except ValueError:
        log.warning("Overpass returned invalid JSON (%s)", url)
        raise OverpassError("The map data service returned an invalid response.")
    except requests.HTTPError as e:
        status = e.response.status_code if e.response is not None else None
        log.warning("Overpass HTTP error %s (%s)", status, url)
        if status == 400:
            raise BadQueryError("The map query was rejected.")
        raise OverpassError("The map data service is unavailable right now.")
    except requests.RequestException as e:
        log.warning("Overpass request failed (%s): %r", url, e)
        raise OverpassError("The map data service is unavailable right now.")
    if "remark" in data:
        log.warning("Overpass remark: %s", data["remark"])
        raise OverpassError("The map data service is busy. Please try again in a minute.")
    if not allow_empty and not data.get("elements"):
        log.warning("Overpass returned no elements (%s)", url)
        raise OverpassError("The map data service returned no data.")
    return data


def run_query(query, allow_empty=False):
    """Try each server in order; stop at the first that answers."""
    last_error = None
    for url in OVERPASS_SERVERS:
        try:
            return _ask_server(url, query, allow_empty)
        except BadQueryError:
            raise
        except OverpassError as e:
            last_error = e
    raise last_error


def _arabic_name(tags):
    """name:ar if the road has it; otherwise the plain name, but only
    if it really contains Arabic letters."""
    name_ar = tags.get("name:ar")
    if name_ar:
        return name_ar
    name = tags.get("name")
    if name and ARABIC_LETTERS.search(name):
        return name
    return None


def normalize_way(el):
    """Turn one raw OSM element into our clean road dictionary."""
    tags = el.get("tags", {})
    b = el.get("bounds")
    center = None
    if b:
        center = {"lat": (b["minlat"] + b["maxlat"]) / 2,
                  "lon": (b["minlon"] + b["maxlon"]) / 2}

    name_en = tags.get("name:en")
    name_fr = tags.get("name:fr")
    return {
        "osm_type": el["type"],
        "osm_id": el["id"],
        "name": name_en or tags.get("name") or name_fr,
        "name_ar": _arabic_name(tags),
        "name_en": name_en,
        "name_fr": name_fr,
        "ref": tags.get("ref"),
        "highway": tags.get("highway"),
        "surface": tags.get("surface"),
        "smoothness": tags.get("smoothness"),
        "oneway": tags.get("oneway") == "yes",
        "coordinates": [[p["lat"], p["lon"]] for p in el.get("geometry", [])],
        "center": center,
    }


def get_roads(region, include_service=False):
    """Return (roads, saved_at, stale). Uses the cache before calling Overpass."""
    key = (region, include_service)
    now = time.time()
    entry = _cache.get(key)

    # 1. fresh entry: no Overpass call at all
    if entry and now - entry[0] < CACHE_TTL:
        return entry[1], entry[0], False

    # 2. no entry, or expired: ask Overpass
    try:
        bbox = REGIONS[region]["bbox"]
        raw = run_query(build_query(bbox, include_service))
    except OverpassError:
        # 3. Overpass failed: serve the old entry if we have one
        if entry:
            return entry[1], entry[0], True
        raise

    roads = [normalize_way(el) for el in raw.get("elements", [])
             if el.get("type") == "way"]
    _cache[key] = (now, roads)
    return roads, now, False


def get_road(osm_id):
    """One road by OSM way id. Raises OverpassError if Overpass gives no usable answer."""
    query = f"[out:json][timeout:25];\nway({int(osm_id)});\nout geom;"
    raw = run_query(query)
    return normalize_way(raw["elements"][0])


def _matches(value, wanted):
    if wanted == "unknown":
        return value is None
    return value == wanted


def filter_roads(roads, surface=None, smoothness=None, name=None):
    """Filter normalized roads. 'unknown' matches roads missing that tag."""
    result = []
    for r in roads:
        if surface and not _matches(r["surface"], surface):
            continue
        if smoothness and not _matches(r["smoothness"], smoothness):
            continue
        if name:
            names = [r["name"], r["name_ar"], r["name_en"], r["name_fr"]]
            if not any(n and name.lower() in n.lower() for n in names):
                continue
        result.append(r)
    return result