# Testing Guide - 5 New Features

**Date:** 2025-11-09
**Features to Test:** Column Mapping, Filter Selection, View All Customers, Download Fixes, GeoJSON Export

---

## Prerequisites

### 1. Start Servers

**Backend:**
```bash
cd /root/openai_projects/Binder_intelligent_zone_generator_v1/Intelligent_zone_generator
source ../.venv/bin/activate
export PYTHONPATH="${PWD}/src:${PYTHONPATH}"
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend:**
```bash
cd /root/openai_projects/Binder_intelligent_zone_generator_v1/Intelligent_zone_generator/ui
npm run dev
```

**Access URL:** http://localhost:5173 (or the URL shown by vite)

---

## Feature 1 & 2: Column Mapping + Filter Selection

### Test Scenario: Upload CSV with Custom Column Names

**Steps:**

1. **Navigate to Upload Page**
   - Click "Upload & Validate" in sidebar
   - Click "Upload New Dataset" button

2. **Select a Test CSV File**
   - Prepare a CSV with non-standard column names:
     ```csv
     ID,Name,Lat,Lon,Town,Area_Code
     12345,Customer A,21.5,39.2,Jeddah,JED_01
     12346,Customer B,24.7,46.7,Riyadh,RYD_02
     ```

3. **Column Mapping Modal Opens** ✅ Expected Behavior:
   - Modal appears with title "Map Columns"
   - Shows file name at top
   - Table displays:
     - **System Field** column (customer_id, latitude, longitude, etc.)
     - **Description** column
     - **CSV Column** dropdown
     - **Use as Filter** checkbox
     - **Status** indicator (✓ or ⚠)

4. **Check Auto-Suggestions** ✅ Expected Behavior:
   - `customer_id` → Should suggest "ID"
   - `latitude` → Should suggest "Lat"
   - `longitude` → Should suggest "Lon"
   - `city` → Should suggest "Town"
   - `zone` → Should suggest "Area_Code"

5. **Manually Adjust Mappings**
   - Change any dropdown if suggestions are wrong
   - Try unmapping a required field → Should show ⚠ warning
   - Confirm "Confirm & Upload" button is disabled until required fields mapped

6. **Select Filter Columns** (Feature 2)
   - Check "Use as Filter" for "Town" column
   - Check "Use as Filter" for "Area_Code" column
   - **Blue summary box** should appear showing: "Selected Filter Columns (2): Town, Area_Code"

7. **Confirm Upload**
   - Click "Confirm & Upload"
   - Modal closes
   - Upload should proceed
   - Success message appears: "Upload complete: [filename]"

### ✅ Pass Criteria:
- [ ] Modal opens automatically after file selection
- [ ] Auto-suggestions work for common column names
- [ ] Required fields show red asterisk (*)
- [ ] Upload button disabled until required fields mapped
- [ ] Filter checkboxes work
- [ ] Filter summary shows selected columns
- [ ] Upload completes successfully

---

## Feature 3: View All Customers on Map

### Test Scenario: View Entire Dataset

**Steps:**

1. **Navigate to Zoning Workspace**
   - Click "Zoning Workspace" in sidebar

2. **Check City Dropdown** ✅ Expected Behavior:
   - First option should be **"All Cities"**
   - Other cities listed below

3. **Select "All Cities"**
   - Select "All Cities" from dropdown
   - Map should load with customers from ALL cities
   - Map caption should show: **"All Cities - [customer count] customers"**

4. **Check Performance Warning** ✅ Expected Behavior (if >5000 customers):
   - Yellow warning banner appears:
     ```
     ⚠ Large dataset detected (X,XXX customers)
     For better performance, select a specific city. Currently showing first X,XXX customers.
     ```

5. **Check Marker Sizes** ✅ Expected Behavior:
   - If >2000 customers: Markers should be **3px**
   - If 1000-2000 customers: Markers should be **4px**
   - If <1000 customers: Markers should be **6px**

6. **Try to Generate Zones**
   - Click "Generate Zones" with "All Cities" selected
   - **Error should appear:** "Cannot generate zones for 'All Cities'. Please select a specific city."

7. **Switch to Specific City**
   - Select a specific city (e.g., "Jeddah")
   - Map reloads showing only that city's customers
   - Caption updates to show city name

### ✅ Pass Criteria:
- [ ] "All Cities" appears as first dropdown option
- [ ] Map loads all customers when "All Cities" selected
- [ ] Performance warning shows for large datasets
- [ ] Marker sizes scale based on customer count
- [ ] Zone generation blocked for "All Cities"
- [ ] Can switch back to specific city successfully

---

## Feature 4: Fix Download Files in Reports

### Test Scenario: Download Reports

**Steps:**

1. **Generate Some Data First**
   - Go to Zoning Workspace
   - Select a city (e.g., "Jeddah")
   - Set target zones to 5
   - Click "Generate Zones"
   - Wait for results

2. **Navigate to Reports Page**
   - Click "Reports & Exports" in sidebar

3. **Check Export Files List** ✅ Expected Behavior:
   - Should see recent zone generation run
   - Files should include:
     - `summary.json`
     - `assignments.csv`
     - `zones.geojson` (NEW!)

4. **Test CSV Download**
   - Click download icon for `assignments.csv`
   - **Browser should download file**
   - **Success toast appears:** "Downloaded: assignments.csv" (green checkmark)

5. **Test JSON Download**
   - Click download for `summary.json`
   - File downloads
   - Success toast appears

6. **Test GeoJSON Download** (Feature 5)
   - Click download for `zones.geojson`
   - File downloads with correct extension
   - Success toast appears

7. **Check Console (F12)**
   - Open browser DevTools Console
   - Look for download logs:
     ```
     [Download] Starting download: {fileName: "...", downloadPath: "..."}
     [Download] Response received: {status: 200, ...}
     [Download] Triggering file download: {blobSize: ..., blobType: "..."}
     [Download] Download completed successfully
     ```

8. **Test Failed Download**
   - Manually edit a file path in browser DevTools (if possible)
   - Or stop backend server temporarily
   - Try to download
   - **Error toast should appear:** "Download failed. Please try again." (red alert icon)

### ✅ Pass Criteria:
- [ ] Downloads trigger browser save dialog
- [ ] Success toast notification shows with green checkmark
- [ ] Error toast shows if download fails
- [ ] Console logs show debug information
- [ ] Correct MIME types set (check Network tab: text/csv, application/json, application/geo+json)
- [ ] Files open correctly after download

---

## Feature 5: GeoJSON Export (EasyTerritory Format)

### Test Scenario: Export Zones as GeoJSON

**Steps:**

1. **Generate Zones**
   - Zoning Workspace → Select city → Generate zones
   - Wait for results to appear

2. **Download from Workspace**
   - Scroll to "Downloads" section
   - Click **"GeoJSON"** button
   - File downloads as `zones_[method]_[city].geojson`

3. **Verify GeoJSON Structure**
   - Open downloaded file in text editor
   - Should be a JSON array with objects like:
     ```json
     [
       {
         "id": "uuid-here",
         "name": "ZONE_01",
         "group": "JEDDAH",
         "featureClass": "2",
         "wkt": "POLYGON((lon1 lat1,lon2 lat2,...))",
         "json": "{\"type\":\"clustering\",\"subType\":null,\"labelPoint\":{...}}",
         "visible": true,
         "symbology": {
           "fillColor": "#02d8e0",
           "fillOpacity": 0.33,
           "lineColor": "black",
           "lineWidth": 2,
           "lineOpacity": 0.5,
           "scale": null
         },
         "notes": "tag : JEDDAH|ZONE_01\n...",
         "nodeTags": [],
         "nameTagPlacementPoint": null,
         "simplificationMeters": 0,
         "modifiedTimestamp": 0,
         "managerId": null,
         "collapsed": true,
         "locked": null
       }
     ]
     ```

4. **Check Backend Auto-Generation**
   - Go to Reports page
   - Find the zone generation run
   - Should see `zones.geojson` file listed
   - Download it
   - Should match the format above

5. **Test Route GeoJSON** (if routing is set up)
   - Generate routes for a zone
   - Check Downloads section
   - GeoJSON should include route linestrings

6. **Verify WKT Geometry**
   - WKT should be `POLYGON((lon lat,lon lat,...))`
   - Note: WKT uses **lon,lat** order (not lat,lon!)
   - Coordinates should match zone boundaries on map

### ✅ Pass Criteria:
- [ ] GeoJSON download button appears in Zoning Workspace
- [ ] Downloaded file is valid JSON
- [ ] Contains array of feature objects
- [ ] Each feature has all required EasyTerritory fields
- [ ] WKT geometry is properly formatted
- [ ] Symbology includes colors matching map display
- [ ] Backend auto-generates .geojson files
- [ ] GeoJSON files appear in Reports page

---

## Additional Testing

### Browser Console Checks

**Open DevTools (F12) → Console:**

1. **During Upload:**
   - No errors should appear
   - Look for successful API responses

2. **During Download:**
   - Check for `[Download]` log messages
   - Verify blob creation and MIME types

3. **During Map Loading:**
   - No React errors
   - Map tiles load correctly

### Network Tab Checks

**Open DevTools (F12) → Network:**

1. **Preview Endpoint:**
   - POST `/api/customers/upload/preview`
   - Status: 200
   - Response contains `detectedColumns`, `suggestedMappings`

2. **Locations Endpoint with "all":**
   - GET `/api/customers/locations?city=all&pageSize=1500`
   - Status: 200
   - Returns customers from all cities

3. **Download Requests:**
   - GET `/api/reports/exports/{run_id}/{filename}`
   - Headers include:
     - `Content-Type: text/csv` (for CSV)
     - `Content-Type: application/json` (for JSON)
     - `Content-Type: application/geo+json` (for GeoJSON)
     - `Content-Disposition: attachment; filename="..."`

---

## Troubleshooting

### Modal Doesn't Appear
- Check browser console for errors
- Verify `/api/customers/upload/preview` endpoint returns 200
- Check network tab for preview request

### Downloads Don't Work
- Open Network tab, check response headers
- Verify Content-Type and Content-Disposition headers
- Check console for `[Download]` logs
- Try different browser if issue persists

### "All Cities" Shows No Customers
- Check `/api/customers/locations?city=all` response
- Verify backend recognizes "all" as special value
- Check customer data has valid coordinates

### GeoJSON File Invalid
- Validate JSON structure with online validator
- Check WKT format: `POLYGON((lon lat,lon lat,...))`
- Verify coordinates are in correct order

---

## Success Criteria Summary

### Overall Testing Complete When:
- [ ] All 5 features tested
- [ ] No console errors during normal operation
- [ ] All downloads work correctly
- [ ] GeoJSON format matches EasyTerritory spec
- [ ] Column mapping modal functions correctly
- [ ] Filter selection works
- [ ] "All Cities" option works
- [ ] Performance optimizations visible (marker sizes, warnings)

---

## Reporting Issues

If you find bugs, note:
1. **Feature:** Which feature (1-5)
2. **Steps:** What you did
3. **Expected:** What should happen
4. **Actual:** What actually happened
5. **Console:** Any error messages
6. **Network:** Failed requests (if any)
7. **Screenshot:** If applicable

---

**Happy Testing!** 🧪
