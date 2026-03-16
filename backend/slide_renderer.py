# backend/slide_renderer.py
import asyncio
import os
import base64
import multiprocessing

# ── Color palettes ──────────────────────────────────────────────────────
PALETTES = {
    'midnight': {'bg': '#0A0E1A', 'accent': '#4F9CF9', 'text': '#FFFFFF', 'muted': 'rgba(255,255,255,0.65)'},
    'obsidian': {'bg': '#0D0D0D', 'accent': '#E8A838', 'text': '#FFFFFF', 'muted': 'rgba(255,255,255,0.65)'},
    'slate':    {'bg': '#0F1923', 'accent': '#3DD68C', 'text': '#FFFFFF', 'muted': 'rgba(255,255,255,0.65)'},
    'crimson':  {'bg': '#12080F', 'accent': '#F25C7A', 'text': '#FFFFFF', 'muted': 'rgba(255,255,255,0.65)'},
}

# ── HTML slide template ──────────────────────────────────────────────────
SLIDE_TEMPLATE = '''<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{
    width:1920px; height:1080px; overflow:hidden;
    background:{bg};
    font-family:'Inter','Helvetica Neue',sans-serif;
  }}
  .grid {{
    position:absolute; inset:0;
    background-image:
      linear-gradient(rgba(255,255,255,0.018) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255,255,255,0.018) 1px, transparent 1px);
    background-size:80px 80px;
  }}
  .accent-bar {{ position:absolute; left:0; top:0; width:6px; height:100%; background:{accent}; }}
  .content {{
    position:absolute; left:120px; top:100px;
    width:{content_width}px; height:880px;
    display:flex; flex-direction:column; justify-content:center;
  }}
  .eyebrow {{
    font-size:20px; font-weight:600; letter-spacing:0.2em;
    text-transform:uppercase; color:{accent}; margin-bottom:24px;
  }}
  .headline {{
    font-size:{headline_size}px; font-weight:700;
    color:{text}; line-height:1.12;
    max-width:1060px; margin-bottom:40px; letter-spacing:-0.025em;
  }}
  .body {{
    font-size:28px; font-weight:400;
    color:{muted}; line-height:1.7;
    max-width:880px; margin-bottom:48px;
  }}
  .callout {{
    display:inline-flex; align-items:flex-start; gap:20px;
    background:rgba(255,255,255,0.05);
    border:1px solid rgba(255,255,255,0.10);
    border-left:4px solid {accent};
    padding:24px 32px; border-radius:4px; max-width:840px;
  }}
  .callout-label {{
    font-size:16px; font-weight:700;
    letter-spacing:0.14em; text-transform:uppercase;
    color:{accent}; white-space:nowrap; padding-top:4px;
  }}
  .callout-text {{
    font-size:26px; font-weight:400;
    color:rgba(255,255,255,0.88); line-height:1.55;
  }}
  .chart-zone {{
    position:absolute; right:80px; top:120px;
    width:700px; height:740px;
  }}
  .chart-zone img {{ width:100%; height:100%; object-fit:contain; }}
  .slide-num {{
    position:absolute; bottom:48px; right:80px;
    font-size:18px; color:rgba(255,255,255,0.22); letter-spacing:0.1em;
  }}
  .brand {{
    position:absolute; bottom:44px; left:120px;
    font-size:18px; font-weight:600;
    color:rgba(255,255,255,0.28); letter-spacing:0.08em;
  }}
  .cover .headline {{ font-size:96px; max-width:1300px; }}
  .cover .body {{ font-size:34px; max-width:1100px; }}
</style></head><body>
<div class="grid"></div>
<div class="accent-bar"></div>
<div class="content {extra_class}">
  <div class="eyebrow">{eyebrow}</div>
  <div class="headline" style="font-size:{headline_size}px">{headline}</div>
  <div class="body">{body}</div>
  {callout_html}
</div>
{chart_html}
<div class="slide-num">{slide_num}</div>
<div class="brand">{brand}</div>
</body></html>'''


def _chart_html(png_path: str) -> str:
    if not png_path or not os.path.exists(png_path):
        return ''
    with open(png_path, 'rb') as f:
        b64 = base64.b64encode(f.read()).decode()
    return f'<div class="chart-zone"><img src="data:image/png;base64,{b64}"/></div>'


def build_cover_html(report_plan: dict, palette: dict) -> str:
    pal = palette
    return SLIDE_TEMPLATE.format(
        bg=pal['bg'], accent=pal['accent'], text=pal['text'], muted=pal['muted'],
        content_width=1680,
        extra_class='cover',
        eyebrow='EXECUTIVE BRIEFING',
        headline=report_plan.get('report_title', 'Business Report'),
        headline_size=88,
        body=report_plan.get('executive_summary', ''),
        callout_html='',
        chart_html='',
        slide_num='01',
        brand='CaseStudy Forge',
    )


