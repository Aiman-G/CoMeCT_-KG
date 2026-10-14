"""Plotly views whose values come exclusively from the parsed RDF study records."""
import textwrap
from datetime import timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from rdflib import URIRef
from rdflib.namespace import DCTERMS

from graph_data import aggregate, annual_counts, label

COLORS = ["#147D87", "#7387C8", "#D6A05F", "#6BAA95", "#C77891", "#5689AC", "#A6AE6A"]
METRIC_LABELS = {"studies": "Studies", "planned": "Planned enrolment", "actual": "Actual enrolment"}
# Plotly's country geometries use ISO 3166 alpha-3 identifiers. The graph's
# ISO alpha-2 country URIs retain their original labels for hover and filtering.
ISO_ALPHA3 = {
    "AT": "AUT", "BE": "BEL", "DK": "DNK", "FI": "FIN", "FR": "FRA", "DE": "DEU",
    "GR": "GRC", "IE": "IRL", "IT": "ITA", "KE": "KEN", "NL": "NLD", "NO": "NOR",
    "PT": "PRT", "ES": "ESP", "SE": "SWE", "UG": "UGA", "GB": "GBR",
}
MAP_COLORS = [[0, "#D2EBEB"], [0.35, "#85C3C8"], [0.7, "#378F9B"], [1, "#075668"]]


def polish(figure, height=370):
    figure.update_layout(template="plotly_white", height=height, paper_bgcolor="rgba(0,0,0,0)",
                         plot_bgcolor="rgba(0,0,0,0)", font=dict(family="Arial, sans-serif", size=12, color="#657889"),
                         margin=dict(l=8, r=16, t=24, b=16), colorway=COLORS,
                         legend=dict(orientation="h", y=-0.2, x=0, title_text=""),
                         hoverlabel=dict(bgcolor="#193448", font_color="white"),
                         clickmode="event+select")
    figure.update_xaxes(showgrid=False, zeroline=False, title_font_size=11)
    figure.update_yaxes(gridcolor="#EEF2F4", zeroline=False, title_font_size=11)
    return figure


def annual_figure(frame, group, metric, style):
    values = annual_counts(frame, group, metric)
    # Missing calendar years are explicit zeroes only for study counts.
    if metric == "studies" and not values.empty:
        years = range(int(frame.year.min()), int(frame.year.max()) + 1)
        categories = values[group].unique()
        index = pd.MultiIndex.from_product([years, categories], names=["year", group])
        values = values.set_index(["year", group]).reindex(index, fill_value=0).reset_index()
    if style == "Lines":
        figure = px.line(values, x="year", y="value", color=group, markers=True,
                         custom_data=["year"], color_discrete_sequence=COLORS)
        figure.update_traces(line_width=3, marker_size=9)
    else:
        figure = px.bar(values, x="year", y="value", color=group, barmode="stack",
                        custom_data=["year"], color_discrete_sequence=COLORS)
        figure.update_traces(marker_line_width=0, width=0.55)
    figure.update_traces(hovertemplate="Study start year: %{x}<br>Value: %{y:,}<extra>%{fullData.name}</extra>")
    figure.update_xaxes(title_text="Study start year", dtick=1)
    figure.update_yaxes(title_text=METRIC_LABELS[metric], rangemode="tozero")
    if metric == "studies":
        figure.update_yaxes(dtick=1)
    return polish(figure, 400)


def bar_figure(frame, field, metric="studies"):
    values = aggregate(frame, field, metric).sort_values("value", ascending=True, na_position="first")
    values["display"] = values[field].map(lambda value: "<br>".join(textwrap.wrap(str(value), 36)))
    figure = px.bar(values, x="value", y="display", orientation="h", text="value",
                    custom_data=[field], color_discrete_sequence=[COLORS[0]])
    figure.update_traces(marker_line_width=0, textposition="outside", cliponaxis=False,
                         hovertemplate="%{customdata[0]}<br>Value: %{x:,}<extra></extra>")
    figure.update_xaxes(title_text=METRIC_LABELS[metric], rangemode="tozero")
    figure.update_yaxes(title_text="", showgrid=False)
    return polish(figure, max(370, 25 * len(values) + 75))


