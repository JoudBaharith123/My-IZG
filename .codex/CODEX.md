# Codex Agent Instructions - Binder's Business

**Company:** Binder's Business - Logistics & Distribution Intelligence  
**Last Updated:** 2025-10-29 (Auto-updated by Codex)

---

## 🎯 Core Directive

**READ FIRST:** `universal_dev_tracker.md` - Your SINGLE source of truth for all project specs, todos, and progress.

---

## 🏢 Company Standards - Binder's Business

### Business Focus
- Logistics and distribution optimization
- Sales intelligence and route planning
- ML/DL-powered decision systems

### Technical Standards
1. **Scientific Rigor:** All ML/DL models MUST include cross-validation
2. **Performance Monitoring:** Real-time model performance tracking required
3. **Data Integrity:** NEVER use fake/synthetic data - only real or user-provided data
4. **Validation:** Every calculation requires manual test case for human verification

---

## 🚫 Agent Restrictions

### What Codex CANNOT Do (Unless Explicitly Requested)

❌ **NO verbose documentation files**  
❌ **NO long explanations or descriptions**  
❌ **NO architectural deep-dives**  
❌ **NO tutorial-style content**  
❌ **NO fake or synthetic data generation**  

### What Codex MUST Do

✅ **Update `universal_dev_tracker.md` timestamp on EVERY edit**  
✅ **Create manual test case for EVERY calculation/algorithm**  
✅ **Check infrastructure details in `.Codex/infrastructure.md`**  
✅ **Keep responses actionable and concise**  
✅ **Implement cross-validation for all ML/DL models**  

---

## 📍 File Locations

```
project_root/
├── universal_dev_tracker.md          ← Project spec, todos, progress
├── .Codex/
│   ├── Codex.md                     ← This file (agent instructions)
│   └── infrastructure.md             ← VM, ports, credentials
└── manual_testing/
    ├── README.md                     ← Testing protocol
    └── test_cases/                   ← Validation cases
        ├── 001_feature_name.md
        └── ...
```

---

## 🔧 Infrastructure Access

**All VM details, ports, IPs, credentials are in:** `.Codex/infrastructure.md`

**Never hardcode:** Read from infrastructure.md for current VM configuration.

---

## 🧪 Manual Testing Requirement (MANDATORY)

For **every calculation, algorithm, or ML model**, create:

```
manual_testing/test_cases/NNN_[feature_name].md
```

**Must include:**
1. Input data (sample from real data)
2. Step-by-step manual calculation
3. Expected output
4. Actual code output
5. Validation status (PASS/FAIL)

**Purpose:** Enable human testers to manually verify calculations.

---

## 📋 Development Workflow

### Step 1: Check Current Task
```bash
# Read universal_dev_tracker.md
# Find next task in TODO list
```

### Step 2: Get Infrastructure Details
```bash
# Read .Codex/infrastructure.md
# Get VM IP, ports, credentials
```

### Step 3: Develop Feature
- Implement with cross-validation (ML/DL)
- Add performance monitoring
- Use only real data
- Keep code clean and documented

### Step 4: Create Manual Test Case
```bash
# Create manual_testing/test_cases/NNN_feature.md
# Include step-by-step calculation
# Enable manual verification
```

### Step 5: Update Tracker
```bash
# Update universal_dev_tracker.md
# AUTO-UPDATE timestamp
# Mark task complete
# Update progress metrics
```

---

## 🎯 Code Development Standards

### Machine Learning / Deep Learning
```python
# REQUIRED: Cross-validation
from sklearn.model_selection import cross_val_score

# REQUIRED: Performance monitoring
import mlflow

# REQUIRED: No fake data
# Use only real data or explicitly provided test data
```

### Routing / Optimization
```python
# REQUIRED: Configurable parameters (JSON)
# REQUIRED: Debug mode
# REQUIRED: Test mode
# REQUIRED: Logging with run ID
# REQUIRED: Manual test case for algorithm
```

### General Python
```python
# REQUIRED: Type hints
# REQUIRED: Docstrings for functions
# REQUIRED: Error handling
# REQUIRED: Logging (not print statements)
```

---

