# backend/chart_generator.py
import os
import json
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # non-interactive backend — MUST be before pyplot import
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
 
 
PALETTE = ['#2E75B6', '#70AD47', '#FF6F00', '#7B2D8B', '#C00000', '#00838F']
 
 
def make_chart(chart_spec: dict, df: pd.DataFrame, output_dir: str, idx: int) -> dict:
    """
    chart_spec keys: type, title, x_column, y_column, color_column, insight_caption
    Returns: {png_path, plotly_json, title, insight_caption}
    """
    chart_type = chart_spec.get('type', 'none')
    if chart_type == 'none':
        return None
 
    title = chart_spec.get('title', f'Chart {idx}')
    x_col = chart_spec.get('x_column')
    y_col = chart_spec.get('y_column')
    color_col = chart_spec.get('color_column')
    caption = chart_spec.get('insight_caption', '')
 
    # Validate columns exist
    valid_x = x_col if x_col and x_col in df.columns else None
    valid_y = y_col if y_col and y_col in df.columns else None
 
    os.makedirs(output_dir, exist_ok=True)
    png_path = os.path.join(output_dir, f'chart_{idx}.png')
 
    # ── Matplotlib (static PNG) ──────────────────────────────
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=150)
    fig.patch.set_facecolor('#FAFAFA')
    ax.set_facecolor('#FAFAFA')
 
    try:
        if chart_type == 'bar' and valid_x and valid_y:
            data = df.groupby(valid_x)[valid_y].sum().reset_index()
            ax.bar(data[valid_x].astype(str), data[valid_y], color=PALETTE[idx % len(PALETTE)])
            ax.set_xlabel(valid_x)
            ax.set_ylabel(valid_y)
 
        elif chart_type == 'line' and valid_x and valid_y:
            data = df.sort_values(valid_x)
            ax.plot(data[valid_x].astype(str), data[valid_y], color=PALETTE[idx % len(PALETTE)], linewidth=2, marker='o', markersize=4)
            ax.set_xlabel(valid_x)
            ax.set_ylabel(valid_y)
            plt.xticks(rotation=45, ha='right')
 
        elif chart_type == 'pie' and valid_x and valid_y:
            data = df.groupby(valid_x)[valid_y].sum().reset_index()
            ax.pie(data[valid_y], labels=data[valid_x].astype(str), autopct='%1.1f%%', colors=PALETTE)
 
        elif chart_type == 'scatter' and valid_x and valid_y:
            ax.scatter(df[valid_x], df[valid_y], color=PALETTE[0], alpha=0.7, s=40)
            ax.set_xlabel(valid_x)
            ax.set_ylabel(valid_y)
 
        else:  # fallback: just show column stats
            numeric_cols = df.select_dtypes('number').columns[:5]
            df[numeric_cols].mean().plot(kind='bar', ax=ax, color=PALETTE[:len(numeric_cols)])
            ax.set_ylabel('Mean Value')
 
        ax.set_title(title, fontsize=12, fontweight='bold', pad=10)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        plt.tight_layout()
        fig.savefig(png_path, bbox_inches='tight')
 
    finally:
        plt.close(fig)
 
    # ── Plotly (interactive JSON) ────────────────────────────
    plotly_json = _make_plotly(chart_type, df, valid_x, valid_y, color_col, title, idx)
 
    return {
        'title': title,
        'insight_caption': caption,
        'png_path': png_path,
        'plotly_json': plotly_json,
    }
 
 
def _make_plotly(chart_type, df, x_col, y_col, color_col, title, idx):
    template = 'plotly_white'
    color_seq = PALETTE
    try:
        if chart_type == 'bar' and x_col and y_col:
            fig = px.bar(df, x=x_col, y=y_col, color=color_col, title=title, template=template, color_discrete_sequence=color_seq)
        elif chart_type == 'line' and x_col and y_col:
            fig = px.line(df, x=x_col, y=y_col, color=color_col, title=title, template=template, markers=True, color_discrete_sequence=color_seq)
        elif chart_type == 'pie' and x_col and y_col:
            fig = px.pie(df, names=x_col, values=y_col, title=title, template=template, color_discrete_sequence=color_seq)
        elif chart_type == 'scatter' and x_col and y_col:
            fig = px.scatter(df, x=x_col, y=y_col, color=color_col, title=title, template=template, color_discrete_sequence=color_seq)
        else:
            numeric_cols = df.select_dtypes('number').columns[:5].tolist()
            means = df[numeric_cols].mean().reset_index()
            means.columns = ['Metric', 'Mean']
            fig = px.bar(means, x='Metric', y='Mean', title=title, template=template, color_discrete_sequence=color_seq)
 
        fig.update_layout(font_family='Arial', title_font_size=14, margin=dict(t=50, b=30, l=30, r=30))
        return fig.to_json()
    except Exception:
        return None
