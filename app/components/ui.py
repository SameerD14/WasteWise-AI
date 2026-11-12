import streamlit as st
from pathlib import Path
from html import escape
from textwrap import dedent

NAVY = "#142B3B"
EMERALD = "#16A879"
TEAL = "#35A995"
AMBER = "#F2B84B"
CORAL = "#EF6B68"
MUTED = "#A6B5BF"

def load_theme():
    css_path = Path(__file__).resolve().parents[1] / "assets" / "style.css"

    if not css_path.exists():
        st.warning("Theme CSS file was not found.")
        return

    css = css_path.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def page_header(title, subtitle):
    html = dedent(f"""
        <div class="ww-page-header">
            <h1>{escape(str(title))}</h1>
            <p>{escape(str(subtitle))}</p>
        </div>
    """)
    st.markdown(html, unsafe_allow_html=True)


def section_header(title, description=None):
    description_html = ""

    if description:
        description_html = (
            f'<p class="ww-section-description">'
            f'{escape(str(description))}</p>'
        )

    html = dedent(f"""
        <div class="ww-section-header">
            <h3>{escape(str(title))}</h3>
            {description_html}
        </div>
    """)
    st.markdown(html, unsafe_allow_html=True)


def kpi_card(label, value, help_text=None):
    help_html = ""

    if help_text:
        help_html = (
            f'<div class="ww-kpi-help">'
            f'{escape(str(help_text))}</div>'
        )

    html = dedent(f"""
        <div class="ww-kpi-card">
            <div class="ww-kpi-label">{escape(str(label))}</div>
            <div class="ww-kpi-value">{escape(str(value))}</div>
            {help_html}
        </div>
    """)

    st.markdown(html, unsafe_allow_html=True)


def format_currency(value):
    try:
        if value is None:
            return "₹0.00"
        return f"₹{float(value):,.2f}"
    except (ValueError, TypeError):
        return "₹0.00"


def status_badge(status):
    colors = {
        "Low Risk": EMERALD,
        "Normal": EMERALD,
        "Success": EMERALD,
        "Connected": EMERALD,
        "High Risk": AMBER,
        "Review": AMBER,
        "Warning": AMBER,
        "Expired": CORAL,
        "Critical": CORAL,
        "Disconnected": CORAL,
        "Expires Today - Immediate Review": CORAL,
    }

    safe_status = escape(str(status))
    background = colors.get(str(status), MUTED)

    html = dedent(f"""
        <span style="
            display:inline-block;
            padding:5px 12px;
            border-radius:20px;
            background:{background};
            color:#FFFFFF;
            font-size:12px;
            font-weight:600;
        ">{safe_status}</span>
    """)
    st.markdown(html, unsafe_allow_html=True)


def empty_state(
    title="No records found",
    message="There is no data available to display."
):
    html = dedent(f"""
        <div class="ww-kpi-card" style="text-align:center;padding:28px;">
            <h3>{escape(str(title))}</h3>
            <p>{escape(str(message))}</p>
        </div>
    """)
    st.markdown(html, unsafe_allow_html=True)


def database_status(connected=True):
    if connected:
        st.success("MySQL Database Connected")
    else:
        st.error("MySQL Database Disconnected")


def app_footer():
    st.divider()
    st.caption(
        "WasteWise AI | Smart Inventory Management & Food Waste Prediction"
    )


def chart_colors():
    return [EMERALD, TEAL, AMBER, CORAL, "#477C9B"]
