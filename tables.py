"""Readable study summaries and a CSV of the same directory fields."""
from html import escape

import pandas as pd

STATUS_LABELS = {
    "Completed - trial ended as planned": ("Completed", "completed"),
    "Not yet applicable (i.e., for surveillance)": ("Surveillance", "surveillance"),
    "Not yet recruiting": ("Not yet recruiting", "planned"),
    "Recruiting": ("Recruiting", "recruiting"),
}


def formatted_number(value):
    return f"{int(value):,}" if pd.notna(value) else "—"


def study_directory_csv(frame):
    columns = ["acronym", "title", "institution", "countries", "design", "status", "actual", "planned"]
    directory = frame[columns].copy()
    directory["countries"] = directory.countries.map(lambda values: "; ".join(values))
    directory["status"] = directory.status.map(lambda value: STATUS_LABELS.get(value, (value, "other"))[0])
    directory = directory.rename(columns={"acronym": "Study", "title": "Title", "institution": "Institution",
                                          "countries": "Countries", "design": "Design", "status": "Recruitment",
                                          "actual": "Actual enrolment", "planned": "Planned enrolment"})
    # Keep enrolment numeric and missing values blank. The UTF-8 signature also
    # lets spreadsheet applications recognise names containing accented text.
    return directory.to_csv(index=False).encode("utf-8-sig")


def study_table_html(frame):
    rows = []
    for row in frame.itertuples():
        status, status_class = STATUS_LABELS.get(row.status, (row.status, "other"))
        design_class = "interventional" if row.design == "Interventional" else "observational"
        progress = ""
        if pd.notna(row.actual) and pd.notna(row.planned) and row.planned > 0:
            percentage = min(max(float(row.actual) / float(row.planned) * 100, 0), 100)
            progress = f'<div class="enrolment-track" aria-hidden="true"><div style="width:{percentage:.2f}%"></div></div>'
        rows.append(
            '<tr>'
            f'<td><div class="study-name">{escape(str(row.acronym))}</div>'
            f'<div class="study-description">{escape(str(row.title))}</div></td>'
            f'<td class="institution-cell">{escape(str(row.institution))}</td>'
            f'<td class="country-cell">{escape(", ".join(row.countries) or "Not reported")}</td>'
            f'<td><span class="design-badge {design_class}">{escape(str(row.design))}</span></td>'
            f'<td><span class="status-badge {status_class}"><span class="status-dot"></span>{escape(str(status))}</span></td>'
            f'<td class="enrolment-cell"><span class="actual-count">{formatted_number(row.actual)}</span>'
            f'<span class="planned-count"> / {formatted_number(row.planned)}</span>{progress}</td>'
            '</tr>'
        )
    headers = '<tr><th scope="col">Study</th><th scope="col">Institution</th><th scope="col">Countries</th>'
    headers += '<th scope="col">Design</th><th scope="col">Recruitment</th><th scope="col" class="enrolment-cell">Actual / planned</th></tr>'
    return ('<div class="study-table-scroll" tabindex="0" role="region" aria-label="Study summaries">'
            '<table class="study-table"><caption class="sr-only">Filtered study summaries and reported enrolment</caption>'
            f'<thead>{headers}</thead><tbody>{"".join(rows)}</tbody></table></div>')
