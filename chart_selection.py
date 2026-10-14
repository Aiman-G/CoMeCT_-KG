"""Translate Plotly selection events into valid dashboard filter values."""
from collections.abc import Mapping


def selection_filter_values(state, field, allowed_values):
    """Return selected values, or None when the event cannot be interpreted.

    Plotly 6 can send a numeric customdata row as {"0": value}, while other
    traces send a list. Invalid events leave the current filter unchanged;
    an explicitly empty selection clears it.
    """
    if not isinstance(state, Mapping) or not isinstance(state.get("selection"), Mapping):
        return None
    points = state["selection"].get("points")
    if not isinstance(points, (list, tuple)):
        return None
    allowed = set(allowed_values)
    values = []
    for point in points:
        if not isinstance(point, Mapping):
            return None
        custom = point.get("customdata")
        if isinstance(custom, Mapping):
            value = custom.get("0", custom.get(0))
        elif isinstance(custom, (list, tuple)):
            value = custom[0] if custom else None
        else:
            value = custom
        if field == "year":
            if value is None:
                value = point.get("x")
            if isinstance(value, bool):
                return None
            try:
                year = int(value)
            except (TypeError, ValueError, OverflowError):
                return None
            if not isinstance(value, str) and value != year:
                return None
            value = year
        elif not isinstance(value, str):
            return None
        if value not in allowed:
            return None
        if value not in values:
            values.append(value)
    return values
