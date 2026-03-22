# app/scripts/update_vessel_types.py
import json
import sys
import os
from urllib.request import urlopen, Request
import gzip
import io

# Lisätään juurihakemisto polkuun, jotta 'app' löytyy
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app import db
from app.config import settings

DIGITRAFFIC_URL = "https://meri.digitraffic.fi/api/port-call/v1/code-descriptions"

# Alkuperäinen tyylitys utils.js:stä
INITIAL_STYLING = {
  "passenger": {
    "color": "#2ed573",
    "category": "passenger",
    "codes": ["10", "20", "30"]
  },
  "cargo": {
    "color": "#4a9eff",
    "category": "cargo",
    "codes": ["40", "44", "50", "60", "70"]
  },
  "tanker": {
    "color": "#ff6b6b",
    "category": "tanker",
    "range": [80, 89]
  },
  "tugboat": {
    "color": "#f9ca24",
    "category": "tugboat",
    "codes": ["91"]
  },
  "barge": {
    "color": "#a29bfe",
    "category": "barge",
    "codes": ["93", "94", "95", "96", "97"]
  },
  "other": {
    "color": "#8899aa",
    "category": "Other",
    "codes": ["90", "99"]
  }
}

def get_styling(code_str: str):
    if not code_str:
        return INITIAL_STYLING["other"]
    try:
        code = int(code_str)
    except ValueError:
        return INITIAL_STYLING["other"]

    for key, style in INITIAL_STYLING.items():
        if "range" in style:
            low, high = style["range"]
            if low <= code <= high:
                return style
        if "codes" in style and code_str in style["codes"]:
            return style
    
    return INITIAL_STYLING["other"]

def update_vessel_types():
    print(f"Fetching vessel types from {DIGITRAFFIC_URL}...")
    try:
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "Digitraffic-User": settings.DIGITRAFFIC_USER,
        }
        req = Request(DIGITRAFFIC_URL, headers=headers)
        with urlopen(req, timeout=10.0) as response:
            if response.status != 200:
                print(f"Error fetching data: HTTP {response.status}")
                return
            
            content_encoding = response.getheader("Content-Encoding")
            raw_data = response.read()

            if content_encoding == "gzip":
                with gzip.GzipFile(fileobj=io.BytesIO(raw_data)) as f:
                    data = json.loads(f.read().decode("utf-8"))
            else:
                data = json.loads(raw_data.decode("utf-8"))
    except Exception as e:
        print(f"Error fetching data: {e}")
        import traceback
        traceback.print_exc()
        return

    vessel_types = data.get("vesselTypes", [])
    print(f"Found {len(vessel_types)} vessel types. Updating database...")

    for vt in vessel_types:
        code = vt.get("code")
        desc_fi = vt.get("descriptionFi")
        desc_en = vt.get("descriptionEn")
        
        style = get_styling(code)
        
        print(f"  - Updating {code}: {desc_en} ({style['category']})")
        db.upsert_vessel_type(
            code=code,
            desc_fi=desc_fi,
            desc_en=desc_en,
            color=style["color"],
            category=style["category"]
        )

    print("Vessel types updated successfully.")

if __name__ == "__main__":
    update_vessel_types()
