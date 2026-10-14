from datetime import date
from io import BytesIO
from pathlib import Path

import pandas as pd

from charts import network_figure, timeline_figure
from graph_data import EX, load_graph
from graph_data import filter_studies
from tables import study_directory_csv, study_table_html

ROOT = Path(__file__).resolve().parents[1]


def test_timeline_preserves_study_periods_and_marks_the_reference_date():
    data = load_graph((ROOT / "metadata_knowledge_graph.ttl").read_bytes())
    figure, omitted = timeline_figure(data.studies, date(2026, 10, 14))
    assert omitted == 0
    assert sum(len(trace.y) for trace in figure.data) == 10
    rows = {name: (start, duration) for trace in figure.data for name, start, duration in zip(trace.y, trace.base, trace.x)}
    start, duration = rows["VAX-BRIDGE"]
    assert pd.Timestamp(start) == pd.Timestamp("2027-01-01")
    assert pd.Timestamp(start) + pd.Timedelta(milliseconds=duration) == pd.Timestamp("2028-10-31")
    assert pd.Timestamp(figure.layout.shapes[0].x0).date() == date(2026, 10, 14)


def test_timeline_omits_invalid_or_missing_dates():
    data = load_graph((ROOT / "metadata_knowledge_graph.ttl").read_bytes())
    frame = data.studies.iloc[:2].copy()
    frame.loc[frame.index[0], "end_date"] = pd.NaT
    frame.loc[frame.index[1], "end_date"] = frame.loc[frame.index[1], "start_date"] - pd.Timedelta(days=1)
    figure, omitted = timeline_figure(frame, date(2026, 10, 14))
    assert figure is None
    assert omitted == 2


def test_study_summary_escapes_text_and_excludes_private_source_fields():
    data = load_graph((ROOT / "metadata_knowledge_graph.ttl").read_bytes())
    frame = data.studies.iloc[:1].copy()
    frame.loc[frame.index[0], "title"] = '<script>alert("test")</script>'
    html = study_table_html(frame)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "https://example.org/comect-demo/" not in html
    assert "Download" not in html
    assert "420" in html and "2,400" in html
    assert "Seabright Respiratory Research Institute" in html


def test_graph_hover_exposes_labels_without_raw_identifiers():
    data = load_graph((ROOT / "metadata_knowledge_graph.ttl").read_bytes())
    figure, _, _ = network_figure(data.graph, data.studies.uri.tolist(), [EX.fundedBy])
    assert "https://example.org/comect-demo/" not in figure.to_json()


def test_directory_csv_contains_only_filtered_summary_fields_in_display_order():
    data = load_graph((ROOT / "metadata_knowledge_graph.ttl").read_bytes())
    filtered = filter_studies(data.studies, {"countries": ["Netherlands"]}).sort_values("acronym")
    content = study_directory_csv(filtered)
    directory = pd.read_csv(BytesIO(content), encoding="utf-8-sig")
    assert directory.Study.tolist() == ["AURORA-RESP", "PATHWAYS-ICU"]
    assert directory.columns.tolist() == ["Study", "Title", "Institution", "Countries", "Design", "Recruitment",
                                          "Actual enrolment", "Planned enrolment"]
    assert directory.iloc[0]["Actual enrolment"] == 420
    assert directory.iloc[0]["Planned enrolment"] == 2400
    assert "https://example.org/comect-demo/" not in content.decode("utf-8-sig")


def test_directory_csv_preserves_zero_missing_values_and_accents():
    data = load_graph((ROOT / "metadata_knowledge_graph.ttl").read_bytes())
    frame = data.studies.iloc[:1].copy()
    frame.loc[frame.index[0], "actual"] = 0
    frame.loc[frame.index[0], "planned"] = pd.NA
    frame.loc[frame.index[0], "institution"] = "Santé research institute"
    directory = pd.read_csv(BytesIO(study_directory_csv(frame)), encoding="utf-8-sig")
    assert directory.iloc[0]["Actual enrolment"] == 0
    assert pd.isna(directory.iloc[0]["Planned enrolment"])
    assert directory.iloc[0].Institution == "Santé research institute"
