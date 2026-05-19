# Fintech App Review Analysis — Insight Report

## Executive Summary

This report presents findings from **1,429 Google Play Store reviews** collected across
three Ethiopian banks: Commercial Bank of Ethiopia (CBE), Bank of Abyssinia (BoA), and
Dashen Bank. Reviews were scraped, cleaned, sentiment-analyzed using DistilBERT, and
categorized into themes using keyword matching.

Overall, **43.5%** of reviews are positive, **26.9%** are negative,
and the remainder are neutral. The analysis surfaces clear satisfaction drivers and
recurring pain points for each bank.

---

## Dataset Overview

| Bank | Reviews | Avg Rating | % Positive | % Negative |
|------|---------|-----------|-----------|-----------|
| Commercial Bank of Ethiopia | 448 | 3.90 ★ | 48.4% | 21.9% |
| Bank of Abyssinia | 490 | 3.28 ★ | 34.9% | 30.8% |
| Dashen Bank | 491 | 3.77 ★ | 47.5% | 27.5% |

---

## Bank-by-Bank Insights

### Commercial Bank of Ethiopia (CBE)

**Average rating: 3.90 ★** — highest among the three banks.

**Satisfaction drivers:**
- **General Feedback**: The most frequently praised theme. Users highlight smooth transaction
  experiences and reliable core banking features.
- **Transaction Performance**: Second key driver — users appreciate this aspect of the app experience.

**Pain points:**
- **Transaction Performance**: The most common complaint theme, indicating friction in this area that
  the product team should prioritize.
- **General Feedback**: A secondary pain point worth addressing to improve retention.

---

### Bank of Abyssinia (BoA)

**Average rating: 3.28 ★** — lowest among the three, indicating room for improvement.

**Satisfaction drivers:**
- **General Feedback**: Users respond positively to this area of the app.
- **App Stability & UI**: Secondary driver contributing to positive reviews.

**Pain points:**
- **General Feedback**: The top complaint category for BoA users, suggesting a significant
  usability or reliability gap.
- **App Stability & UI**: A recurring secondary concern that compounds negative perception.

---

### Dashen Bank

**Average rating: 3.77 ★** — mid-range performance with a large user base.

**Satisfaction drivers:**
- **General Feedback**: Top positive theme for Dashen users.
- **Transaction Performance**: Strong secondary driver of satisfaction.

**Pain points:**
- **General Feedback**: Most mentioned negative theme — users cite issues here consistently.
- **App Stability & UI**: A secondary pain area to monitor and address.

---

## Cross-Bank Comparisons

### Sentiment
CBE leads in positive sentiment (48.4%), while BoA has the highest negative
rate (30.8%). Dashen sits in the middle, with a relatively balanced distribution.

### Ratings
The skewed rating distribution (heavy at 1★ and 5★ across all banks) is typical of
app store reviews, where users are motivated to review primarily after very good or
very bad experiences. Mid-range ratings (2–4★) are underrepresented.

### Common Themes
"General Feedback" dominates across all banks, reflecting broad satisfaction or
dissatisfaction without a specific feature focus. "Transaction Performance" and
"App Stability & UI" are the most actionable themes, appearing across all three banks
and tied most closely to high-sentiment reviews.

---

## Recommendations

1. **All banks**: Invest in app stability improvements — "App Stability & UI" is a
   top pain point driver and directly affects star ratings.

2. **BoA specifically**: With the lowest average rating (3.28★), a focused
   UX audit on account access and transaction flows is recommended.

3. **CBE**: Leverage its positive sentiment lead (48.4% positive) in marketing,
   while addressing its specific pain points to protect its rating advantage.

4. **Dashen**: Targeted improvements to its top pain-point theme could push its average
   rating above 4★ and close the gap with CBE.

---

## Methodology

| Step | Tool / Approach |
|------|----------------|
| Data collection | google-play-scraper (Python) |
| Preprocessing | pandas — dedup, date normalization, text cleaning |
| Sentiment analysis | DistilBERT (distilbert-base-uncased-finetuned-sst-2-english) |
| Theme classification | Keyword matching across 6 categories |
| Storage | PostgreSQL (bank_reviews database) |
| Visualization | matplotlib |

---

*Report generated automatically by `generate_insights.py`*
*Data covers 2024-11-12 to 2026-05-16*
