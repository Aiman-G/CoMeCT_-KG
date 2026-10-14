from pathlib import Path

from charts import map_figure
from graph_data import load_graph

ROOT = Path(__file__).resolve().parents[1]


def test_country_shading_keeps_all_locations_and_source_counts():
    data = load_graph((ROOT / "metadata_knowledge_graph.ttl").read_bytes())
    figure, omitted = map_figure(data.studies, "studies")
    assert omitted == []
    assert [trace.type for trace in figure.data] == ["choropleth"]
    countries = dict(zip(figure.data[0].locations, figure.data[0].z))
    assert len(countries) == 17
    assert countries["NLD"] == 2
    assert countries["DEU"] == 2
    assert countries["KEN"] == 1
    assert sum(countries.values()) == 22  # Multi-country studies contribute once per country.
    assert ["Netherlands"] in figure.data[0].customdata
    assert figure.data[0].colorbar.title.text == "Studies"


def test_country_shading_tracks_the_selected_enrolment_measure():
    data = load_graph((ROOT / "metadata_knowledge_graph.ttl").read_bytes())
    only_aurora = data.studies.loc[data.studies.id == "SYN-0001"]
    figure, _ = map_figure(only_aurora, "actual")
    assert set(figure.data[0].locations) == {"DEU", "NLD"}
    assert list(figure.data[0].z) == [420, 420]
    assert figure.data[0].colorbar.title.text == "Actual enrolment"
