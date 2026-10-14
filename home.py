"""CoMeCT Research Observatory: a customisable Streamlit dashboard over Turtle RDF."""
from __future__ import annotations

from functools import partial
from datetime import datetime
import os
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from charts import annual_figure, bar_figure, donut_figure, enrolment_figure, map_figure, network_figure, timeline_figure
from chart_selection import selection_filter_values
from dashboard_config import (GROUPS, METRICS, PANELS, decode_view, default_config,
                              validate_config)
from graph_data import EX, FILTER_FIELDS, GraphData, filter_studies, load_graph, options, search_suggestions
from tables import study_directory_csv, study_table_html

ROOT = Path(__file__).resolve().parent
# Retained for future data-management work; the everyday dashboard has no
# source-management controls unless the operator explicitly enables them.
ENABLE_SOURCE_UPLOAD = os.environ.get("COMECT_ENABLE_SOURCE_UPLOAD") == "1"
FILTER_LABELS = {"pathogen_groups": "Pathogen group", "countries": "Study countries", "design": "Study design",
                 "status": "Recruitment status", "sharing": "Reported data sharing", "funders": "Research funders",
                 "focus": "Research focus", "year": "Study start year", "institution": "Institution"}
SETTING_KEYS = ("panels", "metric", "group", "annual_style", "geo_style", "layout")

