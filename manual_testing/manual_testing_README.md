# Manual Testing Protocol - Binder's Business

**Purpose:** Enable human testers to manually verify calculations and algorithms before production deployment.

**Company Standard:** Every calculation, algorithm, or ML model output MUST be manually verifiable.

---

## 📋 Testing Philosophy

### Why Manual Testing?

1. **Catch Logic Errors:** Automated tests can pass with wrong logic
2. **Build Trust:** Stakeholders can verify calculations themselves
3. **Regulatory Compliance:** Some industries require human verification
4. **Model Validation:** Ensure ML models make sense to domain experts

---

## 🧪 Test Case Requirements

Every test case MUST include:

### 1. Metadata
```markdown
# Test Case NNN: [Feature Name]

**Date Created:** YYYY-MM-DD
**Feature:** [Feature name]
**Developer:** [Name]
**Reviewer:** [Name]
**Status:** PENDING / PASS / FAIL
```

### 2. Input Data
```markdown
## Input Data

[Sample data from real system - NO fake data]

Format: JSON / Table / Code snippet
Source: [Database query / API response / File]
```

### 3. Manual Calculation Steps
```markdown
## Manual Calculation Steps

Step 1: [Action]
  - Calculation: [Formula]
  - Result: [Number]

Step 2: [Action]
  - Calculation: [Formula]
  - Result: [Number]

...

Final Result: [Number]
```

### 4. Expected Output
```markdown
## Expected Output

[What the code should produce]

Format: JSON / Table / Value
```

### 5. Actual Output
```markdown
## Actual Output (from code)

[What the code actually produces]

Format: JSON / Table / Value
Run Date: YYYY-MM-DD HH:MM:SS
```

### 6. Validation
```markdown
## Validation

Status: ✅ PASS / ❌ FAIL

Comparison:
- Expected: [value]
- Actual: [value]
- Difference: [value or "None"]

Notes: [Any observations]
```

---

## 📁 Directory Structure

```
manual_testing/
├── README.md                          # This file
├── test_cases/                        # All test cases
│   ├── 001_credit_scoring.md
│   ├── 002_route_distance.md
│   ├── 003_zone_assignment.md
│   └── ...
├── validation_logs/                   # Test results
│   ├── 2025-10-29_validation.md
│   ├── 2025-10-28_validation.md
│   └── ...
└── templates/
    └── test_case_template.md         # Template for new cases
```

---

## 🚀 How to Create a Test Case

### Step 1: Copy Template
```bash
cp manual_testing/templates/test_case_template.md \
   manual_testing/test_cases/NNN_feature_name.md
```

### Step 2: Fill in Metadata
- Test case number (sequential)
- Feature name
- Your name
- Date

### Step 3: Add Real Input Data
- Get sample from actual system
- Anonymize if necessary (customer IDs, names)
- Include enough data to recreate calculation

### Step 4: Perform Manual Calculation
- Use calculator, spreadsheet, or pen & paper
- Show every step
- Write formulas explicitly

### Step 5: Document Expected Output
- Write what code should produce
- Be specific (decimals, units, format)

### Step 6: Run Code and Compare
- Execute actual code
- Capture output
- Compare with manual calculation

### Step 7: Document Result
- Mark PASS or FAIL
- Note any discrepancies
- Add reviewer notes

---

## 📊 Example: Simple Calculation

### Test Case 001: Credit Score

```markdown
# Test Case 001: Credit Score Calculation

**Date Created:** 2025-10-29
**Feature:** Customer Credit Scoring
**Developer:** John Doe
**Reviewer:** Jane Smith
**Status:** ✅ PASS

## Input Data

Customer: C12345
- Total Orders: 24
- Payment Delays: 3
- Average Order Value: 5200.00 SAR
- Aging Days: 45

## Manual Calculation Steps

Step 1: Calculate payment reliability
- Formula: (Total Orders - Payment Delays) / Total Orders
- Calculation: (24 - 3) / 24 = 21 / 24 = 0.875

Step 2: Calculate aging penalty
- Formula: Aging Days / Max Aging (90 days)
- Calculation: 45 / 90 = 0.5

Step 3: Compute base score
- Formula: (Reliability × 0.7) + ((1 - Aging Penalty) × 0.3)
- Calculation: (0.875 × 0.7) + ((1 - 0.5) × 0.3)
- Calculation: 0.6125 + 0.15 = 0.7625

Step 4: Scale to 0-1000
- Formula: Base Score × 1000
- Calculation: 0.7625 × 1000 = 762.5

Final Result: 762.5

## Expected Output

```json
{
  "customer_id": "C12345",
  "credit_score": 762.5,
  "risk_category": "MEDIUM",
  "confidence": 0.87
}
```

## Actual Output (from code)

```json
{
  "customer_id": "C12345",
  "credit_score": 762.5,
  "risk_category": "MEDIUM",
  "confidence": 0.87
}
```

Run Date: 2025-10-29 14:23:45

## Validation

Status: ✅ PASS

Comparison:
- Expected Credit Score: 762.5
- Actual Credit Score: 762.5
- Difference: 0.0 (Exact match)

Notes: Manual calculation matches code output perfectly. Algorithm is verified.

Reviewed By: Jane Smith
Review Date: 2025-10-29
```

---

## 🎯 Test Case Naming Convention

```
NNN_feature_name.md

Where:
- NNN = Sequential number (001, 002, 003, ...)
- feature_name = Descriptive, lowercase, underscored
```

**Examples:**
- `001_credit_scoring.md`
- `002_route_distance_calculation.md`
- `003_zone_boundary_assignment.md`
- `004_demand_forecasting_weekly.md`

---

## ✅ Validation Checklist

Before marking test case as PASS:

- [ ] Input data is from real system (not fake)
- [ ] Manual calculation is step-by-step
- [ ] Formulas are explicitly written
- [ ] Code output is captured
- [ ] Comparison shows exact match or acceptable tolerance
- [ ] Status is clearly marked (PASS/FAIL)
- [ ] Reviewer has signed off

---

## 📈 Test Coverage Goals

### Current Coverage
- Credit Scoring: ✅ Validated
- Route Distance: ✅ Validated
- Zone Assignment: ⏳ In Progress
- Demand Forecast: ❌ Not Started

### Target Coverage
- **Q4 2025:** 80% of calculations validated
- **Q1 2026:** 90% of calculations validated
- **Q2 2026:** 95% of calculations validated

---

## 🐛 When Tests Fail

### Step 1: Document Failure
```markdown
## Validation

Status: ❌ FAIL

Comparison:
- Expected: 762.5
- Actual: 758.3
- Difference: 4.2 (0.55% error)

Notes: Code output differs from manual calculation.
```

### Step 2: Create Issue
- Open issue in `universal_dev_tracker.md`
- Reference test case number
- Assign to developer

### Step 3: Root Cause Analysis
- Review code logic
- Check formula implementation
- Verify input data

### Step 4: Fix and Retest
- Update code
- Re-run test case
- Update validation status

---

## 📞 Need Help?

### Questions?
- Review this README.md
- Check example test cases in `test_cases/`
- Ask team lead or data science lead

### Template Not Clear?
- See `templates/test_case_template.md`
- Review existing test cases for examples

---

**END OF TESTING PROTOCOL**
