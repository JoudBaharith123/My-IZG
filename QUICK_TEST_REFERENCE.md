# Quick Test Reference Card

## 🚀 Quick Start

```bash
# Terminal 1 - Backend
cd /root/openai_projects/Binder_intelligent_zone_generator_v1/Intelligent_zone_generator
source ../.venv/bin/activate
export PYTHONPATH="${PWD}/src:${PYTHONPATH}"
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 - Frontend
cd /root/openai_projects/Binder_intelligent_zone_generator_v1/Intelligent_zone_generator/ui
npm run dev

# Access: http://localhost:5173 (or URL shown by vite)
```

---

## ✅ Feature Quick Tests

### Feature 1 & 2: Column Mapping + Filters (2 min)

1. Go to **Upload & Validate**
2. Upload `manual_testing/sample_data_custom_columns.csv`
3. Modal appears → Check auto-suggestions
4. Check "Town" and "Area_Code" as filters
5. Click "Confirm & Upload"

**✓ Pass:** Modal works, filters selected, upload succeeds

---

### Feature 3: View All Customers (1 min)

1. Go to **Zoning Workspace**
2. Select **"All Cities"** from dropdown
3. Check map loads all customers
4. Try to generate zones → Should error

**✓ Pass:** "All Cities" option exists, map loads, generation blocked

---

### Feature 4: Download Fixes (2 min)

1. Generate zones (any city, any method)
2. Go to **Reports & Exports**
3. Download any file (CSV, JSON, GeoJSON)
4. Check success toast appears

**✓ Pass:** File downloads, green toast shows "Downloaded: [filename]"

---

### Feature 5: GeoJSON Export (2 min)

1. After generating zones, click **"GeoJSON"** download button
2. Open downloaded file
3. Verify it's a JSON array with WKT polygons

**✓ Pass:** File contains EasyTerritory format with `wkt`, `symbology`, etc.

---

## 🐛 Common Issues

| Issue | Solution |
|-------|----------|
| Modal doesn't open | Check console, verify preview endpoint working |
| "All Cities" not showing | Clear cache, refresh page |
| Download fails | Check Network tab for MIME types |
| GeoJSON invalid | Verify polygons exist on map first |

---

## 📊 Visual Checks

### Column Mapping Modal
- [ ] Blue info banner at top
- [ ] Table with 5 columns
- [ ] Red asterisks (*) on required fields
- [ ] Green checkmarks (✓) on mapped fields
- [ ] Filter checkboxes
- [ ] Blue filter summary box
- [ ] Disabled "Confirm" button until required fields mapped

### Reports Page
- [ ] Green toast on successful download
- [ ] Red toast on failed download
- [ ] Files listed with .geojson extension
- [ ] Download icons clickable

### Zoning Workspace
- [ ] "All Cities" as first dropdown option
- [ ] Yellow warning for large datasets
- [ ] Smaller markers when many customers
- [ ] GeoJSON download button in Downloads section

---

## 🎯 Success in 10 Minutes

**Fastest Path to Verify All Features:**

```
1. Upload custom CSV (2 min) → Test Features 1 & 2
2. Select "All Cities" (1 min) → Test Feature 3
3. Generate zones (2 min) → Setup for 4 & 5
4. Download reports (2 min) → Test Feature 4
5. Download GeoJSON (1 min) → Test Feature 5
6. Verify files (2 min) → Open downloads, check structure
```

**Total: 10 minutes** ⏱️

---

## 📁 Test Data Locations

- **Sample CSV:** `manual_testing/sample_data_custom_columns.csv`
- **Testing Guide:** `TESTING_GUIDE.md`
- **Real GeoJSON Example:** `data/easyterritory_geojson_routes.JSON`

---

## 🔍 Debug Commands

**Check Preview Endpoint:**
```bash
curl -X POST http://localhost:8000/api/customers/upload/preview \
  -F "file=@manual_testing/sample_data_custom_columns.csv"
```

**Check "All" Parameter:**
```bash
curl "http://localhost:8000/api/customers/locations?city=all&pageSize=10"
```

**Check Download Headers:**
```bash
curl -I "http://localhost:8000/api/reports/exports/{run_id}/summary.json"
# Look for: Content-Type, Content-Disposition
```

---

**Created:** 2025-11-09 | **Features:** 5 | **Test Time:** ~10 min
