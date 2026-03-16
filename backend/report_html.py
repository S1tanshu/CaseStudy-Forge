# backend/report_html.py
from jinja2 import Environment, FileSystemLoader
import json
import os
 
 
def build_html(report_plan: dict, charts: list, output_path: str, template_dir: str):
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template('report.html.j2')
 
    # Prepare sections with embedded Plotly JSON
    sections = []
    chart_iter = iter(charts)
    for section in report_plan.get('sections', []):
        chart_data = next(chart_iter, None)
        sections.append({
            'title': section.get('section_title', ''),
            'narrative': section.get('narrative', ''),
            'plotly_json': chart_data.get('plotly_json') if chart_data else None,
            'chart_title': chart_data.get('title', '') if chart_data else '',
            'caption': chart_data.get('insight_caption', '') if chart_data else '',
            'callout_label': section.get('callout', {}).get('label', ''),
            'callout_text': section.get('callout', {}).get('text', ''),
        })
 
    html = template.render(
        report_title=report_plan.get('report_title', 'Business Report'),
        executive_summary=report_plan.get('executive_summary', ''),
        sections=sections,
        conclusion=report_plan.get('conclusion', ''),
    )
 
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    return output_path
