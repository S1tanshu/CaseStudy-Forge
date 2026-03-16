# backend/video_renderer.py  v3
# =============================================================================
# Cinematic renderer — Chart.js live animations + water theme + Playwright
#
# What changed from v2:
#   • PNG chart images REPLACED by Chart.js canvas — bars grow, pies draw,
#     lines trace, all animated at 1800ms with easing
#   • Animation durations slowed to 1.2–1.5s, travel distances doubled
#   • Plotly JSON -> Chart.js converter added (_plotly_to_chartjs)
#   • Water palette applied to Chart.js datasets (cyan / teal / green)
#   • --disable-gpu intentionally absent from Playwright args
#
# Pipeline:
#   report_plan + charts --> animated HTML (Chart.js canvases, no PNGs)
#                                |
#                        Playwright records .webm (~realtime, GPU-on)
#                                |
#   narration MP3s -------> ffmpeg adelay mux -> synced audio WAV
#                                |
#                        ffmpeg mux -> final .mp4
# =============================================================================

import asyncio
import base64
import json
import os
import re
import subprocess
from pathlib import Path


# Timing
SECTION_HOLD  = 7.0
SILENT_BUFFER = 1.2
TRANS_MS      = 900
INTRO_HOLD    = 5.0
OUTRO_HOLD    = 5.0

# Water palette for Chart.js
CHART_COLORS = [
    "rgba(0,212,255,0.85)",
    "rgba(72,202,228,0.85)",
    "rgba(82,183,136,0.85)",
    "rgba(0,150,199,0.85)",
    "rgba(144,224,239,0.85)",
    "rgba(2,62,138,0.85)",
]
CHART_BORDERS = [c.replace("0.85", "1") for c in CHART_COLORS]


# =============================================================================
# Public helper
# =============================================================================

def get_narration_for_slide(section: dict) -> str:
    return section.get("slide_narration") or section.get("narrative", "")


# =============================================================================
# Internal helpers
# =============================================================================

def _b64_image(png_path: str) -> str:
    if not png_path or not os.path.exists(png_path):
        return ""
    with open(png_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return f"data:image/png;base64,{b64}"


def _get_audio_duration(path: str) -> float:
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet",
             "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1",
             str(Path(path).resolve())],
            capture_output=True, text=True, timeout=15,
        )
        return float(r.stdout.strip())
    except Exception:
        return SECTION_HOLD


def _build_timing(narration_audios: list) -> list:
    timings = []
    for i, path in enumerate(narration_audios):
        base = INTRO_HOLD if i == 0 else OUTRO_HOLD if i == len(narration_audios) - 1 else SECTION_HOLD
        if path and os.path.exists(path):
            dur = _get_audio_duration(path)
            timings.append(round(max(base, dur + SILENT_BUFFER), 3))
        else:
            timings.append(base)
    return timings


def _extract_stat(text: str):
    m = re.search(r'\b(\d{1,4}(?:\.\d{1,2})?)\s*(%|x|X|K|M|B)?\b', text or "")
    if m:
        val, sfx = m.group(1), m.group(2) or ""
        if float(val) > 1:
            return val, sfx
    return None, None


# =============================================================================
# Plotly JSON -> Chart.js converter
# =============================================================================

