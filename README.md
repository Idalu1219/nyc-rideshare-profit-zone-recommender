# NYC Rideshare Profit Zone Recommender

> Predicts hourly profitability for NYC for-hire vehicle drivers across 263 zones using Random Forest regression (R²=0.90), with Top-5 zone recommendations balanced for earnings and geographic spread.

---

## The Problem

NYC's 2025 Congestion Pricing Program changed the game for for-hire vehicle (FHV) drivers overnight. Higher passenger costs shifted demand away from Manhattan's core — and the zones that used to be reliably profitable became less predictable.

This project asks: **given the time, weather, and recent demand, where should a driver go next?**

Rather than pointing every driver to the same hotspot, I built a recommendation system that surfaces the **Top-5 most profitable zones per hour** while keeping picks geographically spread — so drivers get real choices, not a traffic jam of competitors.

---

## Key Results

| Metric | Value |
|---|---|
| Test R² (Jan–Jun 2025) | **0.900** |
| Test RMSE | 32.42 |
| Test MAE | 17.26 |
| Overlap@5 (avg zones matched) | **~3 out of 5 per hour** |
| Recall@5 (profit share captured) | ~8% of citywide profit |
| Diversity (avg spread) | **~8 km between recommended zones** |

The model was trained entirely on 2024 data and generalised to 2025 without retraining — a deliberate design choice to validate real-world robustness across the policy shift.

---

## What I Built

### Data Pipeline
Processed ~120 million raw TLC trip records per year, applying multi-stage filtering (speed plausibility, fare integrity, IQR outlier removal) to retain ~108M valid trips. Integrated hourly weather from NOAA's Central Park station and a calendar feature set covering holidays and weekday patterns.

### Feature Engineering
Aggregated everything to a **zone × hour** level and engineered a custom profit score:

```
profit_score(z, h) = (total_driver_pay / total_trip_minutes) × number_of_trips
```

This balances earnings efficiency with demand volume — a zone with great pay-per-minute but no riders still scores low. Temporal lag features (`t-1` and `t-24` trip counts) were added as predictive signals without data leakage.

### Modelling
Compared a **Ridge regression baseline** against a **Random Forest ensemble**:

| Model | RMSE | MAE | R² |
|---|---|---|---|
| Ridge (λ=1e-4) | 35.17 | 18.46 | 0.880 |
| **Random Forest** | **31.51** | **17.08** | **0.904** |

Random Forest captured non-linear interactions (e.g., congestion effects that depend jointly on demand, speed, and time-of-day) that Ridge couldn't model.

### Recommendation System
Built custom evaluation metrics from scratch to assess recommendation quality beyond standard ML metrics:

- **Overlap@5** — how many predicted top zones match the actual top zones each hour
- **Recall@5** — what share of total citywide profit the recommendations capture
- **Diversity** — mean pairwise distance (km) between recommended zones, penalising clustering

---

## What I Found

- **LaGuardia Airport** remained the single most profitable zone in both years
- Brooklyn zones (**Crown Heights North, Bushwick South, Williamsburg**) broke into the top 10 in 2025 — consistent with congestion pricing redirecting demand away from central Manhattan
- Weekday profitability peaks sharply at **7–9am and 5–8pm** (commuter hours); weekends peak **8–11pm** (leisure)
- Holiday shifts follow a distinct pattern: low morning profit, competitive from midday onwards





---

## Tech Stack

| Category | Tools |
|---|---|
| Data processing | Python, PySpark, pandas |
| Modelling | scikit-learn (Ridge, Random Forest) |
| Geospatial | GeoPandas, Folium, Leaflet |
| Visualisation | matplotlib, seaborn |
| Environment | Jupyter, Python 3.12 |

---

## Project Structure

```
notebooks/
  00_download_data.ipynb            → Fetch raw TLC HVFHV data
  01_process_fhvhv.ipynb            → Build hourly zone features (lags, trips, speed, distance)
  02_process_weather.ipynb          → Ingest & aggregate NOAA weather to hourly
  03_process_calender.ipynb         → Calendar flags (hour, day of week, holiday, weekend)
  04_join_all_features.ipynb        → Join all features; write curated train/val/test splits
  05_process_taxi_zone.ipynb        → Load TLC zone shapes, reproject to WGS84, compute centroids

  10_preliminary_analysis.ipynb     → EDA: distributions, missingness, outlier analysis
  11_temporal_geospatial_analysis   → Daily/weekly/holiday trends; choropleth maps

  20_modelling.ipynb                → Ridge baseline & Random Forest (train 2024 Jan–Apr, val May–Jun)
  21_evaluation_on_test.ipynb       → Score 2025 Jan–Jun; compute RMSE/MAE/R², Overlap/Recall/Diversity
  30_recommendations.ipynb          → Convert predictions to driver-friendly Top-5 zone guidance

scripts/
  spark_session.py                  → SparkSession helper
  tlc_io.py                         → I/O utilities for TLC data
  weather_io.py                     → Weather ingest utilities
  classify_target.py                → Profit score derivation helpers
```

---

## Getting Started

**Requirements:** Python 3.12, ~16GB RAM recommended for Spark steps

```bash
# 1. Clone and install dependencies
git clone https://github.com/yourusername/nyc-rideshare-profit-zone-recommender
cd nyc-rideshare-profit-zone-recommender
pip install -r requirements.txt

# 2. (Optional) Set Spark memory
export SPARK_DRIVER_MEMORY=8g

# 3. Download weather data
# https://www.ncei.noaa.gov/oa/local-climatological-data/index.html#v2/access/2025/

# 4. Run notebooks in order: 00 → 05 → 10 → 11 → 20 → 21 → 30
jupyter notebook
```

**Note:** Raw TLC trip data is not included in this repo due to size (~GB per month). Download from the [NYC TLC Trip Record Data portal](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page). The data pipeline notebooks handle ingestion from raw files.

---

## Data Sources

- [NYC TLC High-Volume FHV Trip Records](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page) — ~120M trips/year
- [NOAA Local Climatological Data — Central Park](https://www.ncei.noaa.gov/metadata/geoportal/rest/metadata/item/gov.noaa.ncdc:C01689/html) — hourly weather
- [Python `holidays` library](https://pypi.org/project/holidays/) — US public holiday calendar

---

## Limitations & Future Work

- The model slightly underpredicts profit peaks in March and May — a known regression-to-the-mean behaviour in ensemble methods; calibration techniques could address this
- Incorporating real-time traffic speed, special event data, or transit disruptions would likely improve demand spike prediction
- The recommendation system currently optimises for a single hour ahead; multi-step forecasting would make it more actionable for shift planning

---

*Built as a capstone data science project at the University of Melbourne, 2025.*