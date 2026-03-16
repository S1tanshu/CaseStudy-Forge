# backend/csv_parser.py
import pandas as pd
import numpy as np
import json
from pathlib import Path
 
 
def profile_csv(filepath: str) -> dict:
    """
    Load a CSV and return a rich profile dict.
    This is what we feed to Gemini for analysis.
    """
    df = pd.read_csv(filepath)
 
    # Basic shape
    profile = {
        'filename': Path(filepath).name,
        'rows': len(df),
        'columns': len(df.columns),
        'column_names': df.columns.tolist(),
        'dtypes': {col: str(dtype) for col, dtype in df.dtypes.items()},
        'sample': df.head(5).to_dict(orient='records'),
        'nulls': df.isnull().sum().to_dict(),
    }
 
    # Numeric stats
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if numeric_cols:
        desc = df[numeric_cols].describe().to_dict()
        # Convert numpy types to Python native for JSON serialisation
        profile['numeric_stats'] = {
            col: {k: float(v) for k, v in stats.items()}
            for col, stats in desc.items()
        }
 
    # Categorical columns
    cat_cols = df.select_dtypes(include=['object']).columns.tolist()
    profile['categorical'] = {}
    for col in cat_cols[:10]:  # cap at 10 to limit prompt size
        vc = df[col].value_counts().head(10)
        profile['categorical'][col] = vc.to_dict()
 
    # Detect date columns
    date_cols = []
    for col in df.columns:
        if 'date' in col.lower() or 'time' in col.lower() or 'month' in col.lower() or 'year' in col.lower():
            date_cols.append(col)
    profile['likely_date_columns'] = date_cols
 
    return profile
 
 
def load_dataframe(filepath: str) -> pd.DataFrame:
    """Return the raw DataFrame for chart generation."""
    return pd.read_csv(filepath)
