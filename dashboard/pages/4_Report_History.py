"""Report History — browse, view, and download past reports."""

import streamlit as st

st.set_page_config(page_title="Report History - MarketView", page_icon="📋", layout="wide")

from dashboard.workflow_state import (
    WORKFLOW_CSS,
    init_session_state,
    render_sidebar,
)
from dashboard import api_client

init_session_state()
st.markdown(WORKFLOW_CSS, unsafe_allow_html=True)
render_sidebar()

# ── Header ──────────────────────────────────────────────────

st.title("Report History")
st.caption("Browse, view, and download past reports")
st.markdown("---")

# ── Pagination State ────────────────────────────────────────

PAGE_SIZE = 10

if "report_page" not in st.session_state:
    st.session_state["report_page"] = 0

page = st.session_state["report_page"]
offset = page * PAGE_SIZE

# ── Fetch Reports ───────────────────────────────────────────

ctrl_cols = st.columns([1, 3])
with ctrl_cols[0]:
    if st.button("Refresh", type="primary"):
        st.rerun()

reports_resp = api_client.list_reports(limit=PAGE_SIZE, offset=offset)

if not reports_resp or not reports_resp.get("reports"):
    if page > 0:
        st.info("No more reports on this page.")
    else:
        st.info("No reports generated yet. Go to Step 3 to generate your first report.")

    if st.button("<< Back to Dashboard"):
        st.switch_page("app.py")
    st.stop()

reports = reports_resp["reports"]
total = reports_resp.get("total", len(reports))
total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)

st.caption(f"Showing {offset + 1}-{min(offset + len(reports), total)} of {total} reports")

# ── Report Table ────────────────────────────────────────────

for report in reports:
    report_id = report.get("report_id", "")
    title = report.get("title", "Untitled Report")
    level = report.get("level", "?")
    created = report.get("created_at", "")[:19]
    fmt = report.get("format", "markdown")

    level_label = {1: "Executive", 2: "Standard", 3: "Deep Dive"}.get(level, str(level))

    with st.expander(f"{title}  |  Level {level_label}  |  {created}  |  {fmt}"):
        # Fetch full report content
        if st.button("Load Report", key=f"load_{report_id}"):
            full = api_client.get_report(report_id)
            if full and full.get("content"):
                st.markdown(full["content"])

                # Downloads
                dl_cols = st.columns(4)
                with dl_cols[0]:
                    st.download_button(
                        "Markdown",
                        data=full["content"],
                        file_name=f"{report_id}.md",
                        mime="text/markdown",
                        key=f"dl_md_{report_id}",
                    )
                with dl_cols[1]:
                    pdf = api_client.download_report(report_id, "pdf")
                    if pdf:
                        st.download_button(
                            "PDF",
                            data=pdf,
                            file_name=f"{report_id}.pdf",
                            mime="application/pdf",
                            key=f"dl_pdf_{report_id}",
                        )
                with dl_cols[2]:
                    json_data = api_client.download_report(report_id, "json")
                    if json_data:
                        st.download_button(
                            "JSON",
                            data=json_data,
                            file_name=f"{report_id}.json",
                            mime="application/json",
                            key=f"dl_json_{report_id}",
                        )
                with dl_cols[3]:
                    html_data = api_client.download_report(report_id, "html")
                    if html_data:
                        st.download_button(
                            "HTML",
                            data=html_data,
                            file_name=f"{report_id}.html",
                            mime="text/html",
                            key=f"dl_html_{report_id}",
                        )
            else:
                st.error("Failed to load report content.")

        # Delete
        if st.button("Delete", key=f"delete_{report_id}", type="secondary"):
            result = api_client.delete_report(report_id)
            if result and result.get("status") == "deleted":
                st.success(f"Deleted report {report_id}")
                st.rerun()
            else:
                st.error("Failed to delete report.")

# ── Pagination Controls ────────────────────────────────────

st.markdown("---")
nav_cols = st.columns([1, 2, 1])
with nav_cols[0]:
    if page > 0:
        if st.button("<< Previous"):
            st.session_state["report_page"] = page - 1
            st.rerun()
with nav_cols[1]:
    st.markdown(
        f"<div style='text-align:center'>Page {page + 1} of {total_pages}</div>",
        unsafe_allow_html=True,
    )
with nav_cols[2]:
    if offset + PAGE_SIZE < total:
        if st.button("Next >>"):
            st.session_state["report_page"] = page + 1
            st.rerun()

# ── Navigation ──────────────────────────────────────────────

if st.button("<< Back to Dashboard", use_container_width=True):
    st.switch_page("app.py")