def donut_figure(frame, field):
    values = aggregate(frame, field)
    short_labels = {
        "Completed - trial ended as planned": "Completed",
        "Not yet applicable (i.e., for surveillance)": "Surveillance",
        "Yes - already shared": "Already shared", "Yes - planned": "Planned",
        "No - by ethics or consent restriction": "Restricted", "Not yet decided": "Undecided",
    }
    values["display"] = values[field].map(lambda value: short_labels.get(value, value))
    figure = px.pie(values, names="display", values="value", hole=0.73,
                    custom_data=[field], color_discrete_sequence=COLORS)
    figure.update_traces(textinfo="none", marker=dict(line=dict(color="white", width=4)),
                         hovertemplate="%{customdata[0]}<br>%{value} studies (%{percent})<extra></extra>")
    figure.add_annotation(text=f"<b>{len(frame)}</b><br>studies", x=0.5, y=0.5, showarrow=False,
                          font=dict(size=23, color="#172C3C"))
    figure.update_layout(legend=dict(orientation="v", y=0.5, x=1.05))
    figure = polish(figure, 340)
    figure.update_layout(legend=dict(orientation="h", y=-0.12, x=0))
    return figure


def map_figure(frame, metric):
    values = aggregate(frame, "countries", metric)
    country_labels = {}
    for names, codes in zip(frame.countries, frame.country_codes):
        # Both lists are sorted independently, so resolve each code by its known
        # country label rather than zipping codes to labels by position.
        for code in codes:
            uri_label = COUNTRY_NAMES.get(code)
            if uri_label in names:
                country_labels[uri_label] = ISO_ALPHA3.get(code, code if len(code) == 3 else None)
    values["iso_alpha3"] = values.countries.map(country_labels)
    known = values.dropna(subset=["iso_alpha3", "value"])
    omitted = sorted(values.loc[values.iso_alpha3.isna(), "countries"].tolist())
    maximum = float(known.value.max()) if not known.empty else 1.0
    figure = go.Figure(go.Choropleth(
        locations=known.iso_alpha3.tolist(), locationmode="ISO-3", z=known.value.astype(float).tolist(),
        customdata=[[name] for name in known.countries], text=known.countries.tolist(),
        colorscale=MAP_COLORS, zmin=0, zmax=max(maximum, 1),
        marker=dict(line=dict(color="white", width=0.75)),
        colorbar=dict(title=dict(text=METRIC_LABELS[metric], font=dict(size=11)),
                      orientation="h", x=0.5, xanchor="center", y=-0.04, yanchor="top",
                      len=0.6, thickness=9, outlinewidth=0,
                      dtick=1 if metric == "studies" else None, tickfont=dict(size=10)),
        hovertemplate=f"<b>%{{text}}</b><br>{METRIC_LABELS[metric]}: %{{z:,}}<extra></extra>",
    ))
    figure.update_geos(projection_type="natural earth", showframe=False, showcoastlines=False,
                       showland=True, landcolor="#E8EDF2", showcountries=True, countrycolor="white",
                       showocean=True, oceancolor="#F7FAFC", bgcolor="rgba(0,0,0,0)")
    figure = polish(figure, 400)
    figure.update_layout(margin=dict(l=0, r=0, t=0, b=55))
    return figure, omitted


COUNTRY_NAMES = {
    "AT": "Austria", "BE": "Belgium", "DK": "Denmark", "FI": "Finland", "FR": "France",
    "DE": "Germany", "GR": "Greece", "IE": "Ireland", "IT": "Italy", "KE": "Kenya",
    "NL": "Netherlands", "NO": "Norway", "PT": "Portugal", "ES": "Spain", "SE": "Sweden",
    "UG": "Uganda", "GB": "United Kingdom",
}


def enrolment_figure(frame):
    values = frame[["acronym", "planned", "actual"]].melt(id_vars="acronym", var_name="Measure", value_name="Enrolment")
    figure = px.bar(values, x="acronym", y="Enrolment", color="Measure", barmode="group",
                    color_discrete_map={"planned": "#D9E8EA", "actual": COLORS[0]})
    figure.update_xaxes(title_text="", tickangle=-35)
    return polish(figure, 420)


