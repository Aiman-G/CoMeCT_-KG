from pathlib import Path

import pandas as pd
import pytest
from rdflib import URIRef

from dashboard_config import decode_view, default_config, encode_view, read_views, save_view, validate_config
from graph_data import EX, aggregate, annual_counts, export_frame, filter_studies, load_graph, search_suggestions, study_subgraph

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def dataset():
    return load_graph((ROOT / "metadata_knowledge_graph.ttl").read_bytes())


def test_source_totals_and_multivalued_links(dataset):
    frame = dataset.studies
    assert len(dataset.graph) == 975
    assert len(frame) == 10
    assert frame.id.nunique() == 10
    assert frame.synthetic.all()
    assert len({country for countries in frame.countries for country in countries}) == 17
    assert frame.actual.sum() == 21770
    assert frame.planned.sum() == 67300
    boreal = frame.loc[frame.id == "SYN-0002"].iloc[0]
    assert len(boreal.funders) == 2
    assert boreal.countries == ["Finland", "Norway", "Sweden"]


def test_filters_combine_or_within_and_between_fields(dataset):
    frame = dataset.studies
    filtered = filter_studies(frame, {"countries": ["Netherlands"], "design": ["Interventional"]})
    assert filtered.id.tolist() == ["SYN-0003"]
    funded = filter_studies(frame, {"funders": ["Aster Research Council", "Boreal Science Trust"]})
    assert set(funded.id) == {"SYN-0001", "SYN-0002", "SYN-0003", "SYN-0006", "SYN-0009"}
    assert funded.id.is_unique
    institutions = filter_studies(frame, {"institution": ["Canal Clinical Trials Alliance", "Seabright Respiratory Research Institute"],
                                          "design": ["Interventional"]})
    assert institutions.id.tolist() == ["SYN-0003"]


def test_search_is_literal_and_can_match_an_investigator(dataset):
    assert filter_studies(dataset.studies, {}, "[").empty
    assert filter_studies(dataset.studies, {}, "elena varga").id.tolist() == ["SYN-0001"]


def test_every_suggested_search_matches_study_metadata(dataset):
    suggestions = search_suggestions(dataset.studies)
    assert "AURORA-RESP" in suggestions
    assert "Seabright Respiratory Research Institute" in suggestions
    assert "Elena Varga" in suggestions
    assert "Aster Research Council" in suggestions
    assert "Not reported" not in suggestions
    assert all(not filter_studies(dataset.studies, {}, term).empty for term in suggestions)


def test_category_totals_respect_many_to_many_relationships(dataset):
    frame = dataset.studies
    assert aggregate(frame, "countries").value.sum() == 22
    assert aggregate(frame, "funders").value.sum() == 11
    assert aggregate(frame, "standards").value.sum() == 24
    assert annual_counts(frame, "pathogen_groups").value.sum() == 10
    assert aggregate(frame, "status", "actual").value.sum() == 21770


def test_zero_is_preserved_and_missing_is_not_fabricated():
    content = b'''@prefix ex: <https://example.org/comect-demo/> .
        @prefix dct: <http://purl.org/dc/terms/> .
        ex:one a ex:Study; dct:title "Missing metadata"; ex:actualEnrolment 0 .
        ex:two a ex:Study; dct:title "Invalid date"; ex:studyStartDate "invalid" .'''
    frame = load_graph(content).studies
    assert frame.iloc[0].actual == 0
    assert pd.isna(frame.iloc[0].planned)
    assert pd.isna(frame.iloc[0].year)
    assert pd.isna(frame.iloc[1].actual)
    assert pd.isna(frame.iloc[1].year)
    assert pd.isna(aggregate(frame, "design", "planned").iloc[0].value)


def test_turtle_export_keeps_provenance_without_inventing_triples(dataset):
    uri = dataset.studies.iloc[0].uri
    exported = study_subgraph(dataset.graph, [uri])
    assert set(exported).issubset(set(dataset.graph))
    assert len(list(exported.triples((URIRef(uri), None, None)))) > 30
    assert not list(exported.triples((URIRef(str(EX) + "study/SYN-0002"), None, None)))
    assert len(study_subgraph(dataset.graph, [])) == 0
    assert "Netherlands" in export_frame(dataset.studies).iloc[0].countries


def test_invalid_or_unsupported_graphs_report_errors():
    with pytest.raises(Exception):
        load_graph(b"This is not Turtle.")
    with pytest.raises(ValueError, match="No studies found"):
        load_graph(b'<https://example.org/s> <https://example.org/p> "value" .')


def test_views_roundtrip_and_reject_invalid_settings(dataset, tmp_path):
    config = default_config()
    config["filters"]["countries"] = ["Netherlands", "Unknown country"]
    config["metric"] = "Actual enrolment"
    assert decode_view(encode_view(config)) == config
    restored = validate_config(config, dataset.studies)
    assert restored["filters"]["countries"] == ["Netherlands"]
    assert restored["metric"] == "Actual enrolment"
    path = tmp_path / "saved_views.json"
    save_view(path, "My view", restored)
    assert read_views(path)["My view"] == restored
    with pytest.raises(ValueError, match="unknown chart"):
        validate_config({**config, "panels": ["Imaginary chart"]}, dataset.studies)
    with pytest.raises(ValueError, match="Invalid filter"):
        validate_config({**config, "filters": {"countries": "Netherlands"}}, dataset.studies)
    with pytest.raises(ValueError):
        decode_view("bad link")
