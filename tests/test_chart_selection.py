from chart_selection import selection_filter_values


def event(*points):
    return {"selection": {"points": list(points)}}


def test_year_selection_accepts_browser_object_rows_and_list_rows():
    # Captured from an actual Plotly 6 / Streamlit 1.48 browser click.
    state = event({"x": 2022, "y": 1, "customdata": {"0": 2022}, "point_number": 0},
                  {"customdata": [2026]}, {"customdata": {"0": 2022}})
    assert selection_filter_values(state, "year", [2022, 2026]) == [2022, 2026]
    assert selection_filter_values(event({"x": 2026}), "year", [2026]) == [2026]


def test_category_selection_preserves_full_labels_for_every_filter():
    for field, value in (("countries", "Netherlands"), ("funders", "Aster Research Council"),
                         ("status", "Completed - trial ended as planned"), ("sharing", "Yes - planned")):
        for custom in ([value], {"0": value}, value):
            assert selection_filter_values(event({"customdata": custom}), field, [value]) == [value]


def test_empty_selection_clears_and_invalid_events_preserve_filters():
    assert selection_filter_values(event(), "year", [2026]) == []
    for state in ({}, {"selection": {"points": None}}, event({"customdata": []}),
                  event({"customdata": {"unexpected": 2026}}), event({"customdata": ["invalid"]}),
                  event({"customdata": [2026.5]}), event({"customdata": [True]}),
                  event({"customdata": [2029]}), event(None)):
        assert selection_filter_values(state, "year", [2026]) is None
    assert selection_filter_values(event({"customdata": ["Unknown"]}), "countries", ["Netherlands"]) is None