st.set_page_config(page_title="CoMeCT · Research Observatory", page_icon="◈", layout="wide")
st.markdown("""
<style>
 .block-container {padding-top:3.6rem; padding-bottom:2.5rem; max-width:1580px;}
 [data-testid="stHeader"] {background:rgba(244,247,250,.94);}
 [data-testid="stExpander"] {background:#F4FAFB; border:1px solid #BEDCDF!important;
                            border-left:3px solid #3E9BA5!important; border-radius:10px!important; overflow:hidden;}
 [data-testid="stExpander"] details {border:0!important; background:transparent;}
 [data-testid="stExpander"] summary {background:#E7F3F5; color:#226976; padding:12px 16px!important;
                                    cursor:pointer; transition:background .15s ease;}
 [data-testid="stExpander"] summary p {font-weight:600; color:inherit!important;}
 [data-testid="stExpander"] summary:hover {background:#D8EEF0;}
 [data-testid="stExpander"] summary:focus-visible {outline:2px solid #3C99A6; outline-offset:-3px;}
 [data-testid="stExpander"] details[open] > summary {background:#DFF0F2; border-bottom:1px solid #CBE1E5;}
 [data-testid="stSidebar"] {background:#142E42; border-right:0;}
 [data-testid="stSidebar"] [data-testid="stSidebarContent"] {background:linear-gradient(180deg,#142E42,#19394D);}
 [data-testid="stSidebar"] .block-container {padding-top:2rem;}
 [data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
 [data-testid="stSidebar"] [data-testid="stWidgetLabel"] {color:#E8F0F5;}
 [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {font-size:.8rem; font-weight:550;}
 [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {color:#ADBFCC;}
 [data-testid="stSidebar"] hr {border-color:#355267; margin:1.2rem 0;}
 [data-testid="stSidebar"] h3 {font-size:1.05rem; color:#F3F7FA;}
 [data-testid="stSidebar"] [data-baseweb="select"] > div,
 [data-testid="stSidebar"] [data-baseweb="input"] {background:#203E52; border-color:#3A586A; border-radius:9px;}
 [data-testid="stSidebar"] input {color:#E8F0F5;}
 [data-testid="stSidebar"] input::placeholder {color:#AFC1CE; opacity:1;}
 [data-testid="stSidebar"] [data-baseweb="tag"] {background:#176E79; color:#FFF;}
 [data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] {background:transparent; color:#D9E9F0; border-color:#47667A;}
 [data-testid="stSidebar"] [data-testid="stBaseButton-secondary"]:hover {background:#294B60; border-color:#6F9AAE;}
 [data-testid="stSidebar"] [data-testid="stExpander"] {background:#234456; border-color:#5B8495!important;
                                                       border-left-color:#70C4CE!important;}
 [data-testid="stSidebar"] [data-testid="stExpander"] summary {background:#2B5165; color:#E8F6F7;}
 [data-testid="stSidebar"] [data-testid="stExpander"] summary:hover {background:#356274;}
 [data-testid="stSidebar"] [data-testid="stExpander"] details[open] > summary {
   background:#2B5165; border-bottom-color:#5B8495;
 }
 h1 {letter-spacing:-1.3px; font-size:2.35rem!important; font-weight:700!important; padding-bottom:.3rem!important;}
 h2,h3 {letter-spacing:-.4px;}
 [data-testid="stMetric"] {background:#FFF; border:1px solid #E1E9EF; border-radius:14px; padding:17px 18px;
                          box-shadow:0 3px 14px rgba(25,52,72,.035);}
 [data-testid="stMetricLabel"] p {font-size:.78rem; color:#657889; font-weight:550;}
 [data-testid="stMetricValue"] {font-size:1.9rem; font-weight:650; color:#193448; letter-spacing:-.7px;}
 [class*="st-key-panel_"] {background:#FFF; border-radius:15px!important; border-color:#E1E9EF!important;
                           box-shadow:0 3px 16px rgba(25,52,72,.035); padding:1.05rem!important;}
 [class*="st-key-panel_"] h3 {font-size:1.12rem; font-weight:650;}
 [class*="st-key-panel_"] [data-testid="stCaptionContainer"] {font-size:.78rem; color:#718492;}
 [role="tablist"] {gap:6px!important; background:#E8EEF3!important; padding:5px!important;
                    border-radius:12px!important; margin:8px 0 22px!important; border-bottom:0!important;}
 [role="tab"] {height:41px!important; padding:0 21px!important; border-radius:8px!important;
                      background:transparent!important; color:#607585!important; font-weight:600; border:0!important;}
 [role="tab"] p {font-size:.88rem; color:inherit!important;}
 [role="tab"]:hover {background:#F8FAFC!important; color:#096D78!important;}
 [role="tab"][aria-selected="true"] {background:#096D78!important; color:#FFF!important;
                                           box-shadow:0 2px 6px rgba(9,109,120,.16);}
 [data-baseweb="tab-highlight"], [data-baseweb="tab-border"] {display:none!important;}
 [role="tab"] .react-aria-SelectionIndicator {display:none!important;}
 button:focus-visible, [role="tab"]:focus-visible {outline:2px solid #3C99A6!important; outline-offset:3px;}
 [data-testid="stPopoverButton"] {border-radius:9px; font-size:.85rem; font-weight:600;}
 .st-key-customise_action [data-testid="stPopoverButton"] {
   background:#096D78; color:#FFF; border-color:#096D78;
 }
 .st-key-customise_action [data-testid="stPopoverButton"]:hover {
   background:#075967; color:#FFF; border-color:#075967;
 }
 .sidebar-brand {display:flex; align-items:center; gap:12px; margin-bottom:4px;}
 .brand-mark {display:grid; place-items:center; width:39px; height:39px; background:#2B6878;
              border:1px solid #478395; border-radius:11px; color:#D1F0EF; font-size:25px;}
 .brand-name {color:#FFF; font-size:23px; font-weight:700; letter-spacing:-.5px;}
 .brand-subtitle {color:#ADBFCC; font-size:10px; letter-spacing:1.5px; text-transform:uppercase; margin-top:3px;}
 .eyebrow {display:flex; align-items:center; gap:12px; font-size:10px; font-weight:700;
            letter-spacing:1.7px; color:#618091; margin-bottom:5px;}
 .demo-badge {color:#8B6733; background:#F6EDDF; border:1px solid #EEDDC1; border-radius:20px;
              padding:3px 9px; font-size:10px; letter-spacing:0; font-weight:600;}
 .lede {font-size:14px; color:#708391; margin-top:-4px; margin-bottom:16px;}
 .study-table-scroll {overflow:auto; max-height:610px; background:#FFF; border:1px solid #E0E8EE;
                      border-radius:13px; box-shadow:0 3px 14px rgba(25,52,72,.025);}
 .study-table {width:100%; min-width:930px; border-collapse:separate; border-spacing:0; table-layout:fixed; font-size:12px;}
 .study-table thead th {position:sticky; top:0; background:#EAF1F5; color:#536D80; z-index:1;
                       font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:.7px;
                       padding:14px 16px; border-bottom:1px solid #DCE6ED; text-align:left;}
 .study-table th:nth-child(1) {width:27%;} .study-table th:nth-child(2) {width:20%;}
 .study-table th:nth-child(3) {width:13%;} .study-table th:nth-child(4) {width:13%;}
 .study-table th:nth-child(5) {width:14%;} .study-table th:nth-child(6) {width:13%;}
 .study-table tbody td {padding:15px 16px; border-bottom:1px solid #EAF0F4; vertical-align:middle;
                       color:#496274; line-height:1.5;}
 .study-table tbody tr:nth-child(even) {background:#F8FAFC;}
 .study-table tbody tr:hover {background:#EEF7F8;}
 .study-table tbody tr:last-child td {border-bottom:0;}
 .study-name {font-size:12px; font-weight:700; color:#193448; margin-bottom:4px;}
 .study-description {font-size:11px; color:#7B8D9A; line-height:1.45;}
 .institution-cell {font-size:11px; font-weight:500;}
 .country-cell {font-size:11px; color:#718492!important;}
 .status-badge,.design-badge {display:inline-flex; align-items:center; gap:5px; border-radius:5px;
                            padding:4px 7px; font-size:10px; font-weight:600; white-space:nowrap;}
 .status-dot {width:5px; height:5px; border-radius:50%; background:currentColor; flex-shrink:0;}
 .recruiting {color:#247764; background:#E6F4EF;} .completed {color:#5C7183; background:#EAF0F5;}
 .planned {color:#976D36; background:#FBF0DE;} .surveillance {color:#6471A6; background:#EDF0FB;}
 .other {color:#647687; background:#EEF2F6;}
 .observational {color:#506F88; background:#EDF3F8;} .interventional {color:#756A9A; background:#F0EDFA;}
 .study-table .enrolment-cell {text-align:right; white-space:nowrap; font-variant-numeric:tabular-nums;}
 .actual-count {color:#264457; font-weight:650; font-size:12px;}
 .planned-count {color:#8A9AA6; font-size:10px;}
 .enrolment-track {height:4px; border-radius:5px; overflow:hidden; background:#E4EDF1; margin-top:7px;}
 .enrolment-track > div {height:100%; background:#4C9BA1; border-radius:5px;}
 .sr-only {position:absolute; width:1px; height:1px; padding:0; margin:-1px; overflow:hidden;
           clip:rect(0,0,0,0); white-space:nowrap; border:0;}
 .study-table-scroll:focus-visible {outline:2px solid #3C99A6; outline-offset:3px;}
 .st-key-study_directory_footer {margin-top:4px; margin-bottom:8px;}
 .st-key-study_directory_footer [data-testid="stDownloadButton"] button {
   background:#096D78; color:#FFF; border-color:#096D78; font-weight:600; border-radius:9px;
 }
 .st-key-study_directory_footer [data-testid="stDownloadButton"] button:hover {
   background:#075967; border-color:#075967;
 }
 .footer {color:#899BA8; font-size:11px; margin-top:28px; border-top:1px solid #E1E9EF; padding-top:15px;}
 @media (max-width:760px) {
   .block-container {padding-left:1rem; padding-right:1rem;}
   h1 {font-size:1.8rem!important;}
   [role="tab"] {padding:0 11px!important;}
   .st-key-dashboard_header [data-testid="stHorizontalBlock"],
   .st-key-summary_metrics [data-testid="stHorizontalBlock"] {
     display:grid!important; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px!important;
   }
   .st-key-dashboard_header [data-testid="stColumn"],
   .st-key-summary_metrics [data-testid="stColumn"] {width:auto!important; min-width:0!important;}
   .st-key-dashboard_header [data-testid="stColumn"]:first-child {grid-column:1/-1;}
   .st-key-summary_metrics [data-testid="stMetric"] {padding:12px 14px;}
   .st-key-summary_metrics [data-testid="stMetricValue"] {font-size:1.65rem;}
   .st-key-study_directory_footer [data-testid="stHorizontalBlock"] {display:flex!important; flex-wrap:wrap!important;}
   .st-key-study_directory_footer [data-testid="stColumn"]:first-child {width:100%!important; flex-basis:100%!important;}
   .st-key-study_directory_footer [data-testid="stColumn"]:last-child {width:160px!important; min-width:160px!important;
                                                                    flex:none!important; margin-left:auto;}
 }
</style>
""", unsafe_allow_html=True)