def _plotly_to_chartjs(chart_data: dict):
    if not chart_data:
        return None
    plotly_json_str = chart_data.get("plotly_json")
    if not plotly_json_str:
        return None
    try:
        spec = json.loads(plotly_json_str) if isinstance(plotly_json_str, str) else plotly_json_str
    except Exception:
        return None

    data_traces = spec.get("data", [])
    if not data_traces:
        return None

    trace = data_traces[0]
    ptype = trace.get("type", "bar")
    title = chart_data.get("title", "")

    common_options = {
        "responsive": True,
        "maintainAspectRatio": False,
        "animation": {"duration": 1800, "easing": "easeOutQuart"},
        "plugins": {
            "legend": {
                "display": True,
                "labels": {"color": "rgba(255,255,255,0.75)", "font": {"size": 13}, "padding": 20},
            },
            "title": {
                "display": bool(title),
                "text": title,
                "color": "rgba(255,255,255,0.90)",
                "font": {"size": 16, "weight": "600"},
                "padding": {"bottom": 20},
            },
        },
        "scales": {},
    }

    xy_scales = {
        "x": {
            "ticks": {"color": "rgba(255,255,255,0.65)", "font": {"size": 12}},
            "grid":  {"color": "rgba(255,255,255,0.06)"},
        },
        "y": {
            "ticks": {"color": "rgba(255,255,255,0.65)", "font": {"size": 12}},
            "grid":  {"color": "rgba(255,255,255,0.08)"},
            "beginAtZero": True,
        },
    }

    if ptype == "bar":
        labels   = [str(v) for v in (trace.get("x") or [])]
        datasets = []
        for ti, t in enumerate(data_traces):
            datasets.append({
                "label":           t.get("name", f"Series {ti+1}"),
                "data":            [float(v) if v is not None else 0 for v in (t.get("y") or [])],
                "backgroundColor": CHART_COLORS[ti % len(CHART_COLORS)],
                "borderColor":     CHART_BORDERS[ti % len(CHART_BORDERS)],
                "borderWidth": 1, "borderRadius": 5, "borderSkipped": False,
            })
        options = {**common_options, "scales": xy_scales}
        return {"type": "bar", "data": {"labels": labels, "datasets": datasets}, "options": options}

    if ptype in ("scatter", "line") and "lines" in trace.get("mode", "lines"):
        labels   = [str(v) for v in (trace.get("x") or [])]
        datasets = []
        for ti, t in enumerate(data_traces):
            color = CHART_COLORS[ti % len(CHART_COLORS)]
            datasets.append({
                "label":               t.get("name", f"Series {ti+1}"),
                "data":                [float(v) if v is not None else 0 for v in (t.get("y") or [])],
                "borderColor":         CHART_BORDERS[ti % len(CHART_BORDERS)],
                "backgroundColor":     color.replace("0.85", "0.15"),
                "borderWidth": 3, "pointRadius": 5,
                "pointBackgroundColor": CHART_BORDERS[ti % len(CHART_BORDERS)],
                "tension": 0.4, "fill": True,
            })
        options = {**common_options, "scales": xy_scales}
        return {"type": "line", "data": {"labels": labels, "datasets": datasets}, "options": options}

    if ptype == "pie":
        labels = [str(v) for v in (trace.get("labels") or [])]
        values = [float(v) if v is not None else 0 for v in (trace.get("values") or [])]
        options = {**common_options}
        options.pop("scales", None)
        options["animation"] = {"animateRotate": True, "animateScale": True, "duration": 2000, "easing": "easeOutQuart"}
        return {
            "type": "doughnut",
            "data": {
                "labels": labels,
                "datasets": [{
                    "data":            values,
                    "backgroundColor": CHART_COLORS[:len(values)],
                    "borderColor":     [c.replace("0.85","0.3") for c in CHART_COLORS[:len(values)]],
                    "borderWidth": 2, "hoverOffset": 12,
                }],
            },
            "options": options,
        }

    if ptype == "scatter":
        x_vals = trace.get("x") or []
        y_vals = trace.get("y") or []
        pts    = [{"x": float(x), "y": float(y)} for x, y in zip(x_vals, y_vals)]
        options = {**common_options, "scales": xy_scales}
        return {
            "type": "scatter",
            "data": {"datasets": [{
                "label":            trace.get("name", "Data"),
                "data":             pts,
                "backgroundColor":  CHART_COLORS[0],
                "borderColor":      CHART_BORDERS[0],
                "pointRadius": 6, "pointHoverRadius": 9,
            }]},
            "options": options,
        }

    return None


# =============================================================================
# Chart block builder
# =============================================================================

