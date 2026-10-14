"""Portable dashboard views with validated settings and atomic local persistence."""
import base64
import json
import os
from pathlib import Path
import tempfile

from graph_data import FILTER_FIELDS, options

PANELS = ["Annual activity", "Geographical reach", "Recruitment status", "Data sharing",
          "Research funders", "Reported standards", "Enrolment", "Study timeline"]
DEFAULT_PANELS = PANELS[:4]
METRICS = {"Study count": "studies", "Planned enrolment": "planned", "Actual enrolment": "actual"}
GROUPS = {"Pathogen group": "pathogen_groups", "Study design": "design", "Recruitment status": "status"}


def default_config():
    return {"version": 1, "filters": {field: [] for field in FILTER_FIELDS}, "search": "",
            "panels": DEFAULT_PANELS.copy(), "metric": "Study count", "group": "Pathogen group",
            "annual_style": "Stacked bars", "geo_style": "Map", "layout": "Two columns"}


def validate_config(value: dict, frame):
    if not isinstance(value, dict) or value.get("version") != 1:
        raise ValueError("Choose a dashboard configuration with version 1.")
    result = default_config()
    filters = value.get("filters", {})
    if not isinstance(filters, dict):
        raise ValueError("Configuration filters must be an object.")
    for field in FILTER_FIELDS:
        selected = filters.get(field, [])
        if not isinstance(selected, list) or any(not isinstance(item, (str, int)) for item in selected):
            raise ValueError(f"Invalid filter values for {field}.")
        allowed = options(frame, field)
        result["filters"][field] = list(dict.fromkeys(item for item in selected if item in allowed))
    search = value.get("search", "")
    if not isinstance(search, str) or len(search) > 500:
        raise ValueError("Search text must be a string of 500 characters or fewer.")
    result["search"] = search
    panels = value.get("panels", DEFAULT_PANELS)
    if not isinstance(panels, list) or any(panel not in PANELS for panel in panels):
        raise ValueError("Configuration contains an unknown chart.")
    result["panels"] = list(dict.fromkeys(panels))
    for field, allowed in {"metric": list(METRICS), "group": list(GROUPS),
                           "annual_style": ["Stacked bars", "Lines"], "geo_style": ["Bars", "Map"],
                           "layout": ["Two columns", "Full width"]}.items():
        selected = value.get(field, result[field])
        if selected not in allowed:
            raise ValueError(f"Invalid dashboard setting: {field}.")
        result[field] = selected
    return result


def encode_view(config):
    return base64.urlsafe_b64encode(json.dumps(config, separators=(",", ":")).encode()).decode()


def decode_view(encoded):
    if len(encoded) > 65536:
        raise ValueError("This dashboard link is too long.")
    try:
        return json.loads(base64.urlsafe_b64decode(encoded).decode())
    except (ValueError, UnicodeError) as error:
        raise ValueError("This dashboard link contains an invalid configuration.") from error


def read_views(path: Path):
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("The saved views file must contain an object.")
    return value


def save_view(path: Path, name: str, config: dict):
    name = name.strip()
    if not name or len(name) > 60:
        raise ValueError("Give your view a name of 1–60 characters.")
    views = read_views(path)
    if name not in views and len(views) >= 20:
        raise ValueError("The local dashboard already has 20 saved views. Reuse an existing view name.")
    views[name] = config
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(views, handle, indent=2)
        temporary = handle.name
    os.replace(temporary, path)