@st.cache_data(show_spinner="Loading studies…", max_entries=8)
def cached_graph(content: bytes, name: str) -> GraphData:
    return load_graph(content, name)


def apply_config(config):
    for field in FILTER_FIELDS:
        st.session_state[f"filter_{field}"] = config["filters"][field]
    st.session_state["search"] = config["search"] or None
    for field in SETTING_KEYS:
        st.session_state[f"cfg_{field}"] = config[field]


def reset_country_selection():
    st.session_state["filter_countries"] = []
    # Plotly selection state is read-only. A fresh widget clears its highlight
    # and stored selection without disturbing the other dashboard filters.
    st.session_state["country_chart_revision"] = st.session_state.get("country_chart_revision", 0) + 1


def reset_filters():
    reset_country_selection()
    for field in FILTER_FIELDS:
        st.session_state[f"filter_{field}"] = []
    st.session_state["search"] = None
    st.query_params.clear()
    st.session_state.pop("loaded_link", None)


def queue_config(value, frame, fingerprint):
    try:
        st.session_state["pending_config"] = validate_config(value, frame)
        if value.get("source_fingerprint") not in (None, fingerprint):
            st.session_state["view_notice"] = "This view was saved for another graph. Only matching filter values were restored."
    except (ValueError, TypeError) as error:
        st.session_state["view_error"] = str(error)