def _build_chart_block(chart_data: dict, canvas_id: str):
    caption = (chart_data.get("insight_caption") or "") if chart_data else ""
    chartjs_config = _plotly_to_chartjs(chart_data)

    if chartjs_config:
        config_json = json.dumps(chartjs_config, ensure_ascii=False)
        html = f"""<div class="chart-zone anim-scale" style="--d:0.6s">
                <canvas id="{canvas_id}" class="chartjs-canvas"></canvas>
                <p class="chart-caption">{caption}</p>
            </div>"""
        js = f"""(function() {{
        var ctx = document.getElementById('{canvas_id}');
        if (!ctx) return;
        new Chart(ctx, {config_json});
    }})();"""
        return html, js

    # PNG fallback
    chart_png = chart_data.get("png_path") if chart_data else None
    b64 = _b64_image(chart_png)
    if b64:
        html = f"""<div class="chart-zone anim-scale" style="--d:0.6s">
                <div class="chart-shimmer"></div>
                <img src="{b64}" alt="{caption}" class="chart-img" />
                <p class="chart-caption">{caption}</p>
            </div>"""
        return html, ""

    return "", ""


# =============================================================================
# HTML builder
# =============================================================================

def _build_presentation_html(report_plan: dict, charts: list, timing: list) -> str:
    sections     = report_plan.get("sections", [])
    title        = report_plan.get("report_title", "Business Report")
    exec_sum     = report_plan.get("executive_summary", "")
    conclusion   = report_plan.get("conclusion", "")
    total_slides = 1 + len(sections) + 1
    timing_json  = json.dumps(timing)
    total_ms     = int(sum(timing) * 1000) + 10000

    section_slides_html = ""
    chartjs_inits       = ""

    for i, section in enumerate(sections):
        chart_data = charts[i] if i < len(charts) else None
        callout    = section.get("callout", {})
        sec_title  = section.get("section_title", f"Section {i+1}")
        narrative  = section.get("narrative", "")
        canvas_id  = f"chart-canvas-{i}"

        stat_val, stat_sfx = _extract_stat(sec_title + " " + narrative)

        chart_block_html, chart_js = _build_chart_block(chart_data, canvas_id)
        if chart_js:
            chartjs_inits += f"""
    chartInitFns["slide-{i+1}"] = function() {{
        {chart_js}
    }};"""

        callout_html = ""
        if callout.get("text"):
            callout_html = f"""<div class="callout anim-wipe" style="--d:0.85s">
                    <span class="callout-label">{callout.get("label","KEY INSIGHT")}</span>
                    <span class="callout-text">{callout.get("text","")}</span>
                </div>"""

        stat_html = ""
        if stat_val:
            stat_html = f"""<div class="stat-block anim-fade" style="--d:0.5s">
                    <span class="stat-num" data-target="{stat_val}" data-suffix="{stat_sfx}">0{stat_sfx}</span>
                </div>"""

        has_chart    = bool(chart_block_html)
        layout_class = "slide-layout slide-layout--split" if has_chart else "slide-layout"

        section_slides_html += f"""
    <div class="slide slide--below" id="slide-{i+1}" data-idx="{i+1}">
        <div class="slide-bg"><div class="orb orb-1"></div><div class="orb orb-2"></div><div class="orb orb-3"></div></div>
        <div class="{layout_class}">
            <div class="slide-content">
                <div class="eyebrow anim-fade" style="--d:0.05s">SECTION {i+1}&nbsp;/&nbsp;{len(sections)}</div>
                <h2 class="sec-title anim-up" style="--d:0.2s">{sec_title}</h2>
                {stat_html}
                <p class="narrative anim-fade" style="--d:0.5s">{narrative}</p>
                {callout_html}
            </div>
            {'<div class="slide-right">' + chart_block_html + '</div>' if has_chart else ''}
        </div>
        <div class="slide-num">{i+2:02d}&nbsp;/&nbsp;{total_slides:02d}</div>
        <div class="cyan-bar"></div>
    </div>"""

    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#020B18;--bg2:#041525;--cyan:#00D4FF;--cyan2:#48CAE4;
  --teal:#0096C7;--green:#52B788;--text:#FFFFFF;
  --muted:rgba(255,255,255,0.62);--subtle:rgba(255,255,255,0.20);
  --border:rgba(0,212,255,0.18);--trans-ms:""" + str(TRANS_MS) + """ms}
