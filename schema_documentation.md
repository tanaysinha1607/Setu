# Borrower Financial Data Schema Documentation

This document explains each field in the borrower financial data schema (`schema.json`) in plain English. This schema is used to represent structured financial metrics extracted from multimodal inputs such as SMS texts, photos of ledgers, and voice notes.

---

## Fields Overview

### 1. `source_type`
- **Type**: String (`enum`)
- **Allowed Values**: `"sms"`, `"ledger_photo"`, `"voice_note"`
- **Description**: Indicates the format of the input from which this information was extracted. This helps downstream applications apply source-specific processing or weightings (e.g., ledgers might be treated as more formal records than SMS).

### 2. `daily_revenue_estimate`
- **Type**: Number (Minimum: `0`)
- **Unit**: Indian Rupees (INR)
- **Description**: The model's estimated average daily revenue for the borrower, calculated from the provided input data.

### 3. `revenue_variance`
- **Type**: String (`enum`)
- **Allowed Values**: `"low"`, `"medium"`, `"high"`
- **Description**: Represents the volatility or fluctuation in the borrower's daily revenue. A `"high"` variance means the revenue fluctuates significantly day-to-day, whereas `"low"` indicates stable, predictable revenue.

### 4. `payment_consistency`
- **Type**: String (`enum`)
- **Allowed Values**: `"low"`, `"medium"`, `"high"`
- **Description**: Measures the reliability and regularity of the borrower's payment history. A `"high"` consistency suggests that payments are made on time without missing cycles.

### 5. `confidence_score`
- **Type**: Number (Float between `0.0` and `1.0`)
- **Description**: The extraction model's self-reported confidence level in the accuracy of the extracted structured data. `1.0` indicates absolute certainty, while `0.0` indicates complete uncertainty.

### 6. `anomaly_flags`
- **Type**: Array of Strings (Unique items)
- **Description**: An audit list of flags indicating unusual patterns or mismatches detected in the data. If no anomalies are detected, this list is empty (`[]`). Common flag examples include:
  - `"revenue_spike"` (unusual revenue increase)
  - `"narrative_mismatch"` (voice note conflicts with ledger photo data)

### 7. `raw_extracted_text`
- **Type**: String
- **Description**: The raw text that the model read or transcribed from the input (e.g., raw OCR text from a ledger image or the direct transcription of a voice note). This is crucial for auditing, debugging, and resolving extraction issues.

### 8. `timestamp`
- **Type**: String (ISO 8601 Date-Time format)
- **Description**: The date and time when the extraction process took place (e.g., `2026-07-10T03:05:36Z`), tracking data recency.

### 9. `borrower_session_id`
- **Type**: String
- **Description**: A shared identifier generated once per borrower assessment session. This links multiple separate extraction records (e.g., from SMS text, ledger photo, or voice note) for the same borrower together, allowing them to be grouped and fused into a single risk score later.