def select_chart(chart_key, field):
    state = st.session_state.get(chart_key, {})
    values = selection_filter_values(state, field, options(studies, field))
    if values is not None:
        st.session_state[f"filter_{field}"] = values


with st.sidebar:
    st.markdown('<div class="sidebar-brand"><div class="brand-mark">◈</div><div><div class="brand-name">CoMeCT</div><div class="brand-subtitle">Research observatory</div></div></div>', unsafe_allow_html=True)
    st.divider()
    uploaded = None
    if ENABLE_SOURCE_UPLOAD:
        with st.expander("Data source", expanded=False):
            uploaded = st.file_uploader("Use another Turtle graph", type=["ttl"], key="graph_upload",
                                       help="Uses the same CoMeCT study vocabulary as the supplied graph. Maximum 20 MB.")

try:
    content = uploaded.getvalue() if uploaded else (ROOT / "metadata_knowledge_graph.ttl").read_bytes()
    source_name = uploaded.name if uploaded else "metadata_knowledge_graph.ttl"
    data = cached_graph(content, source_name)
except Exception:
    st.error("The study data could not be loaded. Please contact the dashboard administrator.")
    st.stop()

studies = data.studies
if st.session_state.get("source_fingerprint") != data.fingerprint:
    apply_config(default_config())
    st.session_state["source_fingerprint"] = data.fingerprint
    st.session_state.pop("study_choice", None)
    st.session_state.pop("graph_focus", None)
    st.session_state.pop("loaded_link", None)

encoded = st.query_params.get("view")
if encoded and encoded != st.session_state.get("loaded_link"):
    st.session_state["loaded_link"] = encoded
    try:
        value = decode_view(encoded)
        queue_config(value, studies, data.fingerprint)
    except (ValueError, TypeError) as error:
        st.session_state["view_error"] = str(error)
if "pending_config" in st.session_state:
    apply_config(st.session_state.pop("pending_config"))

with st.sidebar:
    st.subheader("Filter studies")
    suggestions = search_suggestions(studies)
    # Keep a custom query available after reruns, and normalise the previous
    # text input's empty value when switching to the searchable dropdown.
    if st.session_state.get("search") == "":
        st.session_state["search"] = None
    current_search = st.session_state.get("search")
    if current_search:
        suggestions.setdefault(current_search, current_search)
        # Streamlit 1.48 changes the widget identity when options change.
        # Store the typed value explicitly before registering its new options.
        st.session_state["search"] = current_search
    st.selectbox("Search studies", list(suggestions), index=None, key="search", accept_new_options=True,
                 format_func=lambda value: suggestions.get(value, value),
                 placeholder="Type or choose…",
                 help="Choose a study, institution, researcher, funder or pathogen. For a free-text search, type a keyword and press Enter.")
    for field in ("pathogen_groups", "countries", "institution", "design", "status", "year"):
        st.multiselect(FILTER_LABELS[field], options(studies, field), key=f"filter_{field}", placeholder="All")
    with st.expander("More filters"):
        for field in ("sharing", "funders", "focus"):
            st.multiselect(FILTER_LABELS[field], options(studies, field), key=f"filter_{field}", placeholder="All")
    st.button("Reset filters", on_click=reset_filters, use_container_width=True)

selections = {field: st.session_state[f"filter_{field}"] for field in FILTER_FIELDS}
filtered = filter_studies(studies, selections, st.session_state.search or "")

