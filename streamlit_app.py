"""
Arcnical — Streamlit Dashboard v0.2.0
======================================
Refactored from HTML prototype (arcnical_prototype_2.html) to Streamlit.

HTML → Streamlit Attribute Mapping
------------------------------------
LAYOUT
  app-shell grid (240px sidebar | 1fr main)  →  st.sidebar + st.columns / st.tabs
  header (52px, full-width)                   →  st.markdown() logo block inside sidebar top
  footer (80px, CLI/GUI tabs)                 →  st.expander("CLI / Run Configuration")

COLORS (CSS vars → inline style strings)
  --bg-base:          #0a0c10   →  [data-testid="stApp"] background
  --bg-surface:       #0f1218   →  sidebar + card backgrounds
  --bg-card:          #141820   →  st.container / metric card divs
  --bg-card-hover:    #1a2030   →  hover states via CSS
  --bg-sidebar:       #0c0e14   →  [data-testid="stSidebar"] background
  --border:           #1e2535   →  border: 1px solid #1e2535
  --border-subtle:    #151c28   →  subtle dividers
  --accent-primary:   #7c5cfc   →  buttons, active tabs, rings
  --accent-secondary: #00d4aa   →  success states, LOW severity, teal accents
  --accent-amber:     #f5a623   →  HIGH severity
  --accent-rose:      #f54b6a   →  CRITICAL severity
  --text-primary:     #e8eaf2   →  headings, primary content
  --text-secondary:   #8892a4   →  body text, labels
  --text-muted:       #4a5568   →  meta, timestamps, muted labels

TYPOGRAPHY
  --font-display:  'Syne' (800/700/600)   →  Google Font import in CSS
  --font-body:     'IBM Plex Sans' (400/500/600) →  base font
  --font-mono:     'DM Mono' (300/400/500) →  code blocks, CLI, config values

SEVERITY COLOURS
  CRITICAL → #f54b6a (rose)
  HIGH     → #f5a623 (amber)
  MEDIUM   → #7c5cfc (purple)
  LOW      → #00d4aa (teal)

COMPONENTS MAPPED
  .sev-card            → render_severity_card()
  .score-ring          → render_score_ring() (SVG via st.markdown)
  .config-panel        → render_config_panel()
  .acc-item            → st.expander() with custom styling
  .badge-pill          → render_badge()
  .chip (graph filter) → st.radio() horizontal
  .footer CLI          → st.expander + st.code
  sidebar events       → render_sidebar_events()
"""

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

import streamlit as st

# ── PAGE CONFIG (must be first Streamlit call) ──────────────────────────────
st.set_page_config(
    page_title="Arcnical — Architecture Needs Intelligence",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── DESIGN TOKENS (from HTML prototype :root vars) ──────────────────────────
COLORS = {
    "bg_base":         "#0a0c10",
    "bg_surface":      "#0f1218",
    "bg_card":         "#141820",
    "bg_card_hover":   "#1a2030",
    "bg_sidebar":      "#0c0e14",
    "border":          "#1e2535",
    "border_subtle":   "#151c28",
    "accent_primary":  "#7c5cfc",
    "accent_secondary":"#00d4aa",
    "accent_amber":    "#f5a623",
    "accent_rose":     "#f54b6a",
    "text_primary":    "#e8eaf2",
    "text_secondary":  "#8892a4",
    "text_muted":      "#4a5568",
    "critical":        "#f54b6a",
    "high":            "#f5a623",
    "medium":          "#7c5cfc",
    "low":             "#00d4aa",
}

SEV_COLOR = {
    "CRITICAL": COLORS["critical"],
    "HIGH":     COLORS["high"],
    "MEDIUM":   COLORS["medium"],
    "LOW":      COLORS["low"],
}

# ── GLOBAL CSS ───────────────────────────────────────────────────────────────
# Applies prototype fonts + overrides Streamlit defaults to match design spec.
GLOBAL_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=Syne:wght@400;600;700;800&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

/* ── ROOT ── */
:root {{
  --bg-base: {COLORS['bg_base']};
  --bg-surface: {COLORS['bg_surface']};
  --bg-card: {COLORS['bg_card']};
  --bg-card-hover: {COLORS['bg_card_hover']};
  --bg-sidebar: {COLORS['bg_sidebar']};
  --border: {COLORS['border']};
  --border-subtle: {COLORS['border_subtle']};
  --accent-primary: {COLORS['accent_primary']};
  --accent-secondary: {COLORS['accent_secondary']};
  --accent-amber: {COLORS['accent_amber']};
  --accent-rose: {COLORS['accent_rose']};
  --text-primary: {COLORS['text_primary']};
  --text-secondary: {COLORS['text_secondary']};
  --text-muted: {COLORS['text_muted']};
  --critical: {COLORS['critical']};
  --high: {COLORS['high']};
  --medium: {COLORS['medium']};
  --low: {COLORS['low']};
  --font-display: 'Syne', sans-serif;
  --font-body: 'IBM Plex Sans', sans-serif;
  --font-mono: 'DM Mono', monospace;
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 16px;
  --shadow-card: 0 4px 24px rgba(0,0,0,0.4);
}}

/* ── APP SHELL ── */
[data-testid="stApp"] {{
  background: var(--bg-base) !important;
  font-family: var(--font-body);
  font-size: 14px;
  color: var(--text-primary);
}}

[data-testid="stSidebar"] {{
  background: var(--bg-sidebar) !important;
  border-right: 1px solid var(--border) !important;
}}

[data-testid="stSidebar"] > div:first-child {{
  padding-top: 0 !important;
}}

/* ── HIDE DEFAULT STREAMLIT CHROME ── */
#MainMenu, footer, header {{visibility: hidden;}}
[data-testid="stDecoration"] {{display: none;}}

/* ── SIDEBAR COLLAPSE BUTTON ── */
/* position:fixed escapes sidebar overflow/stacking; left offset keeps it inside sidebar */
[data-testid="stSidebarCollapseButton"] {{
  visibility: visible !important;
  opacity: 1 !important;
  position: fixed !important;
  top: 0.5rem !important;
  left: 13rem !important;
  z-index: 9999999 !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  width: 2rem !important;
  height: 2rem !important;
  background: rgba(255,255,255,0.08) !important;
  border: 1px solid rgba(255,255,255,0.18) !important;
  border-radius: var(--radius-sm) !important;
  cursor: pointer !important;
  transition: border-color 0.15s, background 0.15s !important;
}}
[data-testid="stSidebarCollapseButton"]:hover {{
  background: rgba(124,92,252,0.25) !important;
  border-color: var(--accent-primary) !important;
}}
[data-testid="stSidebarCollapseButton"] svg {{
  fill: white !important;
  stroke: white !important;
}}
[data-testid="stSidebarCollapseButton"]:hover svg {{
  fill: white !important;
  stroke: white !important;
}}

/* ── SIDEBAR OPEN BUTTON (rendered in header after collapse — must escape block-container) ── */
[data-testid="stSidebarOpenButton"] {{
  visibility: visible !important;
  opacity: 1 !important;
  position: fixed !important;
  top: 0.6rem !important;
  left: 0.6rem !important;
  z-index: 9999999 !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  width: 2rem !important;
  height: 2rem !important;
  background: var(--bg-surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-sm) !important;
  cursor: pointer !important;
  transition: border-color 0.15s, background 0.15s !important;
}}
[data-testid="stSidebarOpenButton"]:hover {{
  background: var(--bg-card-hover) !important;
  border-color: var(--accent-primary) !important;
}}
[data-testid="stSidebarOpenButton"] svg {{
  fill: var(--text-secondary) !important;
  stroke: var(--text-secondary) !important;
}}
[data-testid="stSidebarOpenButton"]:hover svg {{
  fill: var(--text-primary) !important;
  stroke: var(--text-primary) !important;
}}
.block-container {{
  padding-top: 1rem !important;
  padding-bottom: 1rem !important;
  max-width: 100% !important;
}}

/* ── TYPOGRAPHY ── */
h1, h2, h3, h4 {{
  font-family: var(--font-display) !important;
  color: var(--text-primary) !important;
}}

p, span, label {{
  font-family: var(--font-body);
  color: var(--text-secondary);
}}

code, pre {{
  font-family: var(--font-mono) !important;
  background: var(--bg-surface) !important;
  color: var(--accent-secondary) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-sm) !important;
}}

/* ── SIDEBAR COMPONENTS ── */
.sidebar-logo-block {{
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border);
  padding: 12px 16px;
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 0;
}}

.logo-icon {{
  width: 30px; height: 30px;
  border-radius: 50%;
  background: conic-gradient(from 0deg, var(--accent-primary), var(--accent-secondary), var(--accent-primary));
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 800; color: white;
  font-family: var(--font-display);
  position: relative; flex-shrink: 0;
}}

.logo-icon::after {{
  content: ''; position: absolute; inset: 2px;
  border-radius: 50%; background: var(--bg-surface);
}}

.logo-icon-letter {{ position: relative; z-index: 1; }}

.logo-text {{
  font-family: var(--font-display);
  font-size: 18px; font-weight: 800;
  color: var(--text-primary); letter-spacing: -0.3px;
}}