def build_section_html(section: dict, chart_png: str,
                       slide_num: int, total: int, palette: dict) -> str:
    pal = palette
    headline = section.get('section_title', '')
    headline_size = 82 if len(headline) < 55 else 66 if len(headline) < 85 else 52

    has_chart = bool(chart_png and os.path.exists(chart_png))
    content_width = 1060 if has_chart else 1680

    callout = section.get('callout', {})
    callout_html = ''
    if callout.get('text'):
        callout_html = (
            f'<div class="callout">'
            f'<span class="callout-label">{callout.get("label", "KEY INSIGHT")}</span>'
            f'<span class="callout-text">{callout.get("text", "")}</span>'
            f'</div>'
        )

    return SLIDE_TEMPLATE.format(
        bg=pal['bg'], accent=pal['accent'], text=pal['text'], muted=pal['muted'],
        content_width=content_width,
        extra_class='',
        eyebrow=f'SECTION {slide_num} OF {total}',
        headline=headline,
        headline_size=headline_size,
        body=section.get('narrative', '')[:320],
        callout_html=callout_html,
        chart_html=_chart_html(chart_png),
        slide_num=f'{slide_num+1:02d} / {total+1:02d}',
        brand='CaseStudy Forge',
    )


def build_conclusion_html(report_plan: dict, palette: dict) -> str:
    pal = palette
    total = len(report_plan.get('sections', [])) + 2
    return SLIDE_TEMPLATE.format(
        bg=pal['bg'], accent=pal['accent'], text=pal['text'], muted=pal['muted'],
        content_width=1680,
        extra_class='',
        eyebrow='CONCLUSION',
        headline='What happens next.',
        headline_size=88,
        body=report_plan.get('conclusion', ''),
        callout_html='',
        chart_html='',
        slide_num=f'{total:02d} / {total:02d}',
        brand='CaseStudy Forge',
    )


# ── Playwright rendering (Windows-safe via separate process) ─────────────

def _playwright_worker(html: str, output_path: str, result_queue: multiprocessing.Queue):
    """
    Runs Playwright in a completely separate process.
    This avoids the Windows ProactorEventLoop NotImplementedError
    that occurs when Playwright tries to create subprocesses inside
    an existing asyncio event loop.
    """
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(args=['--no-sandbox'])
            page = browser.new_page(viewport={'width': 1920, 'height': 1080})
            page.set_content(html, wait_until='networkidle')
            page.screenshot(path=output_path, full_page=False)
            browser.close()
        result_queue.put(('ok', output_path))
    except Exception as e:
        result_queue.put(('error', str(e)))


async def render_slide_to_png(html: str, output_path: str) -> str:
    """
    Spawns a fresh process for each slide render.
    run_in_executor keeps FastAPI's event loop unblocked while waiting.
    """
    result_queue = multiprocessing.Queue()
    proc = multiprocessing.Process(
        target=_playwright_worker,
        args=(html, output_path, result_queue),
        daemon=True,
    )
    proc.start()

    # Wait for the process in a thread so we don't block the event loop
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, proc.join)

    if not result_queue.empty():
        status, value = result_queue.get()
        if status == 'error':
            raise RuntimeError(f"Playwright render failed: {value}")
    else:
        raise RuntimeError(f"Playwright worker exited with no result (exit code {proc.exitcode})")

    return output_path


async def render_all_slides(
    report_plan: dict,
    charts: list,
    out_dir: str,
    palette_name: str = 'midnight'
) -> list[str]:
    """
    Render cover + all content sections + conclusion to PNG files.
    Returns list of PNG file paths in slide order.
    """
    palette = PALETTES.get(palette_name, PALETTES['midnight'])
    os.makedirs(out_dir, exist_ok=True)
    slide_paths = []

    # Cover
    cover_html = build_cover_html(report_plan, palette)
    cover_path = os.path.join(out_dir, 'slide_00_cover.png')
    await render_slide_to_png(cover_html, cover_path)
    slide_paths.append(cover_path)

    # Content sections
    sections = report_plan.get('sections', [])
    for i, section in enumerate(sections):
        chart_data = charts[i] if i < len(charts) else None
        chart_png = chart_data['png_path'] if chart_data else None
        html = build_section_html(section, chart_png, i + 1, len(sections), palette)
        path = os.path.join(out_dir, f'slide_{i+1:02d}.png')
        await render_slide_to_png(html, path)
        slide_paths.append(path)

    # Conclusion
    conc_html = build_conclusion_html(report_plan, palette)
    conc_path = os.path.join(out_dir, 'slide_conclusion.png')
    await render_slide_to_png(conc_html, conc_path)
    slide_paths.append(conc_path)

    return slide_paths


# Required on Windows for multiprocessing to work correctly
if __name__ == '__main__':
    multiprocessing.freeze_support()