html,body{width:1920px;height:1080px;overflow:hidden;background:var(--bg);
  font-family:"Helvetica Neue",Helvetica,Arial,sans-serif;
  -webkit-font-smoothing:antialiased;color:var(--text)}
#stage{position:relative;width:1920px;height:1080px;overflow:hidden;background:var(--bg)}

.slide{position:absolute;inset:0;width:1920px;height:1080px;overflow:hidden;
  will-change:transform,opacity;
  transition:transform var(--trans-ms) cubic-bezier(0.16,1,0.3,1),
             opacity var(--trans-ms) cubic-bezier(0.16,1,0.3,1)}
.slide--below{transform:translateY(100%);opacity:0;z-index:1;pointer-events:none}
.slide--active{transform:translateY(0) scale(1);opacity:1;z-index:2;pointer-events:auto}
.slide--above{transform:translateY(-8%) scale(0.96);opacity:0;z-index:1;pointer-events:none}

.slide-bg{position:absolute;inset:0;overflow:hidden;z-index:0;
  background:radial-gradient(ellipse at 15% 85%,rgba(0,150,199,0.22) 0%,transparent 55%),
             radial-gradient(ellipse at 85% 15%,rgba(0,212,255,0.14) 0%,transparent 50%),
             linear-gradient(160deg,#020B18 0%,#031E36 50%,#020B18 100%)}
.slide-bg::after{content:'';position:absolute;inset:0;pointer-events:none;
  mix-blend-mode:overlay;opacity:0.28;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='250' height='250'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.82' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='250' height='250' filter='url(%23n)' opacity='0.07'/%3E%3C/svg%3E");
  background-size:250px 250px}

.orb{position:absolute;border-radius:50%;filter:blur(100px);
  animation:floatOrb 12s ease-in-out infinite;will-change:transform}
.orb-1{width:720px;height:720px;top:-200px;left:-150px;animation-duration:13s;
  background:radial-gradient(circle,rgba(0,212,255,0.20) 0%,transparent 70%)}
.orb-2{width:520px;height:520px;bottom:-120px;right:180px;animation-duration:10s;animation-delay:-5s;
  background:radial-gradient(circle,rgba(72,202,228,0.16) 0%,transparent 70%)}
.orb-3{width:420px;height:420px;top:35%;left:42%;animation-duration:11s;animation-delay:-8s;
  background:radial-gradient(circle,rgba(82,183,136,0.13) 0%,transparent 70%)}
@keyframes floatOrb{0%,100%{transform:translate(0,0) scale(1)}33%{transform:translate(35px,-45px) scale(1.06)}66%{transform:translate(-25px,28px) scale(0.96)}}

.cyan-bar{position:absolute;left:0;top:0;width:5px;height:100%;
  background:linear-gradient(180deg,transparent 0%,var(--cyan) 25%,var(--green) 75%,transparent 100%);
  opacity:0.85;z-index:10}

.slide-layout{position:relative;z-index:5;display:flex;align-items:center;
  height:100%;padding:80px 120px 80px 140px}
.slide-layout--split .slide-content{width:820px;flex-shrink:0}
.slide-layout--split .slide-right{flex:1;display:flex;align-items:center;justify-content:center;padding-left:70px}
.slide-content{max-width:1100px}

.cover-tag{font-size:13px;font-weight:700;letter-spacing:0.30em;text-transform:uppercase;color:var(--cyan);margin-bottom:30px}
.cover-title{font-size:86px;font-weight:900;line-height:1.05;letter-spacing:-0.03em;color:var(--text);max-width:1350px;margin-bottom:44px}
.cover-divider{width:90px;height:4px;background:linear-gradient(90deg,var(--cyan),var(--green));margin-bottom:44px;border-radius:2px}
.cover-sub{font-size:28px;font-weight:300;line-height:1.75;color:var(--muted);max-width:1000px;margin-bottom:56px}
.cover-brand{font-size:14px;letter-spacing:0.20em;text-transform:uppercase;color:var(--subtle)}

.ripple{position:absolute;border-radius:50%;border:1px solid rgba(0,212,255,0.12);
  animation:rippleExpand 7s ease-out infinite;pointer-events:none}
.ripple-1{width:400px;height:400px;bottom:-80px;right:320px;animation-delay:0s}
.ripple-2{width:720px;height:720px;bottom:-240px;right:140px;animation-delay:2.3s}
.ripple-3{width:1050px;height:1050px;bottom:-420px;right:-40px;animation-delay:4.6s}
@keyframes rippleExpand{0%{transform:scale(0.75);opacity:0.5}100%{transform:scale(1.35);opacity:0}}

.eyebrow{font-size:12px;font-weight:700;letter-spacing:0.32em;text-transform:uppercase;color:var(--cyan);margin-bottom:24px}
.sec-title{font-size:60px;font-weight:800;line-height:1.08;letter-spacing:-0.025em;color:var(--text);max-width:800px;margin-bottom:28px}
.narrative{font-size:23px;font-weight:300;line-height:1.78;color:var(--muted);max-width:760px;margin-bottom:32px}

.stat-block{margin-bottom:24px}
.stat-num{font-size:108px;font-weight:900;line-height:1;letter-spacing:-0.04em;
  background:linear-gradient(135deg,var(--cyan) 0%,var(--green) 100%);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;display:inline-block}

.callout{display:inline-flex;align-items:flex-start;gap:20px;
  background:rgba(0,212,255,0.06);border:1px solid var(--border);
  border-left:4px solid var(--cyan);padding:22px 30px;border-radius:0 8px 8px 0;max-width:760px}
.callout-label{font-size:11px;font-weight:800;letter-spacing:0.24em;text-transform:uppercase;
  color:var(--cyan);white-space:nowrap;padding-top:3px;flex-shrink:0}
.callout-text{font-size:21px;font-weight:400;line-height:1.58;color:rgba(255,255,255,0.88)}

.chart-zone{position:relative;width:100%;max-width:700px}
.chartjs-canvas{width:100% !important;height:480px !important;display:block}
.chart-img{width:100%;height:auto;display:block;border-radius:10px;
  box-shadow:0 0 60px rgba(0,212,255,0.10),0 20px 60px rgba(0,0,0,0.5)}
.chart-shimmer{position:absolute;inset:0;border-radius:10px;
  background:linear-gradient(105deg,transparent 40%,rgba(0,212,255,0.15) 50%,transparent 60%);
  background-size:200% 100%;animation:shimmer 2s ease-out 0.8s 1 forwards;z-index:2;pointer-events:none}
@keyframes shimmer{0%{background-position:200% 0;opacity:1}100%{background-position:-200% 0;opacity:0}}
.chart-caption{margin-top:14px;font-size:14px;font-style:italic;color:var(--subtle);text-align:center}

.conclusion-label{font-size:12px;font-weight:700;letter-spacing:0.32em;text-transform:uppercase;color:var(--cyan);margin-bottom:26px}
.conclusion-title{font-size:90px;font-weight:900;line-height:1.05;letter-spacing:-0.03em;
  background:linear-gradient(135deg,var(--text) 0%,var(--cyan2) 55%,var(--green) 100%);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
  margin-bottom:42px;max-width:1400px}
.conclusion-body{font-size:28px;font-weight:300;line-height:1.72;color:var(--muted);max-width:1000px}

.slide-num{position:absolute;bottom:44px;right:72px;font-size:13px;letter-spacing:0.14em;
  color:rgba(255,255,255,0.20);z-index:10}

#progress{position:fixed;bottom:0;left:0;height:3px;width:0%;
  background:linear-gradient(90deg,var(--cyan) 0%,var(--green) 60%,#90E0EF 100%);
  box-shadow:0 0 18px rgba(0,212,255,0.8),0 0 6px rgba(144,224,239,0.9);z-index:9999}

.anim-up,.anim-fade,.anim-scale,.anim-wipe{opacity:0;transition:none}
.slide--active .anim-up{animation:enterUp 1.3s cubic-bezier(0.16,1,0.3,1) var(--d,0s) forwards}
.slide--active .anim-fade{animation:enterFade 1.2s ease-out var(--d,0s) forwards}
.slide--active .anim-scale{animation:enterScale 1.4s cubic-bezier(0.16,1,0.3,1) var(--d,0s) forwards}
.slide--active .anim-wipe{animation:enterWipe 1.1s cubic-bezier(0.16,1,0.3,1) var(--d,0s) forwards}
@keyframes enterUp{from{opacity:0;transform:translateY(80px)}to{opacity:1;transform:translateY(0)}}
@keyframes enterFade{from{opacity:0}to{opacity:1}}
@keyframes enterScale{from{opacity:0;transform:scale(0.80)}to{opacity:1;transform:scale(1)}}
@keyframes enterWipe{from{opacity:0;transform:translateX(-60px)}to{opacity:1;transform:translateX(0)}}
.slide--active .cover-title{animation:enterUp 1.1s cubic-bezier(0.16,1,0.3,1) 0.25s forwards}
</style>
</head>
<body>
<div id="stage">

<div class="slide slide--active" id="slide-0">
    <div class="slide-bg">
        <div class="orb orb-1"></div>
        <div class="orb orb-2" style="background:radial-gradient(circle,rgba(82,183,136,0.18) 0%,transparent 70%)"></div>
        <div class="orb orb-3"></div>
        <div class="ripple ripple-1"></div><div class="ripple ripple-2"></div><div class="ripple ripple-3"></div>
    </div>
    <div class="slide-layout">
        <div class="slide-content">
            <div class="cover-tag anim-fade" style="--d:0.15s">EXECUTIVE BRIEFING</div>
            <h1 class="cover-title" style="opacity:0">""" + title + """</h1>
            <div class="cover-divider anim-scale" style="--d:0.75s"></div>
            <p class="cover-sub anim-fade" style="--d:0.9s">""" + exec_sum + """</p>
            <div class="cover-brand anim-fade" style="--d:1.3s">CaseStudy Forge &nbsp;&middot;&nbsp; AI-Generated Report</div>
        </div>
    </div>
    <div class="slide-num">01&nbsp;/&nbsp;""" + str(total_slides) + """</div>
    <div class="cyan-bar"></div>
</div>

""" + section_slides_html + """

<div class="slide slide--below" id="slide-""" + str(len(sections)+1) + """">
    <div class="slide-bg">
        <div class="orb orb-1" style="background:radial-gradient(circle,rgba(82,183,136,0.22) 0%,transparent 70%)"></div>
        <div class="orb orb-2"></div>
        <div class="orb orb-3" style="background:radial-gradient(circle,rgba(0,212,255,0.16) 0%,transparent 70%)"></div>
    </div>
    <div class="slide-layout">
        <div class="slide-content">
            <div class="conclusion-label anim-fade" style="--d:0.1s">CONCLUSION</div>
            <h2 class="conclusion-title anim-up" style="--d:0.25s">What happens next.</h2>
            <p class="conclusion-body anim-fade" style="--d:0.65s">""" + conclusion + """</p>
        </div>
    </div>
    <div class="slide-num">""" + str(total_slides) + """&nbsp;/&nbsp;""" + str(total_slides) + """</div>
    <div class="cyan-bar"></div>
</div>

</div>
<div id="progress"></div>

<script>
(function() {
    "use strict";
    var TIMING   = """ + timing_json + """;
    var TOTAL    = TIMING.length;
    var TRANS_MS = """ + str(TRANS_MS) + """;
    var TOTAL_MS = TIMING.reduce(function(a,b){return a+b;},0)*1000;
    var current  = 0, startTime = null;

    var chartInitFns = {}, chartInited = {};
    """ + chartjs_inits + """

    function initChartsForSlide(slideId) {
        if (chartInited[slideId]) return;
        chartInited[slideId] = true;
        if (chartInitFns[slideId]) setTimeout(function(){ chartInitFns[slideId](); }, 400);
    }

    function runCountUp(el) {
        var target=parseFloat(el.dataset.target), suffix=el.dataset.suffix||"";
        var isFloat=target!==Math.floor(target), dur=1600, start=performance.now();
        function tick(now) {
            var p=Math.min(1,(now-start)/dur), ep=p===1?1:1-Math.pow(2,-10*p), v=target*ep;
            el.textContent=(isFloat?v.toFixed(1):Math.floor(v))+suffix;
            if(p<1) requestAnimationFrame(tick);
        }
        requestAnimationFrame(tick);
    }

    function activateSlide(idx) {
        var slide=document.getElementById("slide-"+idx);
        if (!slide) return;
        slide.className="slide slide--active";
        initChartsForSlide("slide-"+idx);
        slide.querySelectorAll(".stat-num[data-target]").forEach(function(el){
            setTimeout(function(){ runCountUp(el); }, 600);
        });
    }

    function advance() {
        var next=current+1;
        if (next>=TOTAL){ window.__DONE__=true; return; }
        var currEl=document.getElementById("slide-"+current);
        var nextEl=document.getElementById("slide-"+next);
        nextEl.className="slide slide--below";
        void nextEl.offsetHeight;
        currEl.className="slide slide--above";
        activateSlide(next);
        current=next;
        setTimeout(advance, TIMING[current]*1000);
    }

    function tickProgress(ts) {
        if (!startTime) startTime=ts;
        var pct=Math.min(100,((ts-startTime)/TOTAL_MS)*100);
        document.getElementById("progress").style.width=pct.toFixed(2)+"%";
        if ((ts-startTime)<TOTAL_MS+3000) requestAnimationFrame(tickProgress);
    }

    for (var i=0;i<TOTAL;i++) {
        var el=document.getElementById("slide-"+i);
        if (el) el.className=(i===0)?"slide slide--active":"slide slide--below";
    }
    document.querySelectorAll("#slide-0 .stat-num[data-target]").forEach(function(el){
        setTimeout(function(){ runCountUp(el); }, 600);
    });
    requestAnimationFrame(tickProgress);
    setTimeout(advance, TIMING[0]*1000);
})();
</script>
</body>
</html>"""


# =============================================================================
# Playwright recorder
# =============================================================================

def _run_playwright_sync(html_path: str, tmp_dir: str, total_ms: int) -> str:
    loop = asyncio.ProactorEventLoop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_record_with_playwright(html_path, tmp_dir, total_ms))
    finally:
        loop.close()


async def _record_with_playwright(html_path: str, tmp_dir: str, total_ms: int) -> str:
    from playwright.async_api import async_playwright

    webm_dir = os.path.join(tmp_dir, "webm")
    os.makedirs(webm_dir, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(args=[
            "--no-sandbox", "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--force-device-scale-factor=1", "--hide-scrollbars",
            # --disable-gpu intentionally absent
        ])
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir=webm_dir,
            record_video_size={"width": 1920, "height": 1080},
            device_scale_factor=1,
        )
        page = await context.new_page()
        file_url = Path(html_path).resolve().as_uri()
        await page.goto(file_url, wait_until="networkidle", timeout=30000)

        hard_timeout_ms = total_ms + 25000
        elapsed_ms = 0
        while elapsed_ms < hard_timeout_ms:
            done = await page.evaluate("() => window.__DONE__ === true")
            if done:
                await asyncio.sleep(2.5)
                break
            await asyncio.sleep(0.5)
            elapsed_ms += 500

        await context.close()
        await browser.close()

    webm_files = sorted(Path(webm_dir).glob("*.webm"))
    if not webm_files:
        raise RuntimeError(f"Playwright produced no .webm in {webm_dir}")
    return str(webm_files[-1])


# =============================================================================
# Audio sync + mux
# =============================================================================

def _build_synced_audio(narration_audios: list, timing: list, output_path: str) -> str:
    start_ms, cumulative = [], 0.0
    for hold in timing:
        start_ms.append(int(cumulative * 1000))
        cumulative += hold

    valid = [
        (idx, str(Path(p).resolve()), start_ms[idx])
        for idx, p in enumerate(narration_audios)
        if p and os.path.exists(p)
    ]

    if not valid:
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", "anullsrc=r=44100:cl=stereo",
            "-t", str(sum(timing) + 3.0), output_path,
        ], check=True, capture_output=True)
        return output_path

    cmd = ["ffmpeg", "-y"]
    for _, path, _ in valid:
        cmd += ["-i", path]

    filter_parts, mix_labels = [], []
    for seq_idx, (_, _, delay) in enumerate(valid):
        lbl = f"a{seq_idx}"
        filter_parts.append(f"[{seq_idx}:a]adelay={delay}|{delay}[{lbl}]")
        mix_labels.append(f"[{lbl}]")

    n = len(valid)
    filter_complex = (
        ";".join(filter_parts) + ";"
        + "".join(mix_labels)
        + f"amix=inputs={n}:duration=longest:dropout_transition=3[out]"
    )
    cmd += ["-filter_complex", filter_complex, "-map", "[out]",
            "-ac", "2", "-ar", "44100",
            str(Path(output_path).resolve())]
    subprocess.run(cmd, check=True, capture_output=True)
    return output_path