.logo-tag {{
  font-size: 11px; color: var(--text-muted);
  font-family: var(--font-mono);
  letter-spacing: 0.05em; text-transform: uppercase;
}}

.sidebar-section-label {{
  font-size: 11px; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.08em;
  color: var(--text-muted);
  font-family: var(--font-display);
  padding: 10px 0 6px 0;
  border-bottom: 1px solid var(--border-subtle);
  margin-bottom: 8px;
}}

/* ── EVENT CARDS (sidebar history) ── */
.event-card {{
  padding: 8px 12px;
  border-bottom: 1px solid var(--border-subtle);
  border-left: 2px solid transparent;
  cursor: pointer;
  transition: background 0.15s;
  margin-bottom: 2px;
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
}}

.event-card.completed {{ border-left-color: var(--accent-secondary); }}
.event-card.warning   {{ border-left-color: var(--accent-amber); }}
.event-card.error     {{ border-left-color: var(--critical); }}

.event-title {{
  font-size: 13px; font-weight: 600;
  color: var(--text-primary); margin-bottom: 1px;
}}

.event-sub {{
  font-size: 12px; color: var(--text-muted);
  font-family: var(--font-mono);
}}

/* ── SEVERITY CARDS ── */
.sev-card {{
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 18px 20px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  border-left: 3px solid;
  transition: transform 0.18s;
  margin-bottom: 0;
}}

.sev-card:hover {{ transform: translateY(-1px); }}
.sev-card.critical {{ border-left-color: var(--critical); }}
.sev-card.high     {{ border-left-color: var(--high); }}
.sev-card.medium   {{ border-left-color: var(--medium); }}
.sev-card.low      {{ border-left-color: var(--low); }}

.sev-label {{
  font-family: var(--font-display); font-size: 11px;
  font-weight: 700; letter-spacing: 0.1em;
  text-transform: uppercase; margin-bottom: 4px;
}}

.sev-card.critical .sev-label {{ color: var(--critical); }}
.sev-card.high .sev-label     {{ color: var(--high); }}
.sev-card.medium .sev-label   {{ color: var(--medium); }}
.sev-card.low .sev-label      {{ color: var(--low); }}

.sev-meta {{ font-size: 12px; color: var(--text-muted); }}
.sev-desc {{ font-size: 12px; color: var(--text-muted); margin-top: 2px; }}

.sev-count {{
  font-family: var(--font-display);
  font-size: 44px; font-weight: 800;
  line-height: 1; letter-spacing: -2px;
}}

.sev-card.critical .sev-count {{ color: var(--critical); }}
.sev-card.high .sev-count     {{ color: var(--high); }}
.sev-card.medium .sev-count   {{ color: var(--medium); }}
.sev-card.low .sev-count      {{ color: var(--low); }}

/* ── CONFIG PANEL ── */
.config-panel {{
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 16px;
}}

.panel-label {{
  font-size: 11px; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.1em;
  color: var(--text-muted); margin-bottom: 12px;
  font-family: var(--font-display);
}}

.config-row {{
  display: flex; justify-content: space-between;
  align-items: center; padding: 4px 0;
  border-bottom: 1px solid var(--border-subtle);
}}

.config-row:last-child {{ border-bottom: none; }}

.config-key {{
  font-size: 12px; color: var(--text-muted);
  font-family: var(--font-mono);
}}

.config-val {{
  font-size: 12px; color: var(--text-secondary);
  font-family: var(--font-mono); text-align: right;
}}

.config-val.ready {{ color: var(--accent-secondary); }}

/* ── SCORES PANEL ── */
.scores-panel {{
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 16px;
}}

.score-item {{ text-align: center; }}

.score-label {{
  font-size: 11px; text-transform: uppercase;
  letter-spacing: 0.07em; color: var(--text-muted);
  font-family: var(--font-display); font-weight: 600;
  margin-bottom: 6px;
}}

/* ── BADGE PILLS ── */
.badge-pill {{
  display: inline-flex; align-items: center;
  padding: 2px 8px; border-radius: 12px;
  font-size: 11px; font-weight: 600;
  font-family: var(--font-display);
  text-transform: uppercase; letter-spacing: 0.05em;
}}

.pill-critical {{ background: rgba(245,75,106,0.12); color: var(--critical); }}
.pill-high     {{ background: rgba(245,166,35,0.12);  color: var(--high); }}
.pill-medium   {{ background: rgba(124,92,252,0.12); color: var(--medium); }}
.pill-low      {{ background: rgba(0,212,170,0.12);  color: var(--low); }}
.pill-ok       {{ background: rgba(0,212,170,0.12);  color: var(--low); }}

/* ── METRIC CARD ── */
.metric-card {{
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 16px;
}}

.metric-card-title {{
  font-size: 11px; text-transform: uppercase;
  letter-spacing: 0.08em; color: var(--text-muted);
  font-family: var(--font-display); font-weight: 700;
  margin-bottom: 8px;
}}

.metric-value {{
  font-family: var(--font-display);
  font-size: 30px; font-weight: 800;
  color: var(--text-primary); letter-spacing: -1px;
  margin-bottom: 4px;
}}

.metric-sub {{ font-size: 12px; color: var(--text-muted); }}

.metric-bar-wrap {{
  height: 4px; background: var(--border);
  border-radius: 2px; margin-top: 10px; overflow: hidden;
}}

.metric-bar {{
  height: 100%; border-radius: 2px;
}}

/* ── TABLE ── */
.data-table {{
  width: 100%; border-collapse: collapse;
  font-size: 13px; margin-bottom: 0;
}}

.data-table th {{
  padding: 10px 14px; text-align: left;
  font-size: 11px; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.07em;
  color: var(--text-muted); background: var(--bg-surface);
  border-bottom: 1px solid var(--border);
  font-family: var(--font-display);
}}

.data-table td {{
  padding: 9px 14px; border-bottom: 1px solid var(--border-subtle);
  color: var(--text-secondary); font-family: var(--font-mono); font-size: 13px;
}}

.data-table tr:last-child td {{ border-bottom: none; }}
.data-table tr:hover td {{ background: var(--bg-card-hover); color: var(--text-primary); }}

/* ── ACCORDION FINDINGS ── */
.acc-item {{
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  margin-bottom: 6px; overflow: hidden;
}}

.acc-item:hover {{ border-color: rgba(124,92,252,0.3); }}

.acc-header {{
  display: flex; align-items: center; gap: 10px;
  padding: 12px 16px; cursor: pointer;
}}

.acc-severity-dot {{
  width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;
}}

.acc-title {{
  flex: 1; font-size: 14px; font-weight: 600; color: var(--text-primary);
}}

.acc-meta {{
  display: flex; align-items: center; gap: 8px;
  font-size: 12px; color: var(--text-muted); font-family: var(--font-mono);
}}

.acc-body {{
  padding: 16px; border-top: 1px solid var(--border-subtle);
}}

.acc-details-grid {{
  display: grid; grid-template-columns: 1fr 1fr;
  gap: 10px; margin-bottom: 12px;
}}

.acc-detail-group {{
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm); padding: 10px;
}}

.acc-detail-key {{
  font-size: 11px; text-transform: uppercase;
  letter-spacing: 0.08em; color: var(--text-muted);
  font-family: var(--font-display); font-weight: 700; margin-bottom: 3px;
}}

.acc-detail-val {{
  font-size: 13px; color: var(--text-secondary);
  font-family: var(--font-mono);
}}

.acc-rationale {{
  font-size: 13px; color: var(--text-muted); line-height: 1.6;
  padding: 10px; background: var(--bg-surface);
  border-radius: var(--radius-sm);
  border-left: 2px solid var(--accent-primary);
}}

/* ── FILE TREE ── */
.files-tree {{
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md); padding: 16px;
}}

.file-stat-card {{
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md); padding: 14px; text-align: center;
}}

.fsc-val {{
  font-family: var(--font-display);
  font-size: 24px; font-weight: 800;
  color: var(--text-primary); letter-spacing: -0.5px;
}}

.fsc-label {{
  font-size: 11px; color: var(--text-muted);
  text-transform: uppercase; letter-spacing: 0.06em; margin-top: 3px;
}}

/* ── CLI BLOCK ── */
.cli-block {{
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 14px 16px;
}}

.cli-label {{
  font-size: 11px; text-transform: uppercase;
  letter-spacing: 0.1em; color: var(--text-muted);
  font-family: var(--font-display); font-weight: 700; margin-bottom: 8px;
}}

.cli-cmd {{
  font-family: var(--font-mono); font-size: 13px;
  color: var(--accent-secondary); word-break: break-all;
}}

/* ── STREAMLIT WIDGET OVERRIDES ── */
.stButton > button {{
  background: var(--accent-primary) !important;
  color: white !important;
  border: none !important;
  border-radius: var(--radius-sm) !important;
  font-family: var(--font-body) !important;
  font-size: 13px !important;
  font-weight: 600 !important;
  transition: opacity 0.15s !important;
}}

.stButton > button:hover {{
  opacity: 0.9 !important;
  color: white !important;
}}
.stButton > button p,
.stButton > button span,
.stButton > button div {{
  color: white !important;
}}

