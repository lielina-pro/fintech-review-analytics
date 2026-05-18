"""
scraper.py
----------
Scrapes Google Play Store reviews for three Ethiopian bank apps.

Usage:
    python scripts/scraper.py
    python scripts/scraper.py --banks CBE BOA Dashen
    python scripts/scraper.py --target 600 --output data/raw/reviews_raw.csv
"""

import argparse
import logging
import os
import time

import pandas as pd
from google_play_scraper import Sort, reviews

# ── logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ── bank configuration ─────────────────────────────────────────────────────────
BANK_APPS = [
    {
        "bank": "Commercial Bank of Ethiopia",
        "app_id": "com.combanketh.mobilebanking",
        "app_name": "CBE Mobile",
        "short": "CBE",
    },
    {
        "bank": "Bank of Abyssinia",
        "app_id": "com.boa.boaMobileBanking",
        "app_name": "BOA Mobile",
        "short": "BOA",
    },
    {
        "bank": "Dashen Bank",
        "app_id": "com.dashen.dashensuperapp",
        "app_name": "Dashen Super App",
        "short": "Dashen",
    },
]

DEFAULT_TARGET  = 600      # reviews to scrape per bank (buffer for dedup losses)
DEFAULT_OUTPUT  = os.path.join("data", "raw", "reviews_raw.csv")
BATCH_SIZE      = 200      # max reviews per API call
BATCH_DELAY     = 2        # seconds between batches
BANK_DELAY      = 3        # seconds between banks
LANGUAGE        = "en"
COUNTRY         = "et"


# ── core functions ─────────────────────────────────────────────────────────────

def scrape_bank(app_id: str, bank_name: str, target: int = DEFAULT_TARGET) -> list[dict]:
    """
    Scrape Google Play Store reviews for a single bank app.

    Parameters
    ----------
    app_id    : Google Play package name
    bank_name : Human-readable bank name used for logging
    target    : Minimum number of reviews to collect

    Returns
    -------
    list of raw review dicts returned by google-play-scraper
    """
    all_reviews = []
    continuation_token = None
    batch_num = 0

    logger.info(f"Starting scrape — {bank_name} ({app_id})")

    while len(all_reviews) < target:
        try:
            batch_num += 1
            result, continuation_token = reviews(
                app_id,
                lang=LANGUAGE,
                country=COUNTRY,
                sort=Sort.NEWEST,
                count=BATCH_SIZE,
                continuation_token=continuation_token,
            )

            if not result:
                logger.warning(f"  No results returned for {bank_name} at batch {batch_num}")
                break

            all_reviews.extend(result)
            logger.info(
                f"  Batch {batch_num}: {len(result)} reviews | "
                f"Total: {len(all_reviews)}"
            )

            if continuation_token is None:
                logger.info(f"  No further pages for {bank_name}")
                break

            time.sleep(BATCH_DELAY)

        except Exception as exc:
            logger.error(f"  Error at batch {batch_num} for {bank_name}: {exc}")
            time.sleep(5)
            break

    logger.info(f"Finished {bank_name}: {len(all_reviews)} reviews collected")
    return all_reviews


def parse_to_dataframe(raw_data: dict, bank_configs: list[dict]) -> pd.DataFrame:
    """
    Convert raw review dicts into a flat pandas DataFrame.

    Parameters
    ----------
    raw_data     : {bank_name: [raw_review, ...]}
    bank_configs : original BANK_APPS list (for app_name lookup)

    Returns
    -------
    pd.DataFrame with standardised columns
    """
    app_name_map = {b["bank"]: b["app_name"] for b in bank_configs}
    frames = []

    for bank_name, review_list in raw_data.items():
        records = [
            {
                "review_id":  r.get("reviewId", ""),
                "review":     r.get("content", ""),
                "rating":     r.get("score"),
                "date":       r.get("at"),
                "bank":       bank_name,
                "app_name":   app_name_map.get(bank_name, ""),
                "source":     "Google Play",
                "thumbs_up":  r.get("thumbsUpCount", 0),
                "reply":      r.get("replyContent", ""),
            }
            for r in review_list
        ]
        frames.append(pd.DataFrame(records))
        logger.info(f"  Parsed {len(records)} records for {bank_name}")

    return pd.concat(frames, ignore_index=True)


def scrape_all(
    bank_shorts: list[str] | None = None,
    target: int = DEFAULT_TARGET,
    output_path: str = DEFAULT_OUTPUT,
) -> pd.DataFrame:
    """
    Scrape all (or selected) banks and save raw CSV.

    Parameters
    ----------
    bank_shorts  : list of short names to scrape, e.g. ['CBE', 'BOA'].
                   If None, all three banks are scraped.
    target       : reviews to collect per bank
    output_path  : path to write the raw CSV

    Returns
    -------
    pd.DataFrame of raw (unpre-processed) reviews
    """
    selected = BANK_APPS
    if bank_shorts:
        selected = [b for b in BANK_APPS if b["short"] in bank_shorts]
        if not selected:
            raise ValueError(
                f"No matching banks for {bank_shorts}. "
                f"Valid short names: {[b['short'] for b in BANK_APPS]}"
            )

    raw_data = {}
    for config in selected:
        raw = scrape_bank(config["app_id"], config["bank"], target)
        raw_data[config["bank"]] = raw
        time.sleep(BANK_DELAY)

    df = parse_to_dataframe(raw_data, BANK_APPS)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8")
    logger.info(f"Raw CSV saved → {output_path}  ({len(df)} rows)")

    return df


# ── CLI entrypoint ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Scrape Google Play Store reviews for Ethiopian bank apps."
    )
    parser.add_argument(
        "--banks",
        nargs="+",
        choices=["CBE", "BOA", "Dashen"],
        default=None,
        help="Banks to scrape (default: all three)",
    )
    parser.add_argument(
        "--target",
        type=int,
        default=DEFAULT_TARGET,
        help=f"Reviews to collect per bank (default: {DEFAULT_TARGET})",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=DEFAULT_OUTPUT,
        help=f"Output CSV path (default: {DEFAULT_OUTPUT})",
    )

    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("SCRAPING START")
    logger.info(f"  Banks  : {args.banks or 'all'}")
    logger.info(f"  Target : {args.target} reviews/bank")
    logger.info(f"  Output : {args.output}")
    logger.info("=" * 60)

    df = scrape_all(
        bank_shorts=args.banks,
        target=args.target,
        output_path=args.output,
    )

    print("\nScraping summary:")
    print(df["bank"].value_counts().to_string())
    print(f"\nTotal raw reviews : {len(df)}")
    print(f"Saved to          : {args.output}")


if __name__ == "__main__":
    main()
