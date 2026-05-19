"""
database_setup.py
-----------------
Task 3: Store cleaned and analyzed review data in PostgreSQL.

Creates the schema and inserts all review data from reviews_analyzed.csv.

Usage:
    python scripts/database_setup.py
    python scripts/database_setup.py --csv data/raw/reviews_analyzed.csv --host localhost --port 5432

Prerequisites:
    pip install psycopg2-binary pandas
    PostgreSQL running with database 'bank_reviews' already created.
"""

import argparse
import logging
import os

import pandas as pd
import psycopg2
from psycopg2.extras import execute_batch

# ── logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ── defaults ───────────────────────────────────────────────────────────────────
DEFAULT_CSV    = os.path.join("data", "raw", "reviews_analyzed.csv")
DEFAULT_HOST   = "localhost"
DEFAULT_PORT   = 5432
DEFAULT_DBNAME = "bank_reviews"
DEFAULT_USER   = "postgres"       # default PostgreSQL superuser
DEFAULT_PASS   = "postgres"       # change to your actual password


# ── SQL definitions ────────────────────────────────────────────────────────────

CREATE_BANKS_TABLE = """
CREATE TABLE IF NOT EXISTS banks (
    bank_id   SERIAL PRIMARY KEY,
    bank_name VARCHAR(100) NOT NULL UNIQUE,
    app_name  VARCHAR(150)
);
"""

CREATE_REVIEWS_TABLE = """
CREATE TABLE IF NOT EXISTS reviews (
    review_id        VARCHAR(20)  PRIMARY KEY,
    bank_id          INTEGER      NOT NULL REFERENCES banks(bank_id),
    review_text      TEXT,
    rating           SMALLINT     CHECK (rating BETWEEN 1 AND 5),
    review_date      DATE,
    sentiment_label  VARCHAR(20),
    sentiment_score  FLOAT,
    identified_theme VARCHAR(100),
    source           VARCHAR(50)  DEFAULT 'Google Play'
);
"""

# Known app names for each bank
BANK_APP_NAMES = {
    "Commercial Bank of Ethiopia": "CBE Mobile Banking",
    "Bank of Abyssinia":           "Bank of Abyssinia Mobile",
    "Dashen Bank":                 "Dashen Bank Mobile",
}


# ── helpers ────────────────────────────────────────────────────────────────────

def get_connection(host, port, dbname, user, password):
    """Open and return a psycopg2 connection."""
    conn = psycopg2.connect(
        host=host,
        port=port,
        dbname=dbname,
        user=user,
        password=password,
    )
    logger.info(f"Connected to PostgreSQL → {dbname} on {host}:{port}")
    return conn


def create_schema(cursor):
    """Create banks and reviews tables if they don't exist."""
    cursor.execute(CREATE_BANKS_TABLE)
    logger.info("Table 'banks' ready.")
    cursor.execute(CREATE_REVIEWS_TABLE)
    logger.info("Table 'reviews' ready.")


def insert_banks(cursor, bank_names: list) -> dict:
    """
    Insert unique banks and return a dict mapping bank_name → bank_id.
    Uses INSERT ... ON CONFLICT DO NOTHING so re-runs are safe.
    """
    bank_id_map = {}
    for name in bank_names:
        app_name = BANK_APP_NAMES.get(name, name)
        cursor.execute(
            """
            INSERT INTO banks (bank_name, app_name)
            VALUES (%s, %s)
            ON CONFLICT (bank_name) DO NOTHING;
            """,
            (name, app_name),
        )
        cursor.execute("SELECT bank_id FROM banks WHERE bank_name = %s;", (name,))
        bank_id_map[name] = cursor.fetchone()[0]

    logger.info(f"Banks inserted/confirmed: {list(bank_id_map.keys())}")
    return bank_id_map


def insert_reviews(cursor, df: pd.DataFrame, bank_id_map: dict):
    """
    Bulk-insert all reviews using execute_batch for performance.
    Skips rows with duplicate review_id (ON CONFLICT DO NOTHING).
    """
    records = []
    for _, row in df.iterrows():
        records.append((
            str(row["review_id"]),
            bank_id_map[row["bank"]],
            str(row["review"]) if pd.notna(row["review"]) else None,
            int(row["rating"]),
            str(row["date"]) if pd.notna(row["date"]) else None,
            str(row["sentiment_label"]) if pd.notna(row.get("sentiment_label")) else None,
            float(row["sentiment_score"]) if pd.notna(row.get("sentiment_score")) else None,
            str(row["identified_theme"]) if pd.notna(row.get("identified_theme")) else None,
            str(row["source"]) if pd.notna(row["source"]) else "Google Play",
        ))

    execute_batch(
        cursor,
        """
        INSERT INTO reviews
            (review_id, bank_id, review_text, rating, review_date,
             sentiment_label, sentiment_score, identified_theme, source)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (review_id) DO NOTHING;
        """,
        records,
        page_size=500,
    )
    logger.info(f"Attempted insert of {len(records)} reviews.")


