from pathlib import Path
import json

from streamlit.testing.v1 import AppTest

from dashboard_config import PANELS, default_config, encode_view

ROOT = Path(__file__).resolve().parents[1]


def app():
    return AppTest.from_file(str(ROOT / "home.py"), default_timeout=30).run()


def assert_healthy(application):
    assert not application.exception, [exception.message for exception in application.exception]


def type_search(application, query):
    # A free-text combobox entry arrives as a frontend string event. Some
    # AppTest versions cannot set a selectbox value outside its initial list.
    states = application._tree.get_widget_states()
    search_id = application.selectbox(key="search").proto.id
    state = next(widget for widget in states.widgets if widget.id == search_id)
    state.string_value = query
    application._run(states)
    return application


def select_points(application, chart, points):
    states = application._tree.get_widget_states()
    selection = next((widget for widget in states.widgets if widget.id == chart.proto.id), None)
    if selection is None:
        selection = states.widgets.add()
        selection.id = chart.proto.id
    selection.string_value = json.dumps({"selection": {"points": points, "point_indices": [], "box": [], "lasso": []}})
    application._run(states)
    assert_healthy(application)


def test_initial_dashboard():
    application = app()
    assert_healthy(application)
    assert application.metric[0].value == "10"
    assert application.metric[2].value == "17"
    assert len(application.tabs) == 4
    assert not application.get("file_uploader")
    assert application.radio(key="cfg_geo_style").value == "Map"


def test_filters_empty_results_and_reset():
    application = app()
    application.multiselect(key="filter_design").set_value(["Interventional"]).run()
    assert_healthy(application)
    assert application.metric[0].value == "4"
    application.multiselect(key="filter_countries").set_value(["Netherlands"]).run()
    assert_healthy(application)
    assert application.metric[0].value == "1"
    type_search(application, "No study matches this phrase")
    assert_healthy(application)
    assert application.metric[0].value == "0"
    reset = next(button for button in application.button if button.label == "Reset filters")
    reset.click().run()
    assert_healthy(application)
    assert application.metric[0].value == "10"


def test_search_accepts_suggestions_free_text_and_clearing():
    application = app()
    assert application.selectbox(key="search").value is None
    assert any("AURORA-RESP" in value for value in application.selectbox(key="search").options)
    assert any("Institution · Seabright" in value for value in application.selectbox(key="search").options)
    application.selectbox(key="search").set_value("AURORA-RESP").run()
    assert_healthy(application)
    assert application.metric[0].value == "1"
    application.selectbox(key="search").set_value("Elena Varga").run()
    assert_healthy(application)
    assert application.metric[0].value == "1"
    type_search(application, "household contact")
    assert_healthy(application)
    assert application.selectbox(key="search").value == "household contact"
    assert application.metric[0].value == "1"
    application.selectbox(key="search").set_value("Aster Research Council").run()
    assert_healthy(application)
    assert application.metric[0].value == "4"
    application.selectbox(key="search").set_value(None).run()
    assert_healthy(application)
    assert application.metric[0].value == "10"


def test_every_panel_and_display_mode():
    application = app()
    application.multiselect(key="cfg_panels").set_value(PANELS).run()
    application.selectbox(key="cfg_metric").set_value("Actual enrolment").run()
    application.radio(key="cfg_annual_style").set_value("Lines").run()
    application.radio(key="cfg_geo_style").set_value("Map").run()
    application.radio(key="cfg_layout").set_value("Full width").run()
    assert_healthy(application)
    assert len(application.get("plotly_chart")) == len(PANELS) + 1


def test_institution_dropdown_filters_the_whole_dashboard():
    application = app()
    institution = "Canal Clinical Trials Alliance"
    assert institution in application.multiselect(key="filter_institution").options
    assert len(application.multiselect(key="filter_institution").options) == 10
    application.multiselect(key="filter_institution").set_value([institution]).run()
    assert_healthy(application)
    assert application.metric[0].value == "1"
    assert application.metric[2].value == "3"
    assert application.selectbox(key="study_choice").options == ["PATHWAYS-ICU"]


