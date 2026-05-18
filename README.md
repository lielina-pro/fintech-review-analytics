# fintech-review-analytics

> **10 Academy — KAIM9 Week 2 Challenge**  
> Customer Experience Analytics for Ethiopian Fintech Apps

A rigorous end-to-end analytics pipeline that transforms raw Google Play Store reviews into actionable product insights for three Ethiopian banks: **Commercial Bank of Ethiopia (CBE)**, **Bank of Abyssinia (BOA)**, and **Dashen Bank**.

---

## Table of Contents

- [Project Overview](#project-overview)
- [Project Structure](#project-structure)
- [Setup & Installation](#setup--installation)
- [Task 1 — Data Collection & Preprocessing](#task-1--data-collection--preprocessing)
- [Task 2 — Sentiment & Thematic Analysis](#task-2--sentiment--thematic-analysis)
- [Task 3 — PostgreSQL Database](#task-3--postgresql-database)
- [Task 4 — Insights & Visualizations](#task-4--insights--visualizations)
- [CI/CD](#cicd)
- [Limitations](#limitations)
- [Author](#author)

---

## Project Overview

Mobile banking adoption in Ethiopia is accelerating, and user reviews on the Google Play Store represent one of the richest unfiltered signals of product quality available to bank product teams. This project builds a systematic pipeline to:

1. **Scrape** 1,200+ reviews from the Play Store for three Ethiopian bank apps
2. **Classify** review sentiment using DistilBERT and VADER
3. **Extract** recurring themes using TF-IDF keyword analysis
4. **Store** the processed data in a relational PostgreSQL database
5. **Synthesize** findings into visualizations and bank-specific recommendations

---

## Project Structure

```
fintech-review-analytics/
├── .github/
│   └── workflows/
│       └── unittests.yml          # CI/CD: runs pytest on every push to main
├── .gitignore
├── requirements.txt
├── README.md
├── data/
│   └── raw/                       # CSVs saved here (gitignored)
│       ├── reviews_clean.csv      # Output of Task 1
│       └── reviews_analyzed.csv   # Output of Task 2
├── notebooks/
│   ├── __init__.py
│   ├── README.md
│   ├── task1_scraping.ipynb       # Data collection & preprocessing
│   ├── task2_sentiment.ipynb      # Sentiment & thematic analysis
│   ├── task3_database.ipynb       # PostgreSQL schema & data insertion
│   └── task4_insights.ipynb       # Visualizations & recommendations
├── scripts/
│   ├── __init__.py
│   ├── README.md
│   └── schema.sql                 # PostgreSQL schema definition
├── src/
│   └── __init__.py
└── tests/
    ├── __init__.py
    └── test_placeholder.py        # Placeholder test for CI/CD
```

---

## Setup & Installation

### Prerequisites

- Python 3.9+
- PostgreSQL (for Task 3)
- Git

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/fintech-review-analytics.git
cd fintech-review-analytics

# 2. Install dependencies
pip install -r requirements.txt

# 3. Download spaCy language model
python -m spacy download en_core_web_sm
```

### requirements.txt

```
google-play-scraper
pandas
transformers
torch
vaderSentiment
spacy
scikit-learn
psycopg2-binary
sqlalchemy
matplotlib
seaborn
jupyter
pytest
```

---

## Task 1 — Data Collection & Preprocessing

**Notebook:** `notebooks/task1_scraping.ipynb`  
**Output:** `data/raw/reviews_clean.csv`

### App IDs

| Bank | App ID | App Name |
|------|--------|----------|
| Commercial Bank of Ethiopia | `com.combanketh.mobilebanking` | CBE Mobile |
| Bank of Abyssinia | `com.boa.boaMobileBanking` | BOA Mobile |
| Dashen Bank | `com.dashen.dashensuperapp` | Dashen Super App |

> **Note:** The initial Dashen Bank app ID (`com.dashen.dashensmart`) returned zero results. The correct ID (`com.dashen.dashensuperapp`) was identified using the Play Store search API.

### Scraping Methodology

- **Library:** `google-play-scraper` — interfaces with the Play Store's internal API
- **Sort order:** Newest first (`Sort.NEWEST`) to capture the most recent user feedback
- **Pagination:** Continuation tokens used to collect reviews across multiple batches
- **Language/Country:** `en` / `et` (Ethiopia)
- **Rate limiting:** 2-second delay between batches, 3-second delay between banks
- **Target:** 600 reviews scraped per bank to ensure 400+ remain after preprocessing

### Preprocessing Steps

1. **Deduplication** — removed duplicates by `review_id` and by identical `(review, bank)` pairs
2. **Missing values** — dropped rows with missing `review` text or `rating`; counts documented
3. **Date normalization** — all dates converted to `YYYY-MM-DD` format
4. **Text cleaning** — stripped whitespace, collapsed multiple spaces, removed non-printable characters
5. **Type enforcement** — `rating` cast to integer and validated in range 1–5

### Results

| Bank | Reviews Collected | Clean Reviews |
|------|------------------|---------------|
| Commercial Bank of Ethiopia | 600 | 448 |
| Bank of Abyssinia | 600 | 490 |
| Dashen Bank | 600 | 491 |
| **Total** | **1,800** | **1,429** |

- Missing data rate: **0.00%** (target: <5% ✅)
- Date format: **YYYY-MM-DD** ✅
- All ratings in range **1–5** ✅

### Output CSV Columns

| Column | Description |
|--------|-------------|
| `review` | Raw review text |
| `rating` | Star rating (1–5) |
| `date` | Review date (YYYY-MM-DD) |
| `bank` | Bank name |
| `source` | Always "Google Play" |

---

## Task 2 — Sentiment & Thematic Analysis

**Notebook:** `notebooks/task2_sentiment.ipynb`  
**Output:** `data/raw/reviews_analyzed.csv`

### Sentiment Analysis

**Primary model:** `distilbert-base-uncased-finetuned-sst-2-english`  
A transformer model fine-tuned on the Stanford Sentiment Treebank (SST-2), producing POSITIVE/NEGATIVE labels with a confidence score.

**Secondary tool:** VADER (Valence Aware Dictionary and sEntiment Reasoner)  
A lexicon-based tool that produces a compound score from -1 to +1, used to detect NEUTRAL reviews (compound between -0.05 and +0.05).

**Final labeling logic:**
- If VADER compound is between -0.05 and +0.05 → label is `neutral`
- Otherwise → use DistilBERT label (`positive` or `negative`)

**Why DistilBERT over VADER alone:**  
VADER misclassifies nuanced reviews (e.g., "transfers work but login always fails" gets a mixed signal). DistilBERT captures contextual meaning more accurately for longer Play Store reviews.

### Thematic Analysis

**Method:** TF-IDF (Term Frequency-Inverse Document Frequency) with unigrams and bigrams (`ngram_range=(1,2)`, `min_df=3`, `max_df=0.85`)

**Themes defined:**

| Theme | Description | Example Keywords |
|-------|-------------|-----------------|
| Account Access Issues | Login, OTP, authentication problems | login, otp, password, fingerprint, session |
| Transaction Performance | Transfer speed and reliability | transfer, slow, payment, pending, failed |
| App Stability & UI | Crashes, bugs, interface quality | crash, error, update, loading, freeze |
| Customer Support | Service quality and responsiveness | support, helpline, agent, response, complaint |
| Feature Requests | Desired new features | fingerprint, dark mode, amharic, notification |

**Theme assignment:** Keyword matching — the theme with the highest keyword hit count in a review is assigned. Falls back to `General Feedback` if no keywords match.

### Output CSV Columns

| Column | Description |
|--------|-------------|
| `review_id` | Unique review identifier |
| `review` | Review text |
| `rating` | Star rating (1–5) |
| `date` | Review date |
| `bank` | Bank name |
| `source` | "Google Play" |
| `sentiment_label` | positive / negative / neutral |
| `sentiment_score` | Model confidence score (0–1) |
| `identified_theme` | Assigned theme |
| `vader_score` | VADER compound score |
| `vader_label` | VADER label |
| `distilbert_label` | DistilBERT label |
| `distilbert_score` | DistilBERT confidence |

---

## Task 3 — PostgreSQL Database

**Notebook:** `notebooks/task3_database.ipynb`  
**Schema:** `scripts/schema.sql`  
**Database name:** `bank_reviews`

### Schema Design

```sql
-- Banks metadata table
CREATE TABLE banks (
    bank_id   SERIAL PRIMARY KEY,
    bank_name VARCHAR(100),
    app_name  VARCHAR(100)
);

-- Reviews table with foreign key to banks
CREATE TABLE reviews (
    review_id       SERIAL PRIMARY KEY,
    bank_id         INT REFERENCES banks(bank_id),
    review_text     TEXT,
    rating          INT,
    review_date     DATE,
    sentiment_label VARCHAR(20),
    sentiment_score FLOAT,
    identified_theme VARCHAR(100),
    source          VARCHAR(50)
);
```

### Setup

1. Install PostgreSQL and create the database:
```sql
CREATE DATABASE bank_reviews;
```

2. Run the schema:
```bash
psql -U postgres -d bank_reviews -f scripts/schema.sql
```

3. Run the insertion notebook to populate both tables from the analyzed CSV.

---

## Task 4 — Insights & Visualizations

**Notebook:** `notebooks/task4_insights.ipynb`

### Visualizations Produced

1. Sentiment distribution by bank (stacked bar chart)
2. Rating distribution per bank (boxplot)
3. Top keywords per bank (horizontal bar chart)
4. Theme frequency per bank (grouped bar chart)
5. Sentiment trend over time (line chart)

### Key Findings

*(Populated after Task 4 is complete)*

---

## CI/CD

GitHub Actions workflow runs on every push to `main`:

```yaml
# .github/workflows/unittests.yml
on:
  push:
    branches: [main]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with: { python-version: '3.10' }
      - run: pip install -r requirements.txt
      - run: pytest tests/
```

---

## Limitations

- **Language coverage:** Only English reviews scraped; many Ethiopian users write in Amharic, so local sentiment may be under-represented.
- **Unofficial API:** `google-play-scraper` uses an unofficial endpoint that may be rate-limited or break without notice.
- **Transformer model:** DistilBERT is trained on English SST-2 data; mixed-language or informal reviews may be misclassified.
- **Theme assignment:** Rule-based keyword matching assigns one theme per review; reviews touching multiple themes receive only the dominant one.
- **VADER domain fit:** VADER was designed for short social media text; longer Play Store reviews may have less accurate compound scores.
- **Date range:** The scraper does not support exact date filtering; the date range reflects whatever the API returns for the most recent reviews.

---

## Author

**Lielina Fekadu Zenebe**  
10 Academy — Artificial Intelligence Mastery Program | KAIM9  
Week 2 Challenge | May 2026
