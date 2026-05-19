-- schema.sql
-- Task 3: PostgreSQL schema for bank_reviews database
-- Run this manually or let database_setup.py handle it automatically.
--
-- Usage:
--   psql -U postgres -d bank_reviews -f schema.sql

-- ── Banks table ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS banks (
    bank_id   SERIAL       PRIMARY KEY,
    bank_name VARCHAR(100) NOT NULL UNIQUE,
    app_name  VARCHAR(150)
);

-- ── Reviews table ─────────────────────────────────────────────────────────────
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

-- ── Useful indexes ────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_reviews_bank_id   ON reviews(bank_id);
CREATE INDEX IF NOT EXISTS idx_reviews_sentiment  ON reviews(sentiment_label);
CREATE INDEX IF NOT EXISTS idx_reviews_date       ON reviews(review_date);

-- ── Verification queries (run after insertion) ────────────────────────────────

-- Count reviews per bank
SELECT b.bank_name, COUNT(r.review_id) AS review_count
FROM banks b
LEFT JOIN reviews r ON b.bank_id = r.bank_id
GROUP BY b.bank_name
ORDER BY review_count DESC;

-- Average rating per bank
SELECT b.bank_name, ROUND(AVG(r.rating)::numeric, 2) AS avg_rating
FROM banks b
JOIN reviews r ON b.bank_id = r.bank_id
GROUP BY b.bank_name
ORDER BY avg_rating DESC;

-- Null check
SELECT
    SUM(CASE WHEN review_text      IS NULL THEN 1 ELSE 0 END) AS null_text,
    SUM(CASE WHEN rating           IS NULL THEN 1 ELSE 0 END) AS null_rating,
    SUM(CASE WHEN sentiment_label  IS NULL THEN 1 ELSE 0 END) AS null_sentiment,
    SUM(CASE WHEN identified_theme IS NULL THEN 1 ELSE 0 END) AS null_theme
FROM reviews;
