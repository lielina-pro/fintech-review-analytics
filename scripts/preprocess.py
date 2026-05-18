"""
preprocess.py
-------------
Cleans and validates raw Google Play Store reviews produced by scraper.py.

Usage:
    python scripts/preprocess.py
    python scripts/preprocess.py --input data/raw/reviews_raw.csv --output data/raw/reviews_clean.csv
"""

import argparse
import logging
import os
import re
from datetime import datetime

import pandas as pd

# ── logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ── defaults ───────────────────────────────────────────────────────────────────
DEFAULT_INPUT  = os.path.join("data", "raw", "reviews_raw.csv")
DEFAULT_OUTPUT = os.path.join("data", "raw", "reviews_clean.csv")
REQUIRED_COLS  = ["review", "rating", "date", "bank", "source"]
MISSING_THRESHOLD = 5.0   # max acceptable missing-data percentage


# ── preprocessing functions ────────────────────────────────────────────────────

def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove duplicate reviews.

    Strategy:
      1. Drop exact duplicate review_ids (same submission).
      2. Drop rows with identical (review, bank) pairs (copy-pasted reviews).

    Parameters
    ----------
    df : raw DataFrame

    Returns
    -------
    pd.DataFrame with duplicates removed
    """
    before = len(df)

    if "review_id" in df.columns:
        df = df.drop_duplicates(subset="review_id", keep="first")

    df = df.drop_duplicates(subset=["review", "bank"], keep="first")

    removed = before - len(df)
    logger.info(f"Deduplication: removed {removed} rows | remaining {len(df)}")
    return df


def drop_missing(df: pd.DataFrame) -> pd.DataFrame:
    """
    Drop rows where review text or rating is missing or empty.

    Raises a warning if the missing rate exceeds MISSING_THRESHOLD.

    Parameters
    ----------
    df : DataFrame after deduplication

    Returns
    -------
    pd.DataFrame with missing rows removed
    """
    before = len(df)

    df = df.dropna(subset=["review", "rating"])
    df = df[df["review"].astype(str).str.strip() != ""]

    removed = before - len(df)
    rate = (removed / before * 100) if before else 0

    if rate > MISSING_THRESHOLD:
        logger.warning(
            f"Missing data rate {rate:.2f}% exceeds threshold of {MISSING_THRESHOLD}%"
        )
    else:
        logger.info(f"Missing values: dropped {removed} rows ({rate:.2f}%) — within threshold")

    return df


def normalize_dates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalise the date column to YYYY-MM-DD string format.

    Handles datetime objects, pandas Timestamps, and string representations.
    Rows with unparseable dates are set to None (not dropped).

    Parameters
    ----------
    df : DataFrame

    Returns
    -------
    pd.DataFrame with standardised date column
    """
    def _parse(val):
        if pd.isnull(val):
            return None
        try:
            if isinstance(val, (datetime, pd.Timestamp)):
                return val.strftime("%Y-%m-%d")
            return pd.to_datetime(str(val)).strftime("%Y-%m-%d")
        except Exception:
            return None

    df = df.copy()
    df["date"] = df["date"].apply(_parse)

    null_dates = df["date"].isnull().sum()
    if null_dates:
        logger.warning(f"Date normalization: {null_dates} dates could not be parsed (set to None)")
    else:
        logger.info("Date normalization complete — all dates in YYYY-MM-DD format")

    return df