def test_directory_csv_is_the_only_download_and_raw_source_views_are_not_rendered():
    application = app()
    assert_healthy(application)
    assert [element.proto.label for element in application.get("download_button")] == ["Export CSV"]
    assert not application.get("dataframe")  # No native table CSV-download toolbar.
    assert [element.proto.popover.label for element in application.get("popover")] == ["Customise"]
    rendered = " ".join(element.value for element in application.markdown)
    assert "metadata_knowledge_graph.ttl" not in rendered
    assert "https://example.org/comect-demo/" not in rendered
    assert "Data details & downloads" not in [element.label for element in application.expander]


def test_deep_link_restores_filters():
    config = default_config()
    config["filters"]["pathogen_groups"] = ["Bacteria"]
    config["metric"] = "Planned enrolment"
    application = AppTest.from_file(str(ROOT / "home.py"), default_timeout=30)
    application.query_params["view"] = encode_view(config)
    application.run()
    assert_healthy(application)
    assert application.metric[0].value == "4"
    assert application.selectbox(key="cfg_metric").value == "Planned enrolment"


def test_chart_selection_updates_global_filters():
    application = app()
    # Send a frontend selection event through Streamlit's widget protocol.
    chart = application.get("plotly_chart")[0]
    select_points(application, chart, [{"customdata": {"0": 2026}, "x": 2026}])
    assert application.metric[0].value == "3"
    assert application.multiselect(key="filter_year").value == [2026]
    select_points(application, application.get("plotly_chart")[0], [{"customdata": ["invalid"]}])
    assert application.multiselect(key="filter_year").value == [2026]
    select_points(application, application.get("plotly_chart")[0], [])
    assert application.metric[0].value == "10"
    assert application.multiselect(key="filter_year").value == []


def test_category_chart_events_update_the_matching_filters():
    application = app()
    application.multiselect(key="cfg_panels").set_value(["Geographical reach", "Research funders"]).run()
    cases = [(0, "countries", "Netherlands"), (1, "funders", "Aster Research Council")]
    for index, field, value in cases:
        chart = application.get("plotly_chart")[index]
        select_points(application, chart, [{"customdata": {"0": value}}])
        assert application.multiselect(key=f"filter_{field}").value == [value]
        assert int(application.metric[0].value) > 0
        next(button for button in application.button if button.label == "Reset filters").click().run()
        assert_healthy(application)
        assert application.metric[0].value == "10"


def test_donut_panels_use_sidebar_filters_instead_of_unsupported_selections():
    application = app()
    captions = [element.value for element in application.caption]
    assert "Use Recruitment status in the sidebar to filter" in captions
    assert "Self-reported sharing · Filter under More filters in the sidebar" in captions
    assert not application.get("plotly_chart")[2].proto.selection_mode
    assert not application.get("plotly_chart")[3].proto.selection_mode
    application.multiselect(key="filter_status").set_value(["Completed - trial ended as planned"]).run()
    assert_healthy(application)
    assert application.metric[0].value == "1"
    next(button for button in application.button if button.label == "Reset filters").click().run()
    application.multiselect(key="filter_sharing").set_value(["Yes - planned"]).run()
    assert_healthy(application)
    assert application.metric[0].value != "10"


def test_map_reset_clears_selection_and_keeps_other_filters():
    application = app()
    assert not any(button.label == "Reset selection" for button in application.button)
    application.multiselect(key="filter_design").set_value(["Interventional"]).run()
    map_chart = application.get("plotly_chart")[1]
    states = application._tree.get_widget_states()
    selection = states.widgets.add()
    selection.id = map_chart.proto.id
    selection.string_value = json.dumps({"selection": {"points": [{"customdata": ["Netherlands"]}],
                                                        "point_indices": [0], "box": [], "lasso": []}})
    application._run(states)
    assert_healthy(application)
    assert application.metric[0].value == "1"
    assert application.multiselect(key="filter_countries").value == ["Netherlands"]
    selected_map_id = application.get("plotly_chart")[1].proto.id
    application.button(key="reset_country_selection").click().run()
    assert_healthy(application)
    assert application.multiselect(key="filter_countries").value == []
    assert application.multiselect(key="filter_design").value == ["Interventional"]
    assert application.metric[0].value == "4"
    reset_map = application.get("plotly_chart")[1]
    assert reset_map.proto.id != selected_map_id
    assert reset_map.value["selection"]["points"] == []
    assert not any(button.label == "Reset selection" for button in application.button)
