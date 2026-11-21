"""
api_client.py -- ALL calls to the Overpass API live here.
Raw OpenStreetMap data goes in, clean dictionaries come out.
"""
import requests

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
TIMEOUT = 30  # seconds for our HTTP request
HEADERS = {"User-Agent": "Tari2na-student-project/1.0"}

MAIN_ROAD_TYPES = ["motorway", "trunk", "primary", "secondary",
                   "tertiary", "unclassified", "residential"]
SERVICE_TYPE = "service"

REGIONS = {
    "naccache": {"label": "Naccache-Antelias", "bbox": (33.905, 35.570, 33.935, 35.600)},
    "jounieh":  {"label": "Jounieh",           "bbox": (33.960, 35.590, 34.000, 35.650)},
    "jbeil":    {"label": "Jbeil (Byblos)",    "bbox": (34.105, 35.630, 34.145, 35.675)},
    "batroun":  {"label": "Batroun",           "bbox": (34.240, 35.645, 34.270, 35.675)},
    "zahle":    {"label": "Zahle",             "bbox": (33.830, 35.880, 33.865, 35.925)},
}


class OverpassError(Exception):
    """Raised when Overpass fails (timeout, bad status, bad JSON, remark)."""


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


def run_query(query):
    """Send a query to Overpass and return the parsed JSON."""
    try:
        r = requests.post(OVERPASS_URL, data={"data": query},
                          headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
    except requests.Timeout:        # specific first
        raise OverpassError("The map data service took too long to respond.")
    except ValueError:              # bad JSON: must come before RequestException
        raise OverpassError("The map data service returned an invalid response.")
    except requests.RequestException:   # general catch-all last
        raise OverpassError("The map data service is unavailable right now.")
    if "remark" in data:
        raise OverpassError("The map data service is busy. Please try again in a minute.")
    return data


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
        "name_ar": tags.get("name:ar") or tags.get("name"),
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
    """All roads in a region, normalized. Filtering happens later, in Python."""
    bbox = REGIONS[region]["bbox"]
    raw = run_query(build_query(bbox, include_service))
    return [normalize_way(el) for el in raw.get("elements", [])
            if el.get("type") == "way"]


def get_road(osm_id):
    """One road by OSM way id, or None if Overpass found nothing."""
    query = f"[out:json][timeout:25];\nway({int(osm_id)});\nout geom;"
    raw = run_query(query)
    elements = raw.get("elements", [])
    return normalize_way(elements[0]) if elements else None


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


def search(query):
    return []


def get_item(item_id):
    return None