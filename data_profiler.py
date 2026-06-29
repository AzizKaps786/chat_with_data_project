import pandas as pd
import numpy as np


class DataProfiler:
    def __init__(self, df: pd.DataFrame):
        self.df = df

    def _python_value(self, value):
        if pd.isna(value):
            return None
        if isinstance(value, (np.integer,)):
            return int(value)
        if isinstance(value, (np.floating,)):
            return float(value)
        if isinstance(value, (pd.Timestamp,)):
            return str(value)
        return value

    def profile(self) -> dict:
        profile = {
            "shape": {"rows": int(len(self.df)), "columns": int(len(self.df.columns))},
            "columns": {},
            "sample_data": self.df.head(5).to_string(index=False),
            "missing_values": {str(k): int(v) for k, v in self.df.isnull().sum().to_dict().items()},
        }

        for col in self.df.columns:
            series = self.df[col]
            col_info = {
                "type": str(series.dtype),
                "null_count": int(series.isnull().sum()),
            }

            if pd.api.types.is_numeric_dtype(series):
                clean = series.dropna()
                col_info.update({
                    "category": "numeric",
                    "min": float(clean.min()) if not clean.empty else None,
                    "max": float(clean.max()) if not clean.empty else None,
                    "mean": float(clean.mean()) if not clean.empty else None,
                })
            elif pd.api.types.is_datetime64_any_dtype(series):
                clean = series.dropna()
                col_info.update({
                    "category": "datetime",
                    "range": f"{clean.min()} to {clean.max()}" if not clean.empty else "No valid dates",
                })
            else:
                top_values = series.astype(str).value_counts(dropna=True).head(5).to_dict()
                col_info.update({
                    "category": "categorical",
                    "unique_values": int(series.nunique(dropna=True)),
                    "top_values": {str(k): int(v) for k, v in top_values.items()},
                })

            profile["columns"][str(col)] = col_info

        return profile

    def get_summary_string(self) -> str:
        profile = self.profile()
        lines = [
            f"Dataset Shape: {profile['shape']['rows']} rows, {profile['shape']['columns']} columns",
            "",
            "Columns:",
        ]
        for col, info in profile["columns"].items():
            line = f"- {col} ({info['category']})"
            if info["category"] == "numeric":
                line += f": min={info['min']}, max={info['max']}, mean={info['mean']}"
            elif info["category"] == "categorical":
                line += f": {info['unique_values']} unique values"
            elif info["category"] == "datetime":
                line += f": {info['range']}"
            lines.append(line)
        lines.append("\nSample Data:\n" + profile["sample_data"])
        return "\n".join(lines)