def _mux_video_audio(webm_path: str, audio_path: str, output_mp4: str) -> str:
    subprocess.run([
        "ffmpeg", "-y",
        "-i", str(Path(webm_path).resolve()),
        "-i", str(Path(audio_path).resolve()),
        "-vf", "fps=60,minterpolate=fps=60:mi_mode=mci:mc_mode=obmc",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-shortest", "-movflags", "+faststart",
        str(Path(output_mp4).resolve()),
    ], check=True, capture_output=True)
    return output_mp4


# =============================================================================
# Orchestrator + public API
# =============================================================================

async def _async_render(report_plan, charts, narration_audios, output_path):
    out_dir = os.path.dirname(os.path.abspath(output_path))
    tmp_dir = os.path.join(out_dir, "_video_tmp")
    os.makedirs(tmp_dir, exist_ok=True)

    print("=== VIDEO A/D: calculating slide timing ===", flush=True)
    timing   = _build_timing(narration_audios)
    total_s  = round(sum(timing), 1)
    total_ms = int(total_s * 1000) + 10000
    print(f"    {len(timing)} slides | {total_s}s total", flush=True)

    print("=== VIDEO B/D: building animated HTML ===", flush=True)
    html_content = _build_presentation_html(report_plan, charts, timing)
    html_path    = os.path.join(tmp_dir, "_presentation.html")
    with open(html_path, "w", encoding="utf-8") as fh:
        fh.write(html_content)

    print("=== VIDEO C/D: recording with Playwright (~realtime) ===", flush=True)
    loop = asyncio.get_event_loop()
    webm_path = await loop.run_in_executor(
        None, _run_playwright_sync, html_path, tmp_dir, total_ms
    )
    print(f"    Recorded -> {webm_path}", flush=True)

    print("=== VIDEO D/D: syncing audio + muxing to MP4 ===", flush=True)
    audio_path = os.path.join(tmp_dir, "narration_synced.wav")
    _build_synced_audio(narration_audios, timing, audio_path)
    _mux_video_audio(webm_path, audio_path, output_path)
    print(f"=== VIDEO COMPLETE: {output_path} ===", flush=True)
    return output_path


async def render_cinematic_video(
    report_plan, charts, narration_audios, output_path,
    slide_images=None, bg_music_path=None, fps=30,
    transition_duration=0.4, silent_buffer=0.5,
) -> str:
    await _async_render(report_plan, charts, narration_audios, output_path)
    return output_path