demo_badge = '<span class="demo-badge">Synthetic demo</span>' if studies.synthetic.all() else ''
st.markdown(f'<div class="eyebrow">RESEARCH PORTFOLIO{demo_badge}</div>', unsafe_allow_html=True)
with st.container(key="dashboard_header"):
    header, customise = st.columns([6.4, 1.6], vertical_alignment="center")
with header:
    st.title("Research observatory")
with customise.container(key="customise_action"):
    with st.popover("Customise", icon=":material/tune:", use_container_width=True):
        st.caption("Choose charts and their display order.")
        st.multiselect("Visible charts", PANELS, key="cfg_panels")
        st.selectbox("Chart measure", list(METRICS), key="cfg_metric")
        st.selectbox("Annual breakdown", list(GROUPS), key="cfg_group")
        st.radio("Annual chart", ["Stacked bars", "Lines"], key="cfg_annual_style", horizontal=True)
        st.radio("Geographical chart", ["Bars", "Map"], key="cfg_geo_style", horizontal=True)
        st.radio("Dashboard layout", ["Two columns", "Full width"], key="cfg_layout", horizontal=True)
        st.caption("Status and sharing charts always count studies.")

st.markdown('<div class="lede">A connected view of studies, recruitment and research reach.</div>', unsafe_allow_html=True)

for key, renderer in (("view_error", st.error), ("view_notice", st.info)):
    if key in st.session_state:
        renderer(st.session_state.pop(key))

countries = {country for values in filtered.countries for country in values}
actual = filtered.actual.sum(min_count=1)
planned = filtered.planned.sum(min_count=1)
with st.container(key="summary_metrics"):
    metrics = st.columns(5)
metrics[0].metric("Studies in view", f"{len(filtered):,}", help="Distinct study identifiers after all filters.")
metrics[1].metric("Recruiting", f"{int((filtered.status == 'Recruiting').sum()):,}", help="Reported recruitment status in the graph.")
metrics[2].metric("Study countries", f"{len(countries):,}", help="Distinct study locations, not coordinating institution locations.")
metrics[3].metric("Actual enrolment", f"{actual:,}" if pd.notna(actual) else "Not reported", help="Sum of reported actual enrolment, including synthetic record-based surveillance counts.")
metrics[4].metric("Planned enrolment", f"{planned:,}" if pd.notna(planned) else "Not reported", help="Sum of reported planned enrolment. Missing values are excluded.")

active = [f"{FILTER_LABELS[field]}: {', '.join(map(str, values))}" for field, values in selections.items() if values]
if st.session_state.search:
    active.append(f"Search: {st.session_state.search}")
st.caption(f"{len(filtered)} of {len(studies)} studies" + (" · " + " | ".join(active) if active else ""))
if filtered.empty:
    st.info("No studies match these filters. Broaden your selection or use Reset filters.")
    st.stop()

overview, explorer, knowledge, methods = st.tabs(["Overview", "Studies", "Connections", "About the data"])
metric = METRICS[st.session_state.cfg_metric]


def chart(figure, key, field=None):
    arguments = dict(use_container_width=True, theme=None, key=key,
                     config={"displaylogo": False, "scrollZoom": False, "modeBarButtonsToRemove": ["toImage"]})
    if field:
        arguments.update(on_select=partial(select_chart, key, field), selection_mode="points")
    st.plotly_chart(figure, **arguments)


