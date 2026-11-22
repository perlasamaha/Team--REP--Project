"""
make_snapshots.py -- turn saved raw Overpass responses into snapshot files.

Input : one text file made of sections. Each section is a label line such as
        "naccache:" followed by the raw Overpass JSON response for that region.
Output: snapshots/<region>.json  ->  {"region", "saved_at", "count", "roads"}

Usage : python make_snapshots.py regions.txt
"""
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from api_client import REGIONS, normalize_way

LABEL = re.compile(r"(?m)^([A-Za-z_ ]+):[ \t]*$")
ALIASES = {"beit_al_chaar": "beit_chaar"}   # label in the file -> key in REGIONS
OUT_DIR = Path("snapshots")


def region_key(label):
    key = label.strip().lower().replace(" ", "_")
    return ALIASES.get(key, key)


def read_sections(path):
    """Yield (region_key, overpass_response_dict) for each section in the file."""
    text = Path(path).read_text(encoding="utf-8")
    decoder = json.JSONDecoder()
    for m in LABEL.finditer(text):
        start = m.end()
        while text[start].isspace():
            start += 1
        response, _ = decoder.raw_decode(text, start)
        yield region_key(m.group(1)), response


def main(path):
    OUT_DIR.mkdir(exist_ok=True)
    seen = set()
    for key, response in read_sections(path):
        if key not in REGIONS:
            sys.exit(f"Unknown region label: {key!r}")
        roads = [normalize_way(el) for el in response.get("elements", [])
                 if el.get("type") == "way"]
        if not roads:
            sys.exit(f"{key}: no roads found, refusing to write an empty snapshot")
        stamp = response["osm3s"]["timestamp_osm_base"]       # e.g. 2026-11-21T13:18:50Z
        saved_at = datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp()
        snapshot = {"region": key, "saved_at": saved_at,
                    "count": len(roads), "roads": roads}
        out = OUT_DIR / f"{key}.json"
        out.write_text(json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")),
                       encoding="utf-8")
        seen.add(key)
        print(f"{key:12} {len(roads):5} roads -> {out}")
    missing = set(REGIONS) - seen
    if missing:
        print("WARNING: no section found for:", ", ".join(sorted(missing)))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python make_snapshots.py regions.txt")
    main(sys.argv[1])