/* ── SELECTBOX / MULTISELECT ACTIVE OPTION ── */
[data-baseweb="menu"] [aria-selected="true"],
[data-baseweb="menu"] [aria-selected="true"] *,
[data-baseweb="menu"] li:hover,
[data-baseweb="menu"] li:hover * {{
  color: white !important;
}}
[data-baseweb="tag"] {{
  background: var(--accent-primary) !important;
  color: white !important;
}}
[data-baseweb="tag"] * {{
  color: white !important;
}}

.stSelectbox > div > div {{
  background: var(--bg-card) !important;
  border: 1px solid var(--border) !important;
  color: var(--text-primary) !important;
  font-family: var(--font-mono) !important;
  font-size: 13px !important;
}}

.stRadio > div {{
  gap: 12px;
}}

.stRadio label {{
  color: var(--text-secondary) !important;
  font-size: 13px !important;
  font-family: var(--font-body) !important;
}}
[data-testid="stRadio"] [data-checked="true"] ~ div p,
[data-testid="stRadio"] [data-checked="true"] ~ div span,
[data-baseweb="radio"] input:checked ~ div {{
  color: white !important;
}}

.stTextInput > div > div > input {{
  background: var(--bg-card) !important;
  border: 1px solid var(--border) !important;
  color: var(--text-primary) !important;
  font-family: var(--font-mono) !important;
  font-size: 13px !important;
  border-radius: var(--radius-sm) !important;
}}

.stTextInput > div > div > input:focus {{
  border-color: var(--accent-primary) !important;
  box-shadow: none !important;
}}

/* ── TABS (nav) ── */
.stTabs [data-baseweb="tab-list"] {{
  background: var(--bg-surface) !important;
  border-bottom: 1px solid var(--border) !important;
  gap: 2px !important;
  padding: 6px 8px 0 8px !important;
}}

.stTabs [data-baseweb="tab"] {{
  background: transparent !important;
  border-radius: var(--radius-sm) var(--radius-sm) 0 0 !important;
  color: var(--text-secondary) !important;
  font-family: var(--font-body) !important;
  font-size: 13px !important;
  font-weight: 500 !important;
  padding: 6px 14px !important;
  border: 1px solid transparent !important;
}}

.stTabs [aria-selected="true"] {{
  background: var(--accent-primary) !important;
  color: white !important;
  border-color: rgba(124,92,252,0.3) !important;
}}
.stTabs [aria-selected="true"] p,
.stTabs [aria-selected="true"] span,
.stTabs [aria-selected="true"] div {{
  color: white !important;
}}

.stTabs [data-baseweb="tab-panel"] {{
  background: var(--bg-base) !important;
  padding: 20px 0 !important;
}}

.stTabs [data-baseweb="tab-border"] {{
  display: none !important;
}}

/* ── METRIC WIDGET ── */
[data-testid="stMetric"] {{
  background: var(--bg-card) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-md) !important;
  padding: 16px !important;
}}

[data-testid="stMetricLabel"] {{
  font-family: var(--font-display) !important;
  font-size: 11px !important;
  font-weight: 700 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.08em !important;
  color: var(--text-muted) !important;
}}

[data-testid="stMetricValue"] {{
  font-family: var(--font-display) !important;
  font-size: 30px !important;
  font-weight: 800 !important;
  color: var(--text-primary) !important;
}}

/* ── EXPANDER ── */
.streamlit-expanderHeader {{
  background: var(--bg-card) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-md) !important;
  color: var(--text-primary) !important;
  font-family: var(--font-body) !important;
  font-size: 14px !important;
  font-weight: 600 !important;
}}

.streamlit-expanderContent {{
  background: var(--bg-card) !important;
  border: 1px solid var(--border) !important;
  border-top: none !important;
  border-radius: 0 0 var(--radius-md) var(--radius-md) !important;
}}

/* ── SECTION HEADERS ── */
.section-header-row {{
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 14px;
}}

.section-title {{
  font-family: var(--font-display); font-size: 15px; font-weight: 700;
  color: var(--text-primary);
}}

.page-title {{
  font-family: var(--font-display); font-size: 22px; font-weight: 700;
  color: var(--text-primary); margin-bottom: 20px; letter-spacing: -0.3px;
}}

/* ── GRAPH PAGE ── */
.graph-legend {{
  display: flex; gap: 16px; align-items: center; flex-wrap: wrap;
  font-size: 12px; padding: 12px;
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: var(--radius-md); margin-top: 12px;
}}

.legend-item {{
  display: flex; align-items: center; gap: 6px; color: var(--text-secondary);
}}

.legend-dot {{
  width: 8px; height: 8px; border-radius: 50%; display: inline-block;
}}

/* ── ABOUT PAGE ── */
.about-hero {{
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 32px; margin-bottom: 20px;
  position: relative; overflow: hidden;
}}

.about-hero-title {{
  font-family: var(--font-display); font-size: 30px; font-weight: 800;
  letter-spacing: -0.5px; margin-bottom: 6px; color: var(--text-primary);
}}

.about-hero-tag {{
  font-family: var(--font-mono); font-size: 12px; color: var(--accent-primary);
  text-transform: uppercase; letter-spacing: 0.12em; margin-bottom: 14px;
}}

.about-hero-desc {{
  font-size: 14px; color: var(--text-secondary); line-height: 1.7; max-width: 640px;
}}

.team-card {{
  display: flex; align-items: center; gap: 12px;
  padding: 10px; background: var(--bg-surface);
  border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);
  margin-bottom: 8px;
}}

.team-name {{ font-size: 14px; font-weight: 600; color: var(--text-primary); }}
.team-role {{ font-size: 12px; color: var(--text-muted); font-family: var(--font-mono); }}

/* ── HORIZONTAL BAR ── */
.hbar-group {{ margin-bottom: 10px; }}
.hbar-label {{
  display: flex; justify-content: space-between;
  font-size: 12px; color: var(--text-secondary);
  margin-bottom: 4px; font-family: var(--font-mono);
}}

.hbar-track {{
  height: 6px; background: var(--border);
  border-radius: 3px; overflow: hidden;
}}

.hbar-fill {{ height: 100%; border-radius: 3px; }}

/* ── STATUS BADGE ── */
.status-badge {{
  display: inline-flex; align-items: center; gap: 5px;
  padding: 3px 10px; border-radius: 20px;
  font-size: 12px; font-weight: 600;
  font-family: var(--font-mono);
}}

.status-ready   {{ background: rgba(0,212,170,0.12); color: var(--accent-secondary); }}
.status-running {{ background: rgba(124,92,252,0.12); color: var(--accent-primary); }}
.status-error   {{ background: rgba(245,75,106,0.12); color: var(--critical); }}

/* ── DIVIDER ── */
hr {{
  border: none !important;
  border-top: 1px solid var(--border) !important;
  margin: 16px 0 !important;
}}

/* ── SCROLLBAR ── */
::-webkit-scrollbar {{ width: 4px; height: 4px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 2px; }}
</style>
"""


# ── COMPONENT HELPERS ────────────────────────────────────────────────────────

def render_severity_card(level: str, count: int, meta: str, desc: str) -> str:
    """
    HTML → .sev-card (.critical/.high/.medium/.low)
    Returns HTML string for st.markdown(unsafe_allow_html=True).
    """
    css_class = level.lower()
    return f"""
    <div class="sev-card {css_class}">
      <div>
        <div class="sev-label">{level}</div>
        <div class="sev-meta">{meta}</div>
        <div class="sev-desc">{desc}</div>
      </div>
      <div class="sev-count">{count}</div>
    </div>
    """


def render_score_ring(label: str, value: int, color: str) -> str:
    """
    Builds one score-ring cell as a raw HTML string.
    Must be used inside render_scores_panel_component() which renders via
    st.iframe() — the only Streamlit call that does NOT sanitise SVG.
    Circumference of r=22 circle = 2π×22 ≈ 138.2
    """
    circ = 138.2
    offset = circ * (1 - value / 100)
    return (
        f'<div style="text-align:center;padding:4px;">' +
        f'<div style="font-size:11px;text-transform:uppercase;letter-spacing:0.07em;' +
        f'color:#4a5568;font-family:Syne,sans-serif;font-weight:600;margin-bottom:10px;">' +
        f'{label}</div>' +
        f'<div style="position:relative;width:54px;height:54px;margin:0 auto 4px;">' +
        f'<svg viewBox="0 0 54 54" width="54" height="54" ' +
        f'style="display:block;transform:rotate(-90deg);">' +
        f'<circle cx="27" cy="27" r="22" fill="none" stroke="#1e2535" stroke-width="4"/>' +
        f'<circle cx="27" cy="27" r="22" fill="none" stroke="{color}" stroke-width="4" ' +
        f'stroke-dasharray="{circ:.1f}" stroke-dashoffset="{offset:.1f}" stroke-linecap="round"/>' +
        f'</svg>' +
        f'<div style="position:absolute;top:0;left:0;width:54px;height:54px;' +
        f'display:flex;align-items:center;justify-content:center;' +
        f'font-family:Syne,sans-serif;font-size:14px;font-weight:700;color:{color};">' +
        f'{value}%</div>' +
        f'</div></div>'
    )


def render_scores_panel_component(score_items: list) -> None:
    """
    Renders the Architectural Health Scores card via st.iframe()
    to avoid Streamlit's markdown sanitiser stripping <svg> and <circle> tags.
    score_items: list of (label, value, color) tuples.
    """
    rings = "".join(render_score_ring(lbl, val, clr) for lbl, val, clr in score_items)

    html = (
        '<!DOCTYPE html><html><head>' +
        '<link href="https://fonts.googleapis.com/css2?family=Syne:wght@600;700&display=swap" rel="stylesheet">' +
        '<style>*{margin:0;padding:0;box-sizing:border-box;}body{background:transparent;}</style>' +
        '</head><body>' +
        '<div style="background:#141820;border:1px solid #1e2535;border-radius:10px;padding:16px 20px;">' +
        '<div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;' +
        'color:#4a5568;margin-bottom:16px;font-family:Syne,sans-serif;">' +
        'Architectural Health Scores</div>' +
        '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;">' +
        rings +
        '</div></div>' +
        '</body></html>'
    )
    # height: label(28) + ring(54) + value + padding ≈ 155px
    st.iframe(html, height=155)


def render_badge(level: str) -> str:
    """HTML → .badge-pill .pill-{level}"""
    css = level.lower().replace("ok", "ok")
    return f'<span class="badge-pill pill-{css}">{level}</span>'


def render_hbar(label: str, value: float, max_val: float, color: str) -> str:
    """HTML → .hbar-group (horizontal progress bar) — fully inline styled."""
    pct = min(100, (value / max_val * 100)) if max_val > 0 else 0
    return f"""
    <div style="margin-bottom:10px;">
      <div style="display:flex;justify-content:space-between;font-size:12px;
                  color:#8892a4;margin-bottom:4px;font-family:'DM Mono',monospace;">
        <span>{label}</span><span>{value:.1f}</span>
      </div>
      <div style="height:6px;background:#1e2535;border-radius:3px;overflow:hidden;">
        <div style="height:100%;width:{pct:.1f}%;background:{color};border-radius:3px;"></div>
      </div>
    </div>
    """


def render_event_card(title: str, sub: str, status: str) -> str:
    """HTML → .event-card (.completed/.warning/.error)"""
    status_map = {"ok": "completed", "warn": "warning", "err": "error"}
    css = status_map.get(status, "completed")
    return f"""
    <div class="event-card {css}">
      <div class="event-title">{title}</div>
      <div class="event-sub">{sub}</div>
    </div>
    """


def render_cli_block(cmd: str, label: str = "CLI Command") -> str:
    """HTML → .cli-block (monospace command display)"""
    return f"""
    <div class="cli-block">
      <div class="cli-label">{label}</div>
      <div class="cli-cmd">$ {cmd}</div>
    </div>
    """


# ── DATA LOADING ─────────────────────────────────────────────────────────────

def load_analysis_data(json_path: Optional[str] = None) -> Optional[dict]:
    """
    Load analysis JSON from json_exporter.py output.
    Falls back to demo data if file not found.
    Integration: orchestrator.py → json_exporter.py → analysis_output.json
    """
    if json_path and Path(json_path).exists():
        try:
            with open(json_path) as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Failed to load analysis data: {e}")
            return None

    # ── Demo / placeholder data matching prototype values ──
    return {
        "repo_path": "arcnical/arcnical",
        "analysis_timestamp": "2026-04-14T16:41:00",
        "llm_provider": "claude",
        "llm_model": "claude-sonnet-4-6",
        "analysis_depth": "standard",
        "status": "completed",
        "scores": {
            "overall": 85,
            "maintainability": 78,
            "security": 92,
            "complexity": 74,
        },
        "findings_summary": {
            "critical": 3,
            "high": 1,
            "medium": 12,
            "low": 0,
            "total": 16,
        },
        "metrics": {
            "total_files": 28,
            "total_loc": 3240,
            "yaml_configs": 4,
            "test_cases": 90,
            "avg_complexity": 9.2,
            "avg_loc_per_file": 115.7,
        },
        "findings": [
            {
                "id": "F-001",
                "title": "Circular Import: orchestrator.py ↔ graph_builder.py",
                "severity": "CRITICAL",
                "layer": "L1 — Qualification",
                "file": "orchestrator.py",
                "line": 12,
                "verified": True,
                "rationale": "A circular import creates a tight coupling between orchestrator.py and graph_builder.py. Refactor by extracting the shared interface into a dedicated protocols.py module to break the cycle.",
            },
            {
                "id": "F-002",
                "title": "Circular Import: schemas/models.py ↔ parsers/python_parser.py",
                "severity": "CRITICAL",
                "layer": "L1 — Qualification",
                "file": "schemas/models.py",
                "line": 5,
                "verified": True,
                "rationale": "Bidirectional import between schema models and parser. Parser should only import from schemas, not vice versa. Extract parser-specific types to break cycle.",
            },
            {
                "id": "F-003",
                "title": "God Class: Orchestrator has 24 public methods",
                "severity": "HIGH",
                "layer": "L2 — Heuristics",
                "file": "orchestrator.py",
                "line": 1,
                "verified": False,
                "rationale": "The Orchestrator class violates SRP with 24 public methods. Decompose into AnalysisCoordinator, ReportCoordinator, and ProviderCoordinator classes.",
            },
            {
                "id": "F-004",
                "title": "High Cyclomatic Complexity in orchestrator.py",
                "severity": "MEDIUM",
                "layer": "L2 — Heuristics",
                "file": "orchestrator.py",
                "line": 48,
                "verified": False,
                "rationale": "Function run_analysis() has cyclomatic complexity of 18.4 — well above the recommended threshold of 10. Decompose into smaller, testable units.",
            },
            {
                "id": "F-005",
                "title": "Unstable Module: graph_builder.py",
                "severity": "MEDIUM",
                "layer": "L2 — Heuristics",
                "file": "graph_builder.py",
                "line": 1,
                "verified": False,
                "rationale": "Module instability index of 0.82 (dependents: 2, dependencies: 11). High fan-out indicates this module is brittle to upstream changes.",
            },
            {
                "id": "F-006",
                "title": "Large File: parsers/python_parser.py",
                "severity": "MEDIUM",
                "layer": "L2 — Heuristics",
                "file": "parsers/python_parser.py",
                "line": 1,
                "verified": False,
                "rationale": "File exceeds 250 LOC threshold at 295 lines. Consider splitting visitor methods into a dedicated visitor module.",
            },
            {
                "id": "F-007",
                "title": "Secrets Scanning: Low Coverage",
                "severity": "CRITICAL",
                "layer": "L3 — Security",
                "file": "configs/layer3.yaml",
                "line": 4,
                "verified": True,
                "rationale": "Security layer configuration only covers 3 of 8 recommended secret patterns. Expand gitleaks ruleset to include GitHub tokens, AWS keys, and JWT secrets.",
            },
            {
                "id": "F-008",
                "title": "Missing Type Annotations in LLM Provider",
                "severity": "MEDIUM",
                "layer": "L2 — Heuristics",
                "file": "llm/claude_provider.py",
                "line": 32,
                "verified": False,
                "rationale": "Several public methods lack return type annotations. Add full PEP 484 annotations to enable static analysis and improve IDE support.",
            },
        ],
        "module_metrics": [
            {"module": "orchestrator.py", "loc": 480, "complexity": 18.4, "functions": 24, "classes": 2, "dependencies": 12, "risk": "CRITICAL"},
            {"module": "graph_builder.py", "loc": 320, "complexity": 11.2, "functions": 18, "classes": 1, "dependencies": 8, "risk": "HIGH"},
            {"module": "parsers/python_parser.py", "loc": 295, "complexity": 9.8, "functions": 15, "classes": 1, "dependencies": 6, "risk": "MEDIUM"},
            {"module": "parsers/ts_parser.py", "loc": 280, "complexity": 9.1, "functions": 14, "classes": 1, "dependencies": 5, "risk": "MEDIUM"},
            {"module": "report/formatters.py", "loc": 260, "complexity": 7.3, "functions": 12, "classes": 3, "dependencies": 4, "risk": "LOW"},
            {"module": "cli/main.py", "loc": 240, "complexity": 6.9, "functions": 10, "classes": 0, "dependencies": 7, "risk": "LOW"},
            {"module": "schemas/models.py", "loc": 220, "complexity": 4.2, "functions": 8, "classes": 14, "dependencies": 2, "risk": "OK"},
            {"module": "heuristics/detectors.py", "loc": 210, "complexity": 8.6, "functions": 16, "classes": 6, "dependencies": 5, "risk": "MEDIUM"},
            {"module": "llm/providers/claude.py", "loc": 180, "complexity": 5.4, "functions": 9, "classes": 1, "dependencies": 3, "risk": "LOW"},
            {"module": "ui/sidebar_enhanced.py", "loc": 165, "complexity": 4.8, "functions": 11, "classes": 0, "dependencies": 4, "risk": "OK"},
        ],
        "graph_data_path": None,   # path to pyvis HTML; None = use graph_builder
        "cli_command": None,       # populated by cli_bridge
    }


# ── SIDEBAR ──────────────────────────────────────────────────────────────────

def render_sidebar(data: dict) -> dict:
    """
    Renders left sidebar matching HTML prototype layout:
      - Logo (header)
      - Provider / depth controls
      - Re-run button + status
      - Repo history (event cards)
    Returns dict of selected options for main area.
    """
    with st.sidebar:
        # ── Logo (HTML → .sidebar-logo-block) ──
        st.markdown("""
        <div class="sidebar-logo-block">
          <div class="logo-icon"><span class="logo-icon-letter">A</span></div>
          <div>
            <div class="logo-text">Arcnical</div>
            <div class="logo-tag">Architecture Needs Intelligence</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

        # ── Config Controls (HTML → .provider-btn-wrap + .depth-group) ──
        st.markdown('<div class="sidebar-section-label">Configuration</div>', unsafe_allow_html=True)

        provider = st.selectbox(
            "LLM Provider",
            options=["claude", "openai", "gemini"],
            index=["claude", "openai", "gemini"].index(
                data.get("llm_provider", "claude")
            ),
            key="provider_select",
            label_visibility="collapsed",
        )

        # Provider model display
        model_map = {
            "claude": "claude-sonnet-4-6",
            "openai": "gpt-4o",
            "gemini": "gemini-1.5-pro",
        }
        model_name = model_map.get(provider, "claude-sonnet-4-6")

        depth = st.radio(
            "Analysis Depth",
            options=["quick", "standard"],
            index=0 if data.get("analysis_depth", "standard") == "quick" else 1,
            key="depth_radio",
            horizontal=True,
        )

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        # ── Repo input ──
        repo_path = st.text_input(
            "Repository Path",
            value=data.get("repo_path", ""),
            placeholder="owner/repo or /local/path",
            key="repo_input",
        )

        # ── Re-run button + status ──
        col_btn, col_status = st.columns([3, 2])
        with col_btn:
            run_clicked = st.button("⬡ Analyze", use_container_width=True)
        with col_status:
            status = data.get("status", "completed")
            status_css = {"completed": "ready", "running": "running", "error": "error"}.get(status, "ready")
            status_label = {"completed": "Ready", "running": "Running…", "error": "Error"}.get(status, "Ready")
            st.markdown(
                f'<div style="display:flex;align-items:center;height:100%;">'
                f'<span class="status-badge status-{status_css}">{status_label}</span></div>',
                unsafe_allow_html=True,
            )

        st.markdown("<hr>", unsafe_allow_html=True)

        # ── Config display (HTML → .config-panel) ──
        ts = data.get("analysis_timestamp", "")
        try:
            ts_fmt = datetime.fromisoformat(ts).strftime("%Y-%m-%d %H:%M")
        except Exception:
            ts_fmt = ts or "—"

        config_rows = [
            ("Model",        model_name),
            ("Provider",     provider.capitalize()),
            ("Depth",        depth.capitalize()),
            ("Last Run",     ts_fmt),
            ("Findings",     str(data.get("findings_summary", {}).get("total", "—"))),
            ("Files",        str(data.get("metrics", {}).get("total_files", "—"))),
        ]

        rows_html = "".join(
            f'<div class="config-row">'
            f'<span class="config-key">{k}</span>'
            f'<span class="config-val{"  ready" if k=="Status" else ""}">{v}</span>'
            f'</div>'
            for k, v in config_rows
        )

        st.markdown(
            f'<div class="config-panel">'
            f'<div class="panel-label">Session Config</div>'
            f'{rows_html}'
            f'</div>',
            unsafe_allow_html=True,
        )

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

        # ── Repo History / Event Cards (HTML → .sidebar-events) ──
        st.markdown('<div class="sidebar-section-label">Recent Analyses</div>', unsafe_allow_html=True)

        history_events = [
            ("arcnical/arcnical",     "2026-04-14 16:41 · 16 findings", "ok"),
            ("arcnical/arcnical",     "2026-04-14 14:12 · 18 findings", "warn"),
            ("test/sample-repo",      "2026-04-13 09:05 · 4 findings",  "ok"),
            ("internal/legacy-svc",   "2026-04-12 17:30 · 31 findings", "err"),
        ]

        for title, sub, status in history_events:
            st.markdown(render_event_card(title, sub, status), unsafe_allow_html=True)

    return {
        "provider": provider,
        "depth": depth,
        "repo_path": repo_path,
        "run_clicked": run_clicked,
        "model": model_name,
    }