def render_panel(panel):
    with st.container(border=True, key="panel_" + panel.lower().replace(" ", "_")):
        st.subheader(panel)
        if panel == "Annual activity":
            st.caption("Studies by their planned start year")
            if filtered.year.notna().any():
                chart(annual_figure(filtered, GROUPS[st.session_state.cfg_group], metric, st.session_state.cfg_annual_style), "annual_chart", "year")
            else:
                st.info("Study start dates are not reported for these records.")
            st.caption("Study start dates · Select a year to filter")
        elif panel == "Geographical reach":
            st.caption("Where the studies take place")
            revision = st.session_state.get("country_chart_revision", 0)
            if st.session_state.cfg_geo_style == "Map":
                figure, omitted = map_figure(filtered, metric)
                chart(figure, f"country_map_{revision}", "countries")
                if omitted:
                    st.info("Map boundaries are unavailable for: " + ", ".join(omitted) + ". Use Bars to see all countries.")
            else:
                chart(bar_figure(filtered, "countries", metric), f"country_chart_{revision}", "countries")
            if selections["countries"]:
                st.button("Reset selection", key="reset_country_selection", icon=":material/restart_alt:",
                          on_click=reset_country_selection)
            st.caption("Select a country to filter · Countries without data are grey" if st.session_state.cfg_geo_style == "Map"
                       else "Select a country to filter · Studies can cover several countries")
        elif panel == "Recruitment status":
            st.caption("Reported recruitment status across studies")
            chart(donut_figure(filtered, "status"), "status_chart")
            st.caption("Use Recruitment status in the sidebar to filter")
        elif panel == "Data sharing":
            st.caption("Reported intention to share individual participant data")
            chart(donut_figure(filtered, "sharing"), "sharing_chart")
            st.caption("Self-reported sharing · Filter under More filters in the sidebar")
        elif panel == "Research funders":
            st.caption("Funders connected to the studies")
            chart(bar_figure(filtered, "funders", metric), "funder_chart", "funders")
            st.caption("Studies can have several funders")
        elif panel == "Reported standards":
            st.caption("Standards researchers report using or planning to use")
            chart(bar_figure(filtered, "standards", metric), "standards_chart")
            st.caption("Reported use, including planned adoption")
        elif panel == "Enrolment":
            st.caption("Actual and planned enrolment by study")
            chart(enrolment_figure(filtered), "enrolment_chart")
            st.caption("Reported enrolment · Includes record-based surveillance studies")
        elif panel == "Study timeline":
            st.caption("Reported start and end dates, coloured by recruitment status")
            today = datetime.now(ZoneInfo("Europe/Amsterdam")).date()
            figure, omitted = timeline_figure(filtered.head(50), today)
            if figure is not None:
                chart(figure, "timeline_chart")
            else:
                st.info("No complete study periods are available for the current selection.")
            if omitted:
                st.caption(f"{omitted} studies have missing or inconsistent dates and are omitted.")
            if len(filtered) > 50:
                st.caption("Showing the first 50 studies. Use filters to narrow the timeline.")
            st.caption("Planned periods provide temporal context; recruitment status is reported, not a live update.")


with overview:
    panels = st.session_state.cfg_panels
    if not panels:
        st.info("Choose Visible charts in Customise to build your overview.")
    elif st.session_state.cfg_layout == "Full width":
        for panel in panels:
            render_panel(panel)
    else:
        index = 0
        while index < len(panels):
            if panels[index] == "Study timeline":
                render_panel(panels[index])
                index += 1
                continue
            row = [panels[index]]
            if index + 1 < len(panels) and panels[index + 1] != "Study timeline":
                row.append(panels[index + 1])
            for column, panel in zip(st.columns(len(row), gap="medium"), row):
                with column:
                    render_panel(panel)
            index += len(row)

with explorer:
    title_column, sort_column = st.columns([4, 1], vertical_alignment="center")
    with title_column:
        st.subheader("Study directory")
        st.caption("Browse the portfolio and choose a study below for more detail.")
    with sort_column:
        sort_columns = {"Study name": "acronym", "Institution": "institution", "Start date": "start_date", "Actual enrolment": "actual"}
        sort_by = st.selectbox("Sort by", list(sort_columns), key="study_sort")
    ordered = filtered.sort_values(sort_columns[sort_by], ascending=sort_by != "Actual enrolment", na_position="last")
    page_count = (len(ordered) + 14) // 15
    if page_count > 1:
        pages = list(range(1, page_count + 1))
        if st.session_state.get("study_page", 1) not in pages:
            st.session_state.study_page = 1
        page = st.selectbox("Page", pages, key="study_page", format_func=lambda number: f"{number} of {page_count}")
    else:
        page = 1
    start = (page - 1) * 15
    st.markdown(study_table_html(ordered.iloc[start:start + 15]), unsafe_allow_html=True)
    with st.container(key="study_directory_footer"):
        table_info, csv_column = st.columns([4, 1], vertical_alignment="center")
        with table_info:
            st.caption(f"{start + 1}–{min(start + 15, len(ordered))} of {len(ordered)} studies · Enrolment shows actual / planned")
        with csv_column:
            st.download_button("Export CSV", study_directory_csv(ordered), file_name="comect-study-directory.csv",
                               mime="text/csv", key="download_study_directory", icon=":material/download:", type="primary",
                               help="Download all studies matching your current filters, in the selected sort order.",
                               on_click="ignore", use_container_width=True)
    if st.session_state.get("study_choice") not in filtered.uri.tolist():
        st.session_state["study_choice"] = filtered.iloc[0].uri
    choice = st.selectbox("Inspect study", filtered.uri.tolist(), key="study_choice",
                          format_func=lambda uri: filtered.loc[filtered.uri == uri, "acronym"].iloc[0])
    study = filtered.loc[filtered.uri == choice].iloc[0]
    with st.container(border=True):
        st.subheader(study.title)
        st.caption(f"{study.id} · {study.design} · {study.status}")
        left, right = st.columns(2)
        with left:
            st.markdown("**Institution**")
            st.write(study.institution)
            st.markdown("**Principal investigator**")
            st.write(study.investigator)
            st.markdown("**Study countries**")
            st.write(", ".join(study.countries) or "Not reported")
            st.markdown("**Research focus**")
            st.write(" · ".join(study.focus) or "Not reported")
        with right:
            st.markdown("**Reported data sharing**")
            st.write(study.sharing)
            st.markdown("**Consent conditions**")
            st.write(study.consent)
            st.markdown("**Access mechanism**")
            st.write(study.access)
            st.markdown("**Reported standards**")
            st.write(" · ".join(study.standards) or "Not reported")
        with st.expander("Study abstract & additional metadata"):
            st.write(study.abstract or "No abstract reported.")
            for field, title in (("data_types", "Data types"), ("settings", "Study settings"), ("age_groups", "Age groups"), ("outcomes", "Primary outcomes"), ("pathogens", "Specific pathogens")):
                st.write(f"**{title}:** " + (" · ".join(study[field]) or "Not reported"))

