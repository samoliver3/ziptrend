"""Pure data operations; importing this module never starts the dashboard."""
from pathlib import Path
import re
import numpy as np
import pandas as pd


def read_data(source, *, filename=None, sheet_name=0, delimiter=None):
    """Read a path or file object, preserving ZIP strings (including leading zeros)."""
    name = filename or getattr(source, "name", str(source))
    suffix = Path(name).suffix.lower()
    if hasattr(source, "seek"):
        source.seek(0)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(source, sheet_name=sheet_name, dtype=str)
    if suffix in {".csv", ".txt", ".tsv"}:
        return pd.read_csv(source, sep=delimiter or ("\t" if suffix == ".tsv" else None),
                           engine="python", dtype=str, encoding="utf-8-sig")
    if suffix in {".json", ".jsonl"}:
        return pd.read_json(source, lines=suffix == ".jsonl", dtype=False)
    raise ValueError("Supported files: CSV, TSV, delimited TXT, XLSX, XLS, JSON, JSONL.")


def normalize_zip(value):
    if pd.isna(value):
        return None
    value = str(value).strip()
    if re.fullmatch(r"\d{1,5}\.0+", value):
        value = value.split(".")[0]
    if re.fullmatch(r"\d{5}-\d{4}", value):
        value = value[:5]
    return value.zfill(5) if re.fullmatch(r"\d{1,5}", value) else None


def prepare_data(frame, *, zip_column, date_column, value_column, date_format=None,
                 duplicate="error"):
    """Return canonical zip/date/value rows. Invalid input raises, never silently drops.

    duplicate: error, sum, mean, or last for repeated ZIP/date pairs.
    Numeric dates must be converted to ISO dates first; four-digit years are accepted.
    """
    if frame.empty:
        raise ValueError("The file has no observations.")
    columns = [zip_column, date_column, value_column]
    if len(set(columns)) != 3 or any(c not in frame for c in columns):
        raise ValueError("Choose three distinct, existing ZIP, date, and value columns.")
    dates = frame[date_column].astype(str).str.strip()
    numeric_dates = dates.str.fullmatch(r"\d+(\.\d+)?") & ~dates.str.fullmatch(r"\d{4}")
    if numeric_dates.any() and not date_format:
        raise ValueError("Numeric dates require an explicit date format or conversion to ISO dates.")
    values = pd.to_numeric(frame[value_column].astype(str).str.replace(",", "", regex=False), errors="coerce")
    result = pd.DataFrame({"zip": frame[zip_column].map(normalize_zip),
                           "date": pd.to_datetime(dates, format=date_format or "mixed", errors="coerce", utc=True).dt.tz_localize(None).dt.normalize(),
                           "value": values})
    bad = result.isna().any(axis=1) | ~np.isfinite(result["value"])
    if bad.any():
        raise ValueError(f"{int(bad.sum())} invalid row(s): ZIP must be 5 digits, dates valid, and values finite numbers. Example row positions: {(np.flatnonzero(bad)[:5] + 1).tolist()}")
    if duplicate not in {"error", "sum", "mean", "last"}:
        raise ValueError("Unknown duplicate policy.")
    if result.duplicated(["zip", "date"]).any():
        if duplicate == "error":
            raise ValueError("Repeated ZIP/date pairs found. Choose how to combine duplicates.")
        result = result.groupby(["zip", "date"], as_index=False)["value"].agg(duplicate)
    return result.sort_values(["date", "zip"]).reset_index(drop=True)


def locate(data, lookup=None):
    """Attach ZIP centroids and states. Supply a lookup for offline/private usage.

    Lookup columns: zip, state, latitude, longitude. Missing ZIPs remain in output.
    Default pgeocode downloads GeoNames once, then uses its local cache.
    """
    if lookup is None:
        import pgeocode
        lookup = pgeocode.Nominatim("us").query_postal_code(data["zip"].unique().tolist())
        lookup = lookup.rename(columns={"postal_code": "zip", "state_code": "state"})
    lookup = lookup[["zip", "state", "latitude", "longitude"]].copy()
    lookup["zip"] = lookup["zip"].map(normalize_zip)
    lookup["state"] = lookup["state"].astype("string").str.strip().str.upper()
    if lookup["zip"].isna().any() or lookup["zip"].duplicated().any():
        raise ValueError("Geography lookup requires one valid row per ZIP.")
    for column, bound in [("latitude", 90), ("longitude", 180)]:
        lookup[column] = pd.to_numeric(lookup[column], errors="coerce")
        lookup.loc[~lookup[column].between(-bound, bound), column] = np.nan
    return data.merge(lookup, on="zip", how="left", validate="many_to_one")


def summarize(data, method="latest"):
    """Aggregate a filtered window per ZIP; latest uses each ZIP's last observation."""
    if method == "latest":
        return data.sort_values("date").groupby("zip", as_index=False).tail(1).reset_index(drop=True)
    if method not in {"sum", "mean"}:
        raise ValueError("Method must be latest, sum, or mean.")
    values = data.groupby("zip", as_index=False)["value"].agg(method)
    meta = data.sort_values("date").drop_duplicates("zip", keep="last").drop(columns="value")
    return values.merge(meta, on="zip", validate="one_to_one")


def trends(data, frequency="month", method="latest", group="zip"):
    """Aggregate within each ZIP/period first, then sum ZIPs for state trends.

    Missing observations are not forward-filled. State totals cover uploaded ZIPs only.
    """
    periods = {"day": "D", "month": "M", "year": "Y"}
    if frequency not in periods or group not in {"zip", "state"}:
        raise ValueError("Invalid frequency or grouping.")
    frame = data.copy()
    frame["period"] = frame["date"].dt.to_period(periods[frequency]).dt.to_timestamp()
    if method == "latest":
        rows = frame.sort_values("date").drop_duplicates(["zip", "period"], keep="last")
    elif method in {"sum", "mean"}:
        keys = ["zip", "period"] + (["state"] if "state" in frame else [])
        rows = frame.groupby(keys, as_index=False, dropna=False)["value"].agg(method)
    else:
        raise ValueError("Method must be latest, sum, or mean.")
    return rows.groupby([group, "period"], as_index=False)["value"].sum().sort_values("period")


def time_bins(data, frequency="month"):
    """Include empty intervals between observations so time never silently skips gaps."""
    code = {"day": "D", "month": "M", "year": "Y"}[frequency]
    return pd.period_range(data.date.min().to_period(code), data.date.max().to_period(code), freq=code).to_timestamp()


def period_snapshot(data, period, frequency="month", method="latest"):
    """Map only observations in the requested time bin; never carry values forward."""
    code = {"day": "D", "month": "M", "year": "Y"}[frequency]
    rows = data[data.date.dt.to_period(code) == pd.Timestamp(period).to_period(code)]
    return summarize(rows, method)
