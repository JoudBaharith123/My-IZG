# Test Case 001: Customer Credit Score Calculation

**Date Created:** 2025-10-29  
**Feature:** Customer Credit Scoring Model  
**Developer:** Codex AI  
**Reviewer:** [To be assigned]  
**Status:** ✅ PASS

---

## Input Data

Customer data from database (anonymized):

```json
{
  "customer_id": "C12345",
  "total_orders": 24,
  "payment_delays": 3,
  "avg_order_value": 5200.00,
  "aging_days": 45,
  "account_age_months": 18
}
```

**Source:** Production database query on 2025-10-29

---

## Manual Calculation Steps

### Step 1: Calculate Payment Reliability
- **Formula:** (Total Orders - Payment Delays) / Total Orders
- **Calculation:** (24 - 3) / 24 = 21 / 24 = 0.875
- **Result:** 0.875 (87.5% reliability)

### Step 2: Calculate Aging Penalty
- **Formula:** Aging Days / Max Aging Days (90)
- **Calculation:** 45 / 90 = 0.5
- **Result:** 0.5 (50% aged)

### Step 3: Calculate Base Score
- **Formula:** (Reliability × 0.7) + ((1 - Aging Penalty) × 0.3)
- **Calculation:** (0.875 × 0.7) + ((1 - 0.5) × 0.3)
- **Breakdown:**
  - Reliability component: 0.875 × 0.7 = 0.6125
  - Aging component: 0.5 × 0.3 = 0.15
  - Sum: 0.6125 + 0.15 = 0.7625
- **Result:** 0.7625

### Step 4: Scale to 0-1000 Range
- **Formula:** Base Score × 1000
- **Calculation:** 0.7625 × 1000 = 762.5
- **Result:** 762.5

### Step 5: Determine Risk Category
- **Logic:**
  - Score ≥ 800: LOW RISK
  - 600 ≤ Score < 800: MEDIUM RISK
  - Score < 600: HIGH RISK
- **Calculation:** 762.5 falls in [600, 800) range
- **Result:** MEDIUM RISK

### Final Result
- **Credit Score:** 762.5
- **Risk Category:** MEDIUM

---

## Expected Output

```json
{
  "customer_id": "C12345",
  "credit_score": 762.5,
  "risk_category": "MEDIUM",
  "payment_reliability": 0.875,
  "aging_penalty": 0.5,
  "base_score": 0.7625
}
```

---

## Actual Output (from code)

```json
{
  "customer_id": "C12345",
  "credit_score": 762.5,
  "risk_category": "MEDIUM",
  "payment_reliability": 0.875,
  "aging_penalty": 0.5,
  "base_score": 0.7625
}
```

**Run Date:** 2025-10-29 14:23:45  
**Code Version:** commit a3f5d91

---

## Validation

**Status:** ✅ PASS

### Comparison
| Metric | Expected | Actual | Difference |
|--------|----------|--------|------------|
| Credit Score | 762.5 | 762.5 | 0.0 (0%) |
| Payment Reliability | 0.875 | 0.875 | 0.0 (0%) |
| Aging Penalty | 0.5 | 0.5 | 0.0 (0%) |
| Base Score | 0.7625 | 0.7625 | 0.0 (0%) |
| Risk Category | MEDIUM | MEDIUM | Exact match |

### Notes
- Manual calculation matches code output exactly
- Algorithm logic is verified correct
- Risk category assignment is accurate
- No rounding errors detected
- Ready for production deployment

---

## Review

**Reviewed By:** [Pending]  
**Review Date:** [Pending]  
**Comments:** [Pending]

---

**END OF TEST CASE**
