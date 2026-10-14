"""Extract study metadata from RDF without flattening away many-to-many links."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from urllib.parse import unquote

import pandas as pd
from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, FOAF, RDF, RDFS, SKOS

EX = Namespace("https://example.org/comect-demo/")
UNKNOWN = "Not reported"


@dataclass
class GraphData:
    graph: Graph
    studies: pd.DataFrame
    fingerprint: str
    source_name: str


def label(graph: Graph, node) -> str:
    if node is None:
        return UNKNOWN
    if isinstance(node, Literal):
        return str(node)
    for predicate in (SKOS.prefLabel, FOAF.name, DCTERMS.title, RDFS.label, DCTERMS.alternative):
        values = sorted(str(value) for value in graph.objects(node, predicate))
        if values:
            return values[0]
    return unquote(str(node).rstrip("/").rsplit("/", 1)[-1].rsplit("#", 1)[-1])


def text(graph: Graph, subject, predicate, default=UNKNOWN):
    value = graph.value(subject, predicate)
    return str(value) if value is not None else default


def number(graph: Graph, subject, predicate):
    value = graph.value(subject, predicate)
    if value is None:
        return None
    try:
        result = int(value)
        return result if result >= 0 else None
    except (TypeError, ValueError):
        return None


def linked_labels(graph: Graph, subject, predicate) -> list[str]:
    return sorted({label(graph, node) for node in graph.objects(subject, predicate)})


def load_graph(content: bytes, source_name: str = "metadata_knowledge_graph.ttl") -> GraphData:
    if len(content) > 20 * 1024 * 1024:
        raise ValueError("The Turtle file must be 20 MB or smaller.")
    graph = Graph().parse(data=content, format="turtle")
    rows = []
    for subject in sorted(set(graph.subjects(RDF.type, EX.Study)), key=str):
        sharing = graph.value(subject, EX.hasSharingConditions)
        investigator = graph.value(subject, EX.hasPrincipalInvestigator)
        start = pd.to_datetime(text(graph, subject, EX.studyStartDate, None), errors="coerce")
        country_nodes = set(graph.objects(subject, EX.takesPlaceIn))
        if not country_nodes:
            country_nodes = set(graph.objects(subject, DCTERMS.spatial))
        rows.append({
            "id": str(subject).rsplit("/", 1)[-1],
            "uri": str(subject),
            "title": text(graph, subject, DCTERMS.title, label(graph, subject)),
            "acronym": text(graph, subject, DCTERMS.alternative, label(graph, subject)),
            "abstract": text(graph, subject, DCTERMS.abstract, ""),
            "start_date": start,
            "end_date": pd.to_datetime(text(graph, subject, EX.studyEndDate, None), errors="coerce"),
            "year": int(start.year) if pd.notna(start) else None,
            "design": text(graph, subject, EX.studyDesign),
            "status": text(graph, subject, EX.recruitmentStatus,
                           label(graph, graph.value(subject, EX.hasRecruitmentStatus))),
            "planned": number(graph, subject, EX.plannedEnrolment),
            "actual": number(graph, subject, EX.actualEnrolment),
            "countries": sorted({label(graph, node) for node in country_nodes}),
            "country_codes": sorted({str(node).rsplit("/", 1)[-1] for node in country_nodes}),
            "institution": label(graph, graph.value(subject, EX.leadInstitution)),
            "funders": linked_labels(graph, subject, EX.fundedBy),
            "pathogen_groups": linked_labels(graph, subject, EX.pathogenGroup),
            "pathogens": sorted(set(linked_labels(graph, subject, EX.studyBacterium)
                                    + linked_labels(graph, subject, EX.studyVirus))),
            "focus": linked_labels(graph, subject, EX.studyFocus),
            "standards": linked_labels(graph, subject, EX.reportsUseOfStandard),
            "data_types": linked_labels(graph, subject, EX.dataType),
            "settings": linked_labels(graph, subject, EX.studySetting),
            "age_groups": linked_labels(graph, subject, EX.targetAgeGroup),
            "outcomes": linked_labels(graph, subject, EX.primaryOutcome),
            "sharing": text(graph, sharing, EX.ipdSharingStatus) if sharing is not None else UNKNOWN,
            "consent": text(graph, sharing, EX.consentResponse) if sharing is not None else UNKNOWN,
            "access": text(graph, sharing, EX.reportedAccessMechanism) if sharing is not None else UNKNOWN,
            "investigator": label(graph, investigator),
            "synthetic": graph.value(subject, EX.synthetic) == Literal(True),
        })
    if not rows:
        raise ValueError(f"No studies found. This dashboard expects subjects of type <{EX.Study}>.")
    frame = pd.DataFrame(rows)
    for column in ("year", "planned", "actual"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce").astype("Int64")
    return GraphData(graph, frame, sha256(content).hexdigest(), source_name)


LIST_FIELDS = {"countries", "funders", "pathogen_groups", "pathogens", "focus", "standards",
               "data_types", "settings", "age_groups", "outcomes"}
FILTER_FIELDS = ("pathogen_groups", "countries", "institution", "design", "status", "sharing", "funders", "focus", "year")


def options(frame: pd.DataFrame, field: str) -> list:
    if field in LIST_FIELDS:
        return sorted({value for values in frame[field] for value in values})
    values = frame[field].dropna().unique().tolist()
    return sorted(int(value) for value in values) if field == "year" else sorted(values)


def search_suggestions(frame: pd.DataFrame) -> dict[str, str]:
    """Searchable terms paired with readable dropdown labels."""
    suggestions = {}
    for row in frame.sort_values("acronym").itertuples():
        if row.acronym and row.acronym != UNKNOWN:
            suggestions.setdefault(row.acronym, f"{row.acronym} · {row.title}")
    for field, category in (("institution", "Institution"), ("investigator", "Researcher"),
                            ("funders", "Funder"), ("pathogens", "Pathogen")):
        for value in options(frame, field):
            if value and value != UNKNOWN:
                suggestions.setdefault(value, f"{category} · {value}")
    return suggestions


def filter_studies(frame: pd.DataFrame, selections: dict, search: str = "") -> pd.DataFrame:
    mask = pd.Series(True, index=frame.index)
    for field in FILTER_FIELDS:
        selected = selections.get(field, [])
        if not selected:
            continue
        if field in LIST_FIELDS:
            wanted = set(selected)
            mask &= frame[field].map(lambda values: bool(wanted.intersection(values)))
        else:
            mask &= frame[field].isin(selected)
    if search.strip():
        searchable = frame.apply(lambda row: " ".join(
            " ".join(row[field]) if isinstance(row[field], list) else str(row[field])
            for field in ("id", "title", "acronym", "abstract", "institution", "investigator", "funders", "pathogens")
        ), axis=1)
        mask &= searchable.str.contains(search.strip(), case=False, regex=False)
    return frame.loc[mask].copy()


def aggregate(frame: pd.DataFrame, field: str, metric: str = "studies") -> pd.DataFrame:
    columns = ["id", field] + ([] if metric == "studies" else [metric])
    values = frame[columns].copy()
    if field in LIST_FIELDS:
        values = values.explode(field)
    values = values.dropna(subset=[field]).drop_duplicates(["id", field])
    if metric == "studies":
        return values.groupby(field, observed=True)["id"].nunique().reset_index(name="value")
    return values.groupby(field, observed=True)[metric].sum(min_count=1).reset_index(name="value")


def annual_counts(frame: pd.DataFrame, group: str, metric: str = "studies") -> pd.DataFrame:
    columns = ["id", "year", group] + ([] if metric == "studies" else [metric])
    values = frame[columns].copy()
    if group in LIST_FIELDS:
        values = values.explode(group)
    values = values.dropna(subset=["year", group]).drop_duplicates(["id", "year", group])
    if metric == "studies":
        return values.groupby(["year", group], observed=True)["id"].nunique().reset_index(name="value")
    return values.groupby(["year", group], observed=True)[metric].sum(min_count=1).reset_index(name="value")


def export_frame(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.copy()
    for column in output.columns:
        if column in LIST_FIELDS or column == "country_codes":
            output[column] = output[column].map(lambda values: "; ".join(values))
    return output


def study_subgraph(graph: Graph, study_uris: list[str]) -> Graph:
    """Study assertions plus a two-hop context; only original triples are copied."""
    result = Graph()
    for prefix, namespace in graph.namespaces():
        result.bind(prefix, namespace)
    frontier = {URIRef(uri) for uri in study_uris}
    visited = set()
    for _ in range(3):
        next_frontier = set()
        for subject in frontier - visited:
            visited.add(subject)
            for triple in graph.triples((subject, None, None)):
                result.add(triple)
                if isinstance(triple[2], (URIRef, BNode)):
                    next_frontier.add(triple[2])
        frontier = next_frontier
    return result


def relationship_rows(graph: Graph, study_uri: str) -> pd.DataFrame:
    rows = []
    for _, predicate, obj in graph.triples((URIRef(study_uri), None, None)):
        rows.append({"Predicate": graph.namespace_manager.normalizeUri(predicate),
                     "Value": label(graph, obj), "Object": str(obj), "Term type": obj.__class__.__name__})
    return pd.DataFrame(rows).sort_values(["Predicate", "Value"]).reset_index(drop=True)
