# CoMeCT Research Observatory

A customisable **Streamlit** dashboard powered directly by `metadata_knowledge_graph.ttl`.
The supplied synthetic graph contains 10 studies, 17 study countries and 975 RDF triples.

## Run

An isolated environment has been prepared in this workspace:

```bash
.venv-streamlit/bin/python -m streamlit run home.py
```

Open the Local URL printed by Streamlit, normally `http://localhost:8501`.
The app supports Streamlit 1.48.1 and newer.

For a fresh installation using Python 3.12 or newer:

```bash
python3 -m venv .venv-streamlit
source .venv-streamlit/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run home.py
```

## Features

- Shared search and filters for pathogen group, country, institution, study design, status, study start year, data sharing, funder and research focus.
- Search studies supports typed keywords and dropdown suggestions for study names, institutions, researchers, funders and pathogens. Press Enter to apply a custom keyword.
- Choose charts, display order, one or two columns, study counts or enrolment, annual bars or lines, and geographical bars or a map.
- Select points or segments in the annual, country, status, sharing and funder charts to update the shared filters. Reset filters clears chart filters.
- Study directory with status badges, enrolment indicators, sorting and pagination; study details include abstracts, consent conditions and reported standards.
- Export CSV below the Study directory, aligned to the right of the table, downloads all filtered study summaries in the selected sort order. Actual and planned enrolment are separate numeric columns; source URIs, abstracts and other graph fields are excluded.
- Optional Study timeline in Customise, showing reported start/end dates and a current-date marker. Planned periods provide context rather than live study-status updates.
- Knowledge graph showing actual relationships to countries, funders, institutions, standards, focus areas and pathogen groups.
- The global Save & export control, source dataset downloads and raw source details are removed from the visitor interface. The Study directory has its own summary CSV export.

The geographical view defaults to a choropleth map: countries are shaded by study count or enrolment, with a shared colour legend. Country boundaries load through Plotly's map service. Bar charts remain available in Customise.

Source management is hidden from the everyday interface. To enable the retained `.ttl` upload feature in a future data-management session, set `COMECT_ENABLE_SOURCE_UPLOAD=1` when launching Streamlit:

```bash
COMECT_ENABLE_SOURCE_UPLOAD=1 .venv-streamlit/bin/python -m streamlit run home.py
```

Uploads must use the same study vocabulary. Unknown country codes stay visible in geographical bar charts.

## Data interpretation

All supplied records are synthetic. Annual charts use **study start dates**, because the graph does not contain registration dates. Disease labels and trial phases are not inferred. Multi-country or jointly funded studies contribute once per category; headline metrics count distinct studies. Missing enrolment remains missing. Reported standards and sharing intentions do not establish compliance or data access.

The reader expects `rdf:type <https://example.org/comect-demo/Study>` and the supplied `ex:` study vocabulary. A graph using another ontology requires a mapping in `graph_data.py`.

Visitors can view the displayed study summaries and charts and download the directory's summary columns as CSV. The interface does not offer the source Turtle graph. This local app does not include user authentication.

## Check

```bash
.venv-streamlit/bin/python -m pip install -r requirements-dev.txt
.venv-streamlit/bin/python -m pytest -q
```

`graph_data.py` handles parsing, filtering, aggregation and provenance. `charts.py` creates Plotly figures. `tables.py` renders the study summaries. `dashboard_config.py` validates dashboard settings and retains future persistence helpers. `home.py` is the Streamlit entry point.