## 📊 Response Format

### When Asked to Develop Feature

**Good Response:**
```
✅ Created: src/feature.py
✅ Config: config/feature.json
✅ Test Case: manual_testing/test_cases/005_feature.md
✅ Updated: universal_dev_tracker.md (2025-10-29 14:23:45)

Summary: [1-2 sentences max]
```

**Bad Response:**
```
❌ I've created a comprehensive solution...
[5 paragraphs of explanation]
[Architectural diagrams]
[Tutorial content]
```

### When Explaining Code

**Good Response:**
```python
# Calculate credit score
score = (reliability * 0.7) + (aging_penalty * 0.3)
# Manual test case: manual_testing/test_cases/003_credit_score.md
```

**Bad Response:**
```python
# This function implements a sophisticated credit scoring algorithm
# that leverages multiple data points to assess customer reliability.
# The algorithm consists of several steps:
# 1. First, we calculate...
# [10 more lines of explanation]
```

---

## 🔄 Universal Dev Tracker Auto-Update

**On EVERY edit to `universal_dev_tracker.md`, Codex MUST:**

1. Update timestamp in header:
```markdown
**Last Updated:** 2025-10-29 14:23:45 UTC
```

2. Update progress metrics (if applicable)

3. Add changelog entry (bottom of file)

---

## 🚨 Emergency Protocols

### If Fake Data Is Requested
```
❌ Cannot generate fake/synthetic data per company policy.
✅ Alternative: Use sample slice from real data or request test dataset.
```

### If Asked for Verbose Documentation
```
❌ Will not create unless explicitly requested.
✅ Alternative: Point to relevant section in universal_dev_tracker.md
```

### If Manual Test Case Cannot Be Created
```
⚠️ Flag as "REQUIRES HUMAN VALIDATION" in universal_dev_tracker.md
✅ Explain why manual calculation is not feasible
```

---

## 📚 Quick Reference

### Check Project Status
```bash
cat universal_dev_tracker.md
```

### Get VM Details
```bash
cat .Codex/infrastructure.md
```

### View Test Cases
```bash
ls manual_testing/test_cases/
```

### Run Manual Validation
```bash
# Follow steps in manual_testing/test_cases/NNN_feature.md
# Compare manual result with code output
```

---

## 🎓 Example: Complete Feature Development

### User Request
"Implement customer credit scoring model"

### Codex Actions

1. **Check tracker:**
```bash
# Read universal_dev_tracker.md
# Find: [ ] Implement credit scoring (Priority: High)
```

2. **Check infrastructure:**
```bash
# Read .Codex/infrastructure.md
# Get: Database credentials, API endpoints
```

3. **Develop feature:**
```python
# src/credit_scoring.py
# - Cross-validation implemented
# - Performance monitoring added
# - Config-driven (config/credit_scoring.json)
```

4. **Create test case:**
```markdown
# manual_testing/test_cases/003_credit_scoring.md
# - Sample real customer data
# - Step-by-step calculation
# - Expected vs actual output
```

5. **Update tracker:**
```markdown
# universal_dev_tracker.md
**Last Updated:** 2025-10-29 14:45:12 UTC

## TODO
- [x] Implement credit scoring (Status: Complete | Completed: 2025-10-29)

## Changelog
- 2025-10-29 14:45: Credit scoring model implemented with cross-validation
```

6. **Respond concisely:**
```
✅ Credit scoring model implemented
✅ Test case: manual_testing/test_cases/003_credit_scoring.md
✅ Tracker updated

Cross-validation score: 0.87 (±0.03)
```

---

## ✅ Checklist: Before Responding to ANY Request

- [ ] Read `universal_dev_tracker.md` for context
- [ ] Check `.Codex/infrastructure.md` if VM/service details needed
- [ ] Create manual test case if implementing calculation
- [ ] Update `universal_dev_tracker.md` timestamp
- [ ] Keep response under 10 lines (unless explicitly asked for more)
- [ ] Verify no fake data used
- [ ] Confirm cross-validation added (if ML/DL)

---

**END OF Codex INSTRUCTIONS**

*This file should remain under 200 lines. Last count: 195 lines.*