# ── verification queries ───────────────────────────────────────────────────────

def run_verification(cursor):
    """Run data-integrity checks and print a report."""
    logger.info("=" * 55)
    logger.info("VERIFICATION REPORT")
    logger.info("=" * 55)

    # 1. Total review count
    cursor.execute("SELECT COUNT(*) FROM reviews;")
    total = cursor.fetchone()[0]
    logger.info(f"  Total reviews in DB : {total}")

    # 2. Reviews per bank
    cursor.execute("""
        SELECT b.bank_name, COUNT(r.review_id) AS review_count
        FROM banks b
        LEFT JOIN reviews r ON b.bank_id = r.bank_id
        GROUP BY b.bank_name
        ORDER BY review_count DESC;
    """)
    logger.info("  Reviews per bank:")
    for row in cursor.fetchall():
        logger.info(f"    {row[0]:<40} {row[1]}")

    # 3. Average rating per bank
    cursor.execute("""
        SELECT b.bank_name, ROUND(AVG(r.rating)::numeric, 2) AS avg_rating
        FROM banks b
        JOIN reviews r ON b.bank_id = r.bank_id
        GROUP BY b.bank_name
        ORDER BY avg_rating DESC;
    """)
    logger.info("  Average rating per bank:")
    for row in cursor.fetchall():
        logger.info(f"    {row[0]:<40} {row[1]}")

    # 4. Null check on key columns
    cursor.execute("""
        SELECT
            SUM(CASE WHEN review_text     IS NULL THEN 1 ELSE 0 END) AS null_text,
            SUM(CASE WHEN rating          IS NULL THEN 1 ELSE 0 END) AS null_rating,
            SUM(CASE WHEN sentiment_label IS NULL THEN 1 ELSE 0 END) AS null_sentiment,
            SUM(CASE WHEN identified_theme IS NULL THEN 1 ELSE 0 END) AS null_theme
        FROM reviews;
    """)
    nulls = cursor.fetchone()
    logger.info(f"  Null counts → text:{nulls[0]}  rating:{nulls[1]}  sentiment:{nulls[2]}  theme:{nulls[3]}")

    # 5. Sentiment distribution
    cursor.execute("""
        SELECT sentiment_label, COUNT(*) AS cnt
        FROM reviews
        GROUP BY sentiment_label
        ORDER BY cnt DESC;
    """)
    logger.info("  Sentiment distribution:")
    for row in cursor.fetchall():
        logger.info(f"    {row[0]:<15} {row[1]}")

    logger.info("=" * 55)


# ── main pipeline ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Task 3: Load reviewed data into PostgreSQL bank_reviews database."
    )
    parser.add_argument("--csv",      default=DEFAULT_CSV,    help="Path to reviews_analyzed.csv")
    parser.add_argument("--host",     default=DEFAULT_HOST,   help="PostgreSQL host")
    parser.add_argument("--port",     default=DEFAULT_PORT,   type=int, help="PostgreSQL port")
    parser.add_argument("--dbname",   default=DEFAULT_DBNAME, help="Database name")
    parser.add_argument("--user",     default=DEFAULT_USER,   help="PostgreSQL username")
    parser.add_argument("--password", default=DEFAULT_PASS,   help="PostgreSQL password")
    args = parser.parse_args()

    # ── Load CSV ──────────────────────────────────────────────────────────────
    logger.info(f"Loading data from: {args.csv}")
    df = pd.read_csv(args.csv)
    logger.info(f"Loaded {len(df)} rows | columns: {df.columns.tolist()}")

    # ── Connect & run ─────────────────────────────────────────────────────────
    conn = get_connection(args.host, args.port, args.dbname, args.user, args.password)
    try:
        with conn:
            with conn.cursor() as cur:
                create_schema(cur)
                bank_id_map = insert_banks(cur, df["bank"].unique().tolist())
                insert_reviews(cur, df, bank_id_map)
                run_verification(cur)
        logger.info("All data committed successfully.")
    except Exception as e:
        logger.error(f"Error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()
        logger.info("Connection closed.")


if __name__ == "__main__":
    main()