# ── PAGE: OVERVIEW ───────────────────────────────────────────────────────────

def render_overview(data: dict):
    st.markdown('<div class="page-title">Analysis Overview</div>', unsafe_allow_html=True)

    summary = data.get("findings_summary", {})

    # ── Severity Cards 2×2 grid (HTML → .severity-grid) ──
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(render_severity_card("CRITICAL", summary.get("critical", 0),
                                         "Circular Imports", "Requires immediate attention"),
                    unsafe_allow_html=True)
    with c2:
        st.markdown(render_severity_card("HIGH", summary.get("high", 0),
                                         "God Classes Detected", "Significant risk to maintainability"),
                    unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    c3, c4 = st.columns(2)
    with c3:
        st.markdown(render_severity_card("MEDIUM", summary.get("medium", 0),
                                         "High Complexity Modules", "Refactoring recommended"),
                    unsafe_allow_html=True)
    with c4:
        st.markdown(render_severity_card("LOW", summary.get("low", 0),
                                         "Style & Convention", "Minor improvements available"),
                    unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Config + Scores row (HTML → .config-scores-row) ──
    scores = data.get("scores", {})
    cfg_col, scores_col = st.columns([3, 7])

    with cfg_col:
        # Config panel — already shown in sidebar; show repo/findings summary here
        ts = data.get("analysis_timestamp", "")
        try:
            ts_fmt = datetime.fromisoformat(ts).strftime("%Y-%m-%d %H:%M")
        except Exception:
            ts_fmt = ts or "—"

        config_rows = [
            ("Status",        '<span class="config-val ready">Ready</span>'),
            ("Model",         data.get("llm_model", "—")),
            ("Provider",      data.get("llm_provider", "—").capitalize()),
            ("Depth",         data.get("analysis_depth", "—").capitalize()),
            ("Last Run",      ts_fmt),
            ("Findings",      str(summary.get("total", "—"))),
            ("Files Analyzed",str(data.get("metrics", {}).get("total_files", "—"))),
            ("Repo",          data.get("repo_path", "—")),
        ]

        rows_html = "".join(
            f'<div class="config-row">'
            f'<span class="config-key">{k}</span>'
            f'{"" if k == "Status" else "<span class=config-val>"}{v}{"" if k == "Status" else "</span>"}'
            f'</div>'
            for k, v in config_rows
        )

        st.markdown(
            f'<div class="config-panel">'
            f'<div class="panel-label">Configuration</div>'
            f'{rows_html}'
            f'</div>',
            unsafe_allow_html=True,
        )

    with scores_col:
        score_items = [
            ("Overall",         scores.get("overall", 85),        COLORS["accent_primary"]),
            ("Maintainability", scores.get("maintainability", 78), COLORS["accent_amber"]),
            ("Security",        scores.get("security", 92),        COLORS["accent_secondary"]),
            ("Complexity",      scores.get("complexity", 74),      COLORS["accent_rose"]),
        ]
        # Use components.html to bypass Streamlit markdown SVG sanitiser
        render_scores_panel_component(score_items)


# ── PAGE: METRICS ────────────────────────────────────────────────────────────

def render_metrics(data: dict):
    st.markdown('<div class="page-title">Metrics</div>', unsafe_allow_html=True)

    metrics = data.get("metrics", {})
    mods = data.get("module_metrics", [])

    # ── Summary metric cards (HTML → .metrics-grid 3-col) ──
    col1, col2, col3 = st.columns(3)

    def metric_card_html(title: str, value: str, sub: str, bar_pct: float, bar_color: str) -> str:
        return f"""
        <div class="metric-card">
          <div class="metric-card-title">{title}</div>
          <div class="metric-value">{value}</div>
          <div class="metric-sub">{sub}</div>
          <div class="metric-bar-wrap">
            <div class="metric-bar" style="width:{bar_pct:.0f}%;background:{bar_color};"></div>
          </div>
        </div>
        """

    with col1:
        st.html(metric_card_html(
            "Total Files", str(metrics.get("total_files", 28)), "Python source files",
            metrics.get("total_files", 28) / 50 * 100, COLORS["accent_primary"]))

    with col2:
        st.html(metric_card_html(
            "Lines of Code", f"{metrics.get('total_loc', 3240):,}", "Across all modules",
            metrics.get("total_loc", 3240) / 5000 * 100, COLORS["accent_secondary"]))

    with col3:
        avg_cx = metrics.get("avg_complexity", 9.2)
        st.html(metric_card_html(
            "Avg Complexity", f"{avg_cx:.1f}", "Cyclomatic complexity",
            min(100, avg_cx / 20 * 100), COLORS["accent_amber"]))

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Horizontal bar charts ──
    hcol1, hcol2 = st.columns(2)
    with hcol1:
        if mods:
            top5 = sorted(mods, key=lambda m: m["complexity"], reverse=True)[:5]
            bars = "".join(render_hbar(m["module"].split("/")[-1], m["complexity"], 25.0, COLORS["accent_rose"])
                           for m in top5)
            st.html(
                f'<div style="background:#141820;border:1px solid #1e2535;border-radius:10px;padding:16px;">'
                f'<div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;'
                f'color:#4a5568;font-family:\'Syne\',sans-serif;margin-bottom:12px;">Top Complexity</div>'
                f'{bars}</div>'
            )

    with hcol2:
        if mods:
            top5loc = sorted(mods, key=lambda m: m["loc"], reverse=True)[:5]
            bars = "".join(render_hbar(m["module"].split("/")[-1], float(m["loc"]), 600.0, COLORS["accent_primary"])
                           for m in top5loc)
            st.html(
                f'<div style="background:#141820;border:1px solid #1e2535;border-radius:10px;padding:16px;">'
                f'<div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;'
                f'color:#4a5568;font-family:\'Syne\',sans-serif;margin-bottom:12px;">Largest Files (LOC)</div>'
                f'{bars}</div>'
            )

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Module metrics table (HTML → .table-wrap .data-table) ──
    st.markdown('<div class="section-title" style="margin-bottom:10px;">Module Details</div>',
                unsafe_allow_html=True)

    rows = "".join(
        f"<tr>"
        f"<td>{m['module']}</td>"
        f"<td>{m['loc']}</td>"
        f"<td>{m['complexity']}</td>"
        f"<td>{m['functions']}</td>"
        f"<td>{m['classes']}</td>"
        f"<td>{m['dependencies']}</td>"
        f"<td>{render_badge(m['risk'])}</td>"
        f"</tr>"
        for m in mods
    )

    st.html(
        f'<div style="background:var(--bg-card);border:1px solid var(--border);'
        f'border-radius:var(--radius-md);overflow:hidden;">'
        f'<table class="data-table"><thead><tr>'
        f'<th>Module</th><th>LOC</th><th>Complexity</th>'
        f'<th>Functions</th><th>Classes</th><th>Dependencies</th><th>Risk</th>'
        f'</tr></thead><tbody>{rows}</tbody></table></div>'
    )


# ── PAGE: GRAPH ──────────────────────────────────────────────────────────────

def render_graph(data: dict, config: dict):
    """
    HTML → #page-graph with PyVis integration.
    Tries to load live PyVis HTML from graph_builder output;
    falls back to inline SVG demo matching prototype.
    Integration: graph_builder.py → graph_components.py generate_pyvis_html()
    """
    st.markdown('<div class="page-title">Dependency Graph</div>', unsafe_allow_html=True)

    # ── Graph filter chips (HTML → .graph-controls .chip) ──
    filter_col, _ = st.columns([6, 4])
    with filter_col:
        graph_filter = st.radio(
            "Filter",
            ["All Modules", "Critical Path", "Circular Deps", "Hub Modules"],
            horizontal=True,
            key="graph_filter",
            label_visibility="collapsed",
        )

    # ── Try loading live PyVis output ──
    graph_html_path = data.get("graph_data_path")
    pyvis_loaded = False

    if graph_html_path and Path(graph_html_path).exists():
        try:
            # Try to import and use graph_components
            try:
                import sys
                sys.path.insert(0, str(Path(__file__).parent))
                from graph_components import render_pyvis_graph
                render_pyvis_graph(graph_html_path)
                pyvis_loaded = True
            except ImportError:
                # Fallback: render the HTML directly in an iframe
                with open(graph_html_path) as f:
                    graph_html = f.read()
                st.iframe(graph_html, height=420)
                pyvis_loaded = True
        except Exception as e:
            st.warning(f"Graph render error: {e}")

    if not pyvis_loaded:
        # ── Inline SVG demo (matches prototype canvas) ──
        svg_demo = """
        <div style="background:var(--bg-card);border:1px solid var(--border);
             border-radius:var(--radius-md);padding:0;overflow:hidden;height:400px;position:relative;">
          <svg width="100%" height="100%" viewBox="0 0 800 400" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <radialGradient id="g-orch" cx="40%" cy="35%">
                <stop offset="0%" stop-color="#f54b6a" stop-opacity="0.8"/>
                <stop offset="100%" stop-color="#f54b6a" stop-opacity="0.3"/>
              </radialGradient>
              <radialGradient id="g-graph" cx="40%" cy="35%">
                <stop offset="0%" stop-color="#f5a623" stop-opacity="0.8"/>
                <stop offset="100%" stop-color="#f5a623" stop-opacity="0.3"/>
              </radialGradient>
              <radialGradient id="g-schema" cx="40%" cy="35%">
                <stop offset="0%" stop-color="#7c5cfc" stop-opacity="0.8"/>
                <stop offset="100%" stop-color="#7c5cfc" stop-opacity="0.3"/>
              </radialGradient>
              <radialGradient id="g-util" cx="40%" cy="35%">
                <stop offset="0%" stop-color="#00d4aa" stop-opacity="0.8"/>
                <stop offset="100%" stop-color="#00d4aa" stop-opacity="0.3"/>
              </radialGradient>
            </defs>
            <!-- Edges -->
            <line x1="400" y1="200" x2="600" y2="120" stroke="#1e2535" stroke-width="1" stroke-opacity="0.5"/>
            <line x1="400" y1="200" x2="200" y2="120" stroke="#1e2535" stroke-width="1" stroke-opacity="0.5"/>
            <line x1="400" y1="200" x2="520" y2="280" stroke="#1e2535" stroke-width="1" stroke-opacity="0.5"/>
            <line x1="400" y1="200" x2="640" y2="180" stroke="#1e2535" stroke-width="1" stroke-opacity="0.5"/>
            <line x1="400" y1="200" x2="400" y2="328" stroke="#1e2535" stroke-width="1" stroke-opacity="0.5"/>
            <!-- Circular dep (dashed red) -->
            <line x1="400" y1="200" x2="600" y2="120" stroke="#f54b6a" stroke-width="1.5" stroke-opacity="0.7" stroke-dasharray="4 3"/>
            <line x1="600" y1="120" x2="400" y2="200" stroke="#f54b6a" stroke-width="1.5" stroke-opacity="0.7" stroke-dasharray="4 3"/>
            <!-- Nodes -->
            <circle cx="400" cy="200" r="22" fill="#f54b6a" fill-opacity="0.08"/>
            <circle cx="400" cy="200" r="18" fill="url(#g-orch)" stroke="#f54b6a" stroke-width="1.5"/>
            <text x="400" y="227" text-anchor="middle" fill="#8892a4" font-size="9" font-family="DM Mono, monospace">orchestrator</text>

            <circle cx="600" cy="120" r="18" fill="#f5a623" fill-opacity="0.08"/>
            <circle cx="600" cy="120" r="14" fill="url(#g-graph)" stroke="#f5a623" stroke-width="1.5"/>
            <text x="600" y="144" text-anchor="middle" fill="#8892a4" font-size="9" font-family="DM Mono, monospace">graph_builder</text>

            <circle cx="200" cy="120" r="16" fill="#7c5cfc" fill-opacity="0.08"/>
            <circle cx="200" cy="120" r="13" fill="url(#g-schema)" stroke="#7c5cfc" stroke-width="1.5"/>
            <text x="200" y="142" text-anchor="middle" fill="#8892a4" font-size="9" font-family="DM Mono, monospace">schemas</text>

            <circle cx="160" cy="240" r="15" fill="#7c5cfc" fill-opacity="0.08"/>
            <circle cx="160" cy="240" r="12" fill="url(#g-schema)" stroke="#7c5cfc" stroke-width="1.5"/>
            <text x="160" y="261" text-anchor="middle" fill="#8892a4" font-size="9" font-family="DM Mono, monospace">py_parser</text>

            <circle cx="520" cy="280" r="15" fill="#00d4aa" fill-opacity="0.08"/>
            <circle cx="520" cy="280" r="12" fill="url(#g-util)" stroke="#00d4aa" stroke-width="1.5"/>
            <text x="520" y="301" text-anchor="middle" fill="#8892a4" font-size="9" font-family="DM Mono, monospace">heuristics</text>

            <circle cx="640" cy="180" r="14" fill="#00d4aa" fill-opacity="0.08"/>
            <circle cx="640" cy="180" r="11" fill="url(#g-util)" stroke="#00d4aa" stroke-width="1.5"/>
            <text x="640" y="200" text-anchor="middle" fill="#8892a4" font-size="9" font-family="DM Mono, monospace">report</text>

            <circle cx="400" cy="328" r="13" fill="#00d4aa" fill-opacity="0.08"/>
            <circle cx="400" cy="328" r="10" fill="url(#g-util)" stroke="#00d4aa" stroke-width="1.5"/>
            <text x="400" y="348" text-anchor="middle" fill="#8892a4" font-size="9" font-family="DM Mono, monospace">cli</text>

            <circle cx="720" cy="80" r="11" fill="#6b7280" fill-opacity="0.08"/>
            <circle cx="720" cy="80" r="8" fill="#6b7280" fill-opacity="0.5" stroke="#6b7280" stroke-width="1"/>
            <text x="720" y="100" text-anchor="middle" fill="#8892a4" font-size="9" font-family="DM Mono, monospace">claude</text>

            <circle cx="730" cy="160" r="10" fill="#6b7280" fill-opacity="0.08"/>
            <circle cx="730" cy="160" r="7" fill="#6b7280" fill-opacity="0.5" stroke="#6b7280" stroke-width="1"/>
            <text x="730" y="178" text-anchor="middle" fill="#8892a4" font-size="9" font-family="DM Mono, monospace">openai</text>
          </svg>
          <div style="position:absolute;top:10px;right:12px;
               background:rgba(245,75,106,0.1);border:1px solid rgba(245,75,106,0.3);
               border-radius:6px;padding:4px 10px;font-family:'DM Mono',monospace;
               font-size:10px;color:#f54b6a;">⚠ 2 circular deps</div>
        </div>
        """
        st.markdown(svg_demo, unsafe_allow_html=True)

    # ── Legend (HTML → .graph-legend) ──
    st.markdown("""
    <div class="graph-legend">
      <span style="font-size:10px;text-transform:uppercase;letter-spacing:.06em;color:var(--text-muted);margin-right:8px;">Legend</span>
      <span class="legend-item"><span class="legend-dot" style="background:#f54b6a;"></span>Critical</span>
      <span class="legend-item"><span class="legend-dot" style="background:#f5a623;"></span>High</span>
      <span class="legend-item"><span class="legend-dot" style="background:#7c5cfc;"></span>Core</span>
      <span class="legend-item"><span class="legend-dot" style="background:#00d4aa;"></span>Utility</span>
      <span class="legend-item"><span class="legend-dot" style="background:#6b7280;"></span>Leaf</span>
      <span class="legend-item">
        <svg width="20" height="8"><line x1="0" y1="4" x2="20" y2="4" stroke="#f54b6a" stroke-width="1.5" stroke-dasharray="4 3"/></svg>
        Circular Dep
      </span>
    </div>
    """, unsafe_allow_html=True)


# ── PAGE: FILES ──────────────────────────────────────────────────────────────

def render_files(data: dict):
    st.markdown('<div class="page-title">File Explorer</div>', unsafe_allow_html=True)

    metrics = data.get("metrics", {})

    # ── File stat cards (HTML → .files-stats-row) ──
    c1, c2, c3, c4 = st.columns(4)
    stats = [
        (str(metrics.get("total_files", 28)), "Python Files"),
        (f"{metrics.get('total_loc', 3240):,}", "Total Lines"),
        (str(metrics.get("yaml_configs", 4)), "YAML Configs"),
        (f"{metrics.get('test_cases', 90)}+", "Test Cases"),
    ]
    for col, (val, label) in zip([c1, c2, c3, c4], stats):
        with col:
            st.markdown(
                f'<div class="file-stat-card">'
                f'<div class="fsc-val">{val}</div>'
                f'<div class="fsc-label">{label}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Module list table (simplified file tree) ──
    st.markdown('<div class="section-title" style="margin-bottom:10px;">Module Inventory</div>',
                unsafe_allow_html=True)

    mods = data.get("module_metrics", [])
    rows = "".join(
        f"<tr>"
        f"<td>🐍 {m['module']}</td>"
        f"<td>{m['loc']} LOC</td>"
        f"<td>{render_badge(m['risk'])}</td>"
        f"</tr>"
        for m in mods
    )

    st.markdown(
        f'<div style="background:var(--bg-card);border:1px solid var(--border);'
        f'border-radius:var(--radius-md);overflow:hidden;">'
        f'<table class="data-table"><thead><tr>'
        f'<th>Module</th><th>Size</th><th>Risk</th>'
        f'</tr></thead><tbody>{rows}</tbody></table></div>',
        unsafe_allow_html=True,
    )


# ── PAGE: FINDINGS ───────────────────────────────────────────────────────────

def render_findings(data: dict):
    st.markdown('<div class="page-title">Findings</div>', unsafe_allow_html=True)

    findings = data.get("findings", [])
    summary = data.get("findings_summary", {})

    # ── Summary chips (HTML → .finding-count-chip) ──
    chips_html = f"""
    <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:16px;">
      <span class="finding-count-chip fcc-critical">⬡ {summary.get('critical', 0)} Critical</span>
      <span class="finding-count-chip fcc-high">⬡ {summary.get('high', 0)} High</span>
      <span class="finding-count-chip fcc-medium">⬡ {summary.get('medium', 0)} Medium</span>
      <span class="finding-count-chip fcc-low">⬡ {summary.get('low', 0)} Low</span>
      <span class="finding-count-chip fcc-total">∑ {summary.get('total', 0)} Total</span>
    </div>
    <style>
      .finding-count-chip {{
        display:inline-flex;align-items:center;gap:6px;
        padding:6px 14px;border-radius:20px;font-size:12px;font-weight:600;
        border:1px solid;cursor:pointer;transition:all 0.15s;
        font-family:var(--font-mono);
      }}
      .fcc-critical{{border-color:var(--critical);color:var(--critical);background:rgba(245,75,106,0.06);}}
      .fcc-high    {{border-color:var(--high);color:var(--high);background:rgba(245,166,35,0.06);}}
      .fcc-medium  {{border-color:var(--medium);color:var(--medium);background:rgba(124,92,252,0.06);}}
      .fcc-low     {{border-color:var(--low);color:var(--low);background:rgba(0,212,170,0.06);}}
      .fcc-total   {{border-color:var(--border);color:var(--text-secondary);background:var(--bg-card);}}
    </style>
    """
    st.markdown(chips_html, unsafe_allow_html=True)

    # ── Findings accordion (HTML → .acc-item) ──
    # Using st.expander per finding; styled via CSS overrides
    for finding in findings:
        sev = finding["severity"]
        sev_color = SEV_COLOR.get(sev, COLORS["text_muted"])
        verified_color = COLORS["accent_secondary"] if finding.get("verified") else COLORS["text_muted"]
        verified_label = "True ✓" if finding.get("verified") else "False"

        header_label = (
            f"{'🔴' if sev=='CRITICAL' else '🟠' if sev=='HIGH' else '🟣' if sev=='MEDIUM' else '🟢'} "
            f"[{finding['id']}] {finding['title']}"
        )

        with st.expander(header_label):
            detail_html = f"""
            <div class="acc-body">
              <div class="acc-details-grid">
                <div class="acc-detail-group">
                  <div class="acc-detail-key">Finding ID</div>
                  <div class="acc-detail-val">{finding['id']}</div>
                </div>
                <div class="acc-detail-group">
                  <div class="acc-detail-key">Layer</div>
                  <div class="acc-detail-val">{finding['layer']}</div>
                </div>
                <div class="acc-detail-group">
                  <div class="acc-detail-key">Severity</div>
                  <div class="acc-detail-val" style="color:{sev_color}">{sev}</div>
                </div>
                <div class="acc-detail-group">
                  <div class="acc-detail-key">Verified</div>
                  <div class="acc-detail-val" style="color:{verified_color}">{verified_label}</div>
                </div>
                <div class="acc-detail-group">
                  <div class="acc-detail-key">File</div>
                  <div class="acc-detail-val">{finding['file']}</div>
                </div>
                <div class="acc-detail-group">
                  <div class="acc-detail-key">Line</div>
                  <div class="acc-detail-val">{finding['line']}</div>
                </div>
              </div>
              <div class="acc-rationale">{finding['rationale']}</div>
            </div>
            """
            st.markdown(detail_html, unsafe_allow_html=True)


# ── PAGE: ABOUT ──────────────────────────────────────────────────────────────

def render_about():
    st.markdown("""
    <div class="about-hero">
      <div class="about-hero-title">Arcnical</div>
      <div class="about-hero-tag">⬡ Architecture Needs Intelligence · v0.2.0</div>
      <div class="about-hero-desc">
        An AI-powered GitHub repository analyzer that detects architectural issues,
        security vulnerabilities, and code quality problems across L1–L4 analysis layers.
        Built with Python 3.11+, tree-sitter parsers, networkx knowledge graphs,
        and multi-LLM provider support (Claude / OpenAI / Gemini).
      </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        stack_items = [
            "Python 3.11+ · uv package manager",
            "tree-sitter (Python + TypeScript parsers)",
            "networkx (knowledge graph)",
            "Pydantic v2 (schema validation)",
            "Typer + Rich (CLI)",
            "Streamlit + PyVis (dashboard)",
            "Anthropic / OpenAI / Gemini SDKs",
            "Jinja2 (report templates)",
        ]
        items_html = "".join(
            f'<div class="stack-item"><span class="stack-dot"></span>{item}</div>'
            for item in stack_items
        )
        st.markdown(
            f'<div style="background:var(--bg-card);border:1px solid var(--border);'
            f'border-radius:var(--radius-md);padding:20px;">'
            f'<div style="font-family:var(--font-display);font-size:13px;font-weight:700;'
            f'color:var(--text-primary);margin-bottom:14px;">⬡ Tech Stack</div>'
            f'<style>.stack-dot{{width:5px;height:5px;border-radius:50%;background:var(--accent-primary);'
            f'flex-shrink:0;display:inline-block;margin-right:8px;}}</style>'
            f'{items_html}</div>',
            unsafe_allow_html=True,
        )

    with col2:
        team_cards = [
            ("A", "Engineer A", "Backend · Qualification → Review Agent",
             "linear-gradient(135deg,#7c5cfc,#a78bfa)"),
            ("B", "Engineer B", "Surface · CLI · Streamlit · Evaluation",
             "linear-gradient(135deg,#00d4aa,#34d399)"),
        ]
        cards_html = "".join(
            f'<div style="display:flex;align-items:center;gap:12px;padding:10px;'
            f'background:#0f1218;border-radius:6px;border:1px solid #151c28;margin-bottom:8px;">'
            f'<div style="width:36px;height:36px;border-radius:50%;display:flex;align-items:center;'
            f'justify-content:center;font-family:\'Syne\',sans-serif;font-size:13px;font-weight:700;'
            f'color:white;flex-shrink:0;background:{bg};">{init}</div>'
            f'<div>'
            f'<div style="font-size:12.5px;font-weight:600;color:#e8eaf2;">{name}</div>'
            f'<div style="font-size:11px;color:#4a5568;font-family:\'DM Mono\',monospace;">{role}</div>'
            f'</div></div>'
            for init, name, role, bg in team_cards
        )

        st.markdown(
            f'<div style="background:#141820;border:1px solid #1e2535;border-radius:10px;padding:20px;margin-bottom:12px;">'
            f'<div style="font-family:\'Syne\',sans-serif;font-size:13px;font-weight:700;'
            f'color:#e8eaf2;margin-bottom:14px;">⬡ Team</div>'
            f'{cards_html}'
            f'</div>',
            unsafe_allow_html=True,
        )

        # ── Analysis Layers — separate card ──
        analysis_layers = [
            ("L1", "Qualification", COLORS["accent_primary"]),
            ("L2", "Heuristics",    COLORS["accent_amber"]),
            ("L3", "Security",      COLORS["accent_rose"]),
            ("L4", "LLM Review",    COLORS["accent_secondary"]),
        ]
        layers_html = "".join(
            f'<div style="display:flex;align-items:center;gap:10px;padding:8px 0;'
            f'border-bottom:1px solid #151c28;font-size:12px;color:#8892a4;">'
            f'<span style="font-family:\'DM Mono\',monospace;color:{c};font-weight:600;'
            f'min-width:28px;">{l}</span>'
            f'<span style="width:1px;height:14px;background:#1e2535;flex-shrink:0;"></span>'
            f'<span style="color:#e8eaf2;">{n}</span>'
            f'</div>'
            for l, n, c in analysis_layers
        )
        # Remove border-bottom from last item via wrapper
        st.markdown(
            f'<div style="background:#141820;border:1px solid #1e2535;border-radius:10px;padding:20px;">'
            f'<div style="font-family:\'Syne\',sans-serif;font-size:13px;font-weight:700;'
            f'color:#e8eaf2;margin-bottom:12px;">⬡ Analysis Layers</div>'
            f'{layers_html}'
            f'<div style="padding-top:8px;font-size:11px;color:#4a5568;font-family:\'DM Mono\',monospace;">'
            f'L1 → L2 → L3 → L4 pipeline</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── Project Stats card — full width below the two columns ──
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    stat_items = [
        ("⬡", "Sessions",      "8 sessions · 7-day sprint",       COLORS["accent_primary"]),
        ("⬡", "Codebase",      "3,000+ lines of code",             COLORS["accent_secondary"]),
        ("⬡", "Tests",         "90+ tests · 74.8% coverage",       COLORS["accent_amber"]),
        ("⬡", "Modules",       "28 Python modules · 4 YAML configs", COLORS["accent_primary"]),
        ("⬡", "Requirements",  "73 requirements mapped (RTM)",      COLORS["medium"]),
        ("⬡", "Delivery",      "15 April 2026 · On Track ✓",        COLORS["accent_secondary"]),
    ]

    stat_cells = "".join(
        f'<div style="background:#0f1218;border:1px solid #1e2535;border-radius:8px;'
        f'padding:14px 16px;">'
        f'<div style="font-size:9px;text-transform:uppercase;letter-spacing:0.1em;'
        f'color:#4a5568;font-family:\'Syne\',sans-serif;font-weight:700;margin-bottom:6px;">{key}</div>'
        f'<div style="font-size:12px;color:#e8eaf2;font-family:\'DM Mono\',monospace;'
        f'line-height:1.5;border-left:2px solid {color};padding-left:8px;">{val}</div>'
        f'</div>'
        for _, key, val, color in stat_items
    )

    st.markdown(
        f'<div style="background:#141820;border:1px solid #1e2535;border-radius:10px;padding:20px;">'
        f'<div style="font-family:\'Syne\',sans-serif;font-size:13px;font-weight:700;'
        f'color:#e8eaf2;margin-bottom:16px;">⬡ Project Stats</div>'
        f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;">'
        f'{stat_cells}'
        f'</div>'
        f'<div style="margin-top:14px;padding:10px 14px;background:rgba(0,212,170,0.06);'
        f'border:1px solid rgba(0,212,170,0.2);border-radius:6px;display:flex;align-items:center;gap:8px;">'
        f'<span style="color:#00d4aa;font-size:14px;">✓</span>'
        f'<span style="font-family:\'DM Mono\',monospace;font-size:11.5px;color:#00d4aa;font-weight:600;">'
        f'Session #8 Phase 5 — Testing &amp; polish · v0.2.0 release · 15 April 2026</span>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── CLI / RUN SECTION ─────────────────────────────────────────────────────────

def render_cli_section(data: dict, config: dict):
    """
    HTML → footer (.footer-tabs CLI/GUI) mapped to st.expander at bottom.
    Integration: cli_bridge.py for actual command construction.
    """
    try:
        from cli_bridge import build_cli_command
        cmd = build_cli_command(
            repo_path=config.get("repo_path", ""),
            provider=config.get("provider", "claude"),
            model=config.get("model", "claude-sonnet-4-6"),
            depth=config.get("depth", "standard"),
        )
    except ImportError:
        # Fallback CLI command construction
        repo = config.get("repo_path", "owner/repo")
        prov = config.get("provider", "claude")
        model = config.get("model", "claude-sonnet-4-6")
        depth = config.get("depth", "standard")
        cmd = f"arcnical analyze {repo} --llm-provider {prov} --llm-model {model} --depth {depth} --output json"

    with st.expander("⬡ CLI & Run Configuration", expanded=False):
        c1, c2 = st.columns([7, 3])
        with c1:
            st.markdown(render_cli_block(cmd, "Generated CLI Command"), unsafe_allow_html=True)
            st.code(cmd, language="bash")
        with c2:
            st.markdown(
                f'<div class="config-panel">'
                f'<div class="panel-label">Export Options</div>'
                f'<div class="config-row"><span class="config-key">Format</span>'
                f'<span class="config-val">JSON · Markdown · PDF</span></div>'
                f'<div class="config-row"><span class="config-key">Output Dir</span>'
                f'<span class="config-val">./reports/</span></div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            st.button("⬇ Export JSON", use_container_width=True)


# ── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    # ── Inject global CSS ──
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

    # ── Session state ──
    if "analysis_data" not in st.session_state:
        st.session_state.analysis_data = None
    if "last_run" not in st.session_state:
        st.session_state.last_run = None

    # ── Load data ──
    # Priority: session state → JSON export path → demo data
    json_paths = [
        "reports/analysis_output.json",
        "output/analysis_output.json",
        "analysis_output.json",
    ]
    data = None
    for p in json_paths:
        if Path(p).exists():
            data = load_analysis_data(p)
            break
    if data is None:
        data = load_analysis_data()  # demo data

    if st.session_state.analysis_data:
        data = st.session_state.analysis_data

    # ── Render sidebar (returns config dict) ──
    config = render_sidebar(data)

    # ── Handle re-run ──
    if config["run_clicked"]:
        repo = config["repo_path"].strip()
        if not repo:
            st.error("⚠ Please enter a repository path.")
        else:
            with st.spinner("Running analysis…"):
                try:
                    from orchestrator import run_analysis
                    result = run_analysis(
                        repo_path=repo,
                        llm_provider=config["provider"],
                        llm_model=config["model"],
                        depth=config["depth"],
                    )
                    st.session_state.analysis_data = result
                    data = result
                    st.success("✓ Analysis complete.")
                except ImportError:
                    # Orchestrator not available in demo mode
                    st.info("Demo mode: orchestrator.py not found. Showing sample data.")

    # ── Header bar (logo + export row above tabs) ──
    header_left, header_right = st.columns([8, 2])
    with header_left:
        st.markdown(
            f'<div style="padding:4px 0 12px 0;">'
            f'<span style="font-family:var(--font-mono);font-size:11px;color:var(--text-muted);">'
            f'arcnical / </span>'
            f'<span style="font-family:var(--font-mono);font-size:11px;color:var(--accent-secondary);">'
            f'{data.get("repo_path","—")}</span>'
            f'<span style="font-family:var(--font-mono);font-size:11px;color:var(--text-muted);margin-left:12px;">'
            f'v0.2.0</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with header_right:
        st.button("⬇ Export", use_container_width=True)

    # ── Navigation tabs (HTML → <nav> .nav-tab) ──
    tabs = st.tabs(["Overview", "Graph", "Metrics", "Files", "Findings", "About"])

    with tabs[0]:
        render_overview(data)

    with tabs[1]:
        render_graph(data, config)

    with tabs[2]:
        render_metrics(data)

    with tabs[3]:
        render_files(data)

    with tabs[4]:
        render_findings(data)

    with tabs[5]:
        render_about()

    # ── CLI section (HTML → footer) ──
    st.markdown("<hr>", unsafe_allow_html=True)
    render_cli_section(data, config)


if __name__ == "__main__":
    main()