with knowledge:
    st.subheader("Explore the connections")
    st.caption("Explore connections between studies and their research partners. All global filters apply.")
    relation_choices = {"Study countries": EX.takesPlaceIn, "Research funders": EX.fundedBy,
                        "Lead institutions": EX.leadInstitution, "Reported standards": EX.reportsUseOfStandard,
                        "Research focus": EX.studyFocus, "Pathogen groups": EX.pathogenGroup}
    graph_left, graph_right = st.columns(2)
    with graph_left:
        relationships = st.multiselect("Show relationships", list(relation_choices), default=["Research funders", "Pathogen groups"])
    with graph_right:
        focus_options = ["All filtered studies"] + filtered.uri.tolist()
        if st.session_state.get("graph_focus") not in focus_options:
            st.session_state["graph_focus"] = "All filtered studies"
        focus = st.selectbox("Focus on study", focus_options, key="graph_focus",
                            format_func=lambda uri: uri if uri == "All filtered studies" else filtered.loc[filtered.uri == uri, "acronym"].iloc[0])
    uris = filtered.uri.tolist() if focus == "All filtered studies" else [focus]
    if len(uris) > 50:
        st.info("The graph shows the first 50 filtered studies. Use filters or focus on one study for a smaller view.")
    if relationships:
        figure, node_count, edge_count = network_figure(data.graph, uris[:50], [relation_choices[value] for value in relationships])
        chart(figure, "network_chart")
        st.caption(f"{node_count} connections and studies · {edge_count} relationships")
    else:
        st.info("Select at least one relationship to draw the graph.")

with methods:
    st.subheader("About the study data")
    if studies.synthetic.all():
        st.write("This demonstration uses fictional studies to explore research activity and connections. "
                 "The counts and enrolment figures describe the sample portfolio.")
    else:
        st.write(f"This portfolio includes {int(studies.synthetic.sum())} studies marked as synthetic examples.")
    st.markdown("""
    - **Study counts:** each study is counted once in the summary. A study can contribute to several countries, funders or research categories.
    - **Annual activity:** dates describe when studies start. They are separate from registration dates.
    - **Study timeline:** planned study periods show how research overlaps in time. The current-date marker does not establish whether a study is actively running.
    - **Enrolment:** planned and actual values are reported by each study. Missing values are excluded. Surveillance studies may count records.
    - **Sharing and standards:** information is self-reported. Sharing intentions do not guarantee data access, and reported standards do not establish verified compliance.
    - **Filters:** choosing several values within a filter includes any of those values. Different filters narrow the results together.
    - **Map colours:** darker shades mean more studies or higher enrolment, according to the selected measure. Grey countries have no value in the current view.
    """)

st.markdown('<div class="footer">CoMeCT Research Observatory · Aiman</div>', unsafe_allow_html=True)