def clean_text(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean review text.

    Steps:
      - Strip leading/trailing whitespace
      - Collapse multiple spaces into one
      - Remove non-printable characters
      - Drop reviews that become empty or too short (<3 characters) after cleaning

    Parameters
    ----------
    df : DataFrame

    Returns
    -------
    pd.DataFrame with cleaned review text
    """
    def _clean(text):
        if pd.isnull(text):
            return ""
        text = str(text).strip()
        text = " ".join(text.split())
        text = "".join(ch for ch in text if ch.isprintable())
        return text

    before = len(df)
    df = df.copy()
    df["review"] = df["review"].apply(_clean)
    df = df[df["review"].str.len() > 2]

    removed = before - len(df)
    logger.info(f"Text cleaning: removed {removed} reviews that became empty after cleaning")
    return df


def enforce_types(df: pd.DataFrame) -> pd.DataFrame:
    """
    Enforce correct data types.

      - rating → integer, clamped to 1–5
      - source → string, filled as 'Google Play' if missing

    Parameters
    ----------
    df : DataFrame

    Returns
    -------
    pd.DataFrame with enforced types
    """
    df = df.copy()
    df["rating"] = df["rating"].astype(int)
    df = df[df["rating"].between(1, 5)]

    if "source" in df.columns:
        df["source"] = df["source"].fillna("Google Play")
    else:
        df["source"] = "Google Play"

    logger.info(
        f"Type enforcement complete — "
        f"rating range: {df['rating'].min()}–{df['rating'].max()}"
    )
    return df


def validate(df: pd.DataFrame) -> bool:
    """
    Run all validation checks and print a report.

    Checks:
      1. Required columns present
      2. Total reviews >= 1200
      3. Per-bank count >= 400
      4. Missing data < 5%
      5. Date format YYYY-MM-DD
      6. Ratings in range 1–5
      7. Source column == 'Google Play'

    Parameters
    ----------
    df : final clean DataFrame

    Returns
    -------
    True if all checks pass, False otherwise
    """
    passed = True

    def check(condition, msg_ok, msg_fail):
        nonlocal passed
        if condition:
            logger.info(f"  ✅ {msg_ok}")
        else:
            logger.warning(f"  ⚠️  {msg_fail}")
            passed = False

    logger.info("=" * 55)
    logger.info("VALIDATION REPORT")
    logger.info("=" * 55)

    missing_cols = [c for c in REQUIRED_COLS if c not in df.columns]
    check(not missing_cols, "Required columns present",
          f"Missing columns: {missing_cols}")

    check(len(df) >= 1200,
          f"Total reviews: {len(df)} (target: 1,200+)",
          f"Total reviews: {len(df)} — below 1,200 target")

    for bank, count in df["bank"].value_counts().items():
        check(count >= 400,
              f"{bank}: {count} reviews (target: 400+)",
              f"{bank}: {count} reviews — below 400 target")

    total_cells = df[REQUIRED_COLS].size
    missing_cells = df[REQUIRED_COLS].isnull().sum().sum()
    rate = (missing_cells / total_cells * 100) if total_cells else 0
    check(rate < 5.0,
          f"Missing data: {rate:.2f}% (target: <5%)",
          f"Missing data: {rate:.2f}% — exceeds 5%")

    sample = df["date"].dropna().iloc[0] if not df["date"].dropna().empty else ""
    try:
        datetime.strptime(str(sample), "%Y-%m-%d")
        check(True, f"Date format YYYY-MM-DD (sample: {sample})", "")
    except ValueError:
        check(False, "", f"Date format issue: {sample}")

    check(df["rating"].between(1, 5).all(),
          "All ratings in range 1–5",
          "Some ratings outside range 1–5")

    check((df["source"] == "Google Play").all(),
          "Source column: 'Google Play'",
          "Source column has unexpected values")

    logger.info("=" * 55)
    return passed


# ── pipeline ───────────────────────────────────────────────────────────────────

def preprocess(
    input_path: str = DEFAULT_INPUT,
    output_path: str = DEFAULT_OUTPUT,
) -> pd.DataFrame:
    """
    Full preprocessing pipeline.

    Steps: load → deduplicate → drop missing → normalize dates
           → clean text → enforce types → validate → save

    Parameters
    ----------
    input_path  : path to raw CSV (output of scraper.py)
    output_path : path to write the clean CSV

    Returns
    -------
    pd.DataFrame of clean, validated reviews
    """
    logger.info(f"Loading raw data from: {input_path}")
    df = pd.read_csv(input_path)
    logger.info(f"Loaded {len(df)} rows")

    df = remove_duplicates(df)
    df = drop_missing(df)
    df = normalize_dates(df)
    df = clean_text(df)
    df = enforce_types(df)

    # Keep only the required 5 columns for the final output
    df_final = df[REQUIRED_COLS].copy().reset_index(drop=True)

    all_passed = validate(df_final)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df_final.to_csv(output_path, index=False, encoding="utf-8")
    logger.info(f"Clean CSV saved → {output_path}  ({len(df_final)} rows)")

    if not all_passed:
        logger.warning("One or more validation checks failed — review the report above.")

    return df_final


# ── CLI entrypoint ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Preprocess raw Google Play Store reviews."
    )
    parser.add_argument(
        "--input",
        type=str,
        default=DEFAULT_INPUT,
        help=f"Path to raw CSV (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=DEFAULT_OUTPUT,
        help=f"Path to write clean CSV (default: {DEFAULT_OUTPUT})",
    )

    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("PREPROCESSING START")
    logger.info(f"  Input  : {args.input}")
    logger.info(f"  Output : {args.output}")
    logger.info("=" * 60)

    df = preprocess(input_path=args.input, output_path=args.output)

    print("\nPreprocessing summary:")
    print(df["bank"].value_counts().to_string())
    print(f"\nTotal clean reviews : {len(df)}")
    print(f"Saved to            : {args.output}")


if __name__ == "__main__":
    main()