def timeline_figure(frame, as_of):
    """Reported study periods; the date marker is context, not a live status claim."""
    valid = frame.start_date.notna() & frame.end_date.notna() & (frame.end_date >= frame.start_date)
    values = frame.loc[valid].sort_values(["start_date", "acronym"]).copy()
    omitted = len(frame) - len(values)
    if values.empty:
        return None, omitted
    short_status = {
        "Completed - trial ended as planned": "Completed",
        "Not yet applicable (i.e., for surveillance)": "Surveillance",
    }
    values["reported_status"] = values.status.map(lambda value: short_status.get(value, value))
    values["start_label"] = values.start_date.dt.strftime("%d %b %Y")
    values["end_label"] = values.end_date.dt.strftime("%d %b %Y")
    figure = px.timeline(values, x_start="start_date", x_end="end_date", y="acronym", color="reported_status",
                         custom_data=["title", "institution", "start_label", "end_label", "status"],
                         category_orders={"acronym": values.acronym.tolist()},
                         color_discrete_map={"Recruiting": COLORS[0], "Completed": "#A3B2BF",
                                             "Surveillance": COLORS[1], "Not yet recruiting": COLORS[2]})
    figure.update_traces(marker_line_width=0, width=0.55,
                         hovertemplate="<b>%{y}</b><br>%{customdata[0]}<br>%{customdata[1]}<br>"
                                       "Start: %{customdata[2]}<br>End: %{customdata[3]}<br>%{customdata[4]}<extra></extra>")
    today = pd.Timestamp(as_of)
    figure.add_shape(type="line", x0=today.isoformat(), x1=today.isoformat(), y0=0, y1=1, xref="x", yref="paper",
                     line=dict(color="#496477", width=1.5, dash="dot"))
    figure.add_annotation(x=today.isoformat(), y=1.06, xref="x", yref="paper", showarrow=False,
                          text=f"Today · {today.strftime('%d %b %Y')}", font=dict(size=11, color="#496477"))
    figure = polish(figure, max(360, 30 * len(values) + 140))
    figure.update_layout(margin=dict(l=8, r=16, t=42, b=32))
    figure.update_yaxes(title_text="", autorange="reversed", showgrid=False)
    figure.update_xaxes(title_text="Planned study period", tickformat="%b %Y", showgrid=True, gridcolor="#EEF2F4",
                        range=[(min(values.start_date.min(), today) - timedelta(days=60)).isoformat(),
                               (max(values.end_date.max(), today) + timedelta(days=60)).isoformat()])
    return figure, omitted


def network_figure(graph, study_uris, predicates):
    studies = [URIRef(uri) for uri in study_uris]
    nodes = {}
    edges = []
    for study in studies:
        acronym = graph.value(study, DCTERMS.alternative)
        nodes[str(study)] = (str(acronym) if acronym is not None else label(graph, study), "Study")
        for predicate in predicates:
            for obj in graph.objects(study, predicate):
                nodes[str(obj)] = (label(graph, obj), label(graph, predicate))
                edges.append((str(study), str(obj), graph.namespace_manager.normalizeUri(predicate)))
    positions = {}
    left = [str(study) for study in studies]
    right = sorted(set(nodes) - set(left), key=lambda uri: nodes[uri])
    for side, members in enumerate((left, right)):
        for index, uri in enumerate(members):
            positions[uri] = (side, (index + 1) / (len(members) + 1))
    figure = go.Figure()
    xs, ys = [], []
    for source, target, _ in edges:
        xs.extend([positions[source][0], positions[target][0], None])
        ys.extend([positions[source][1], positions[target][1], None])
    figure.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color="#D5E0E5", width=1.4), hoverinfo="skip", showlegend=False))
    for side, members, color in ((0, left, COLORS[0]), (1, right, COLORS[1])):
        figure.add_trace(go.Scatter(
            x=[positions[uri][0] for uri in members], y=[positions[uri][1] for uri in members],
            mode="markers+text", text=["<br>".join(textwrap.wrap(nodes[uri][0], 30)) for uri in members],
            textposition="middle left" if side == 0 else "middle right",
            customdata=[[nodes[uri][1]] for uri in members],
            hovertemplate="%{text}<br>%{customdata[0]}<extra></extra>",
            marker=dict(size=15 if side == 0 else 11, color=color, line=dict(color="white", width=2)),
            showlegend=False,
        ))
    figure = polish(figure, max(480, 40 * max(len(left), len(right)) + 80))
    figure.update_layout(margin=dict(l=5, r=5, t=10, b=10))
    figure.update_xaxes(visible=False, range=[-0.9, 1.9], fixedrange=True)
    figure.update_yaxes(visible=False, range=[0, 1], fixedrange=True)
    return figure, len(nodes), len(edges)
