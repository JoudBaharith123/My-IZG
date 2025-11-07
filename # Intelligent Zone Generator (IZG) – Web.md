# Intelligent Zone Generator (IZG) – Web UI Specification

## Design Goals
A fast, planner-focused workflow for:
- Uploading and validating customer data  
- Generating balanced geographic zones  
- Reviewing routing results  
- Exporting reports  

The interface should be **map-centric**, **responsive**, and **built with React + Tailwind** components, focusing on usability and planner efficiency.

---

## 1. Global Layout

### Top Bar
- **Title:** *Intelligent Zone Generator*  
- **Health Indicators:** OSRM status chip (✅ / ⚠️)  
- **Quick Links:** Documentation | Downloads | Notifications  
- **CTA:** “Start New Upload”

### Left Navigation
- **Sections (Icon + Label):**
  1. Upload & Validate  
  2. Zoning Workspace  
  3. Routing Workspace  
  4. Reports  

### Main Content
- Two-column layout (Controls left, Map/Data right)  
- Responsive collapse to single column for smaller screens  

---

## 2. Upload & Validate Page

### Header & Summary
- Card showing:
  - **Last upload timestamp**
  - **Download latest customer CSV**
  - **OSRM health chip (✅ / ⚠️)**
- Banner reminder:  
  > *Reassigning agents requires Finance clearance.*
- Status indicator:  
  > *Latest validation run: Success / Warning*

### Upload Panel
- Drag-and-drop card for **CSV/XLSX** files  
- Display file name, size, and upload timestamp  
- Helper text:  
  > *Max file size: 50 MB. Accepted formats: CSV, XLSX.*  
- CTA: **Validate Data** (disabled until file uploaded)

### Validation Summary
Accordion sections:
- Missing Coordinates  
- Out-of-Bounds (e.g., 170 records)  
- Duplicate IDs  
- Finance Clearance Needed *(new section)*  

Each section includes:
- Record count badge (with % of dataset)  
- “Download issue report” button  

### Customer Table
- **Columns:** CusId | CusName | City | Zone | Latitude | Longitude | Status  
- **Filters:** City (Jeddah, Riyadh, Dammam…), Zone, Status  
- **Bulk Actions:** *Mark Reviewed*, *Export Selection*  
- **Color Coding:**
  - Errors = Red  
  - Unassigned = Amber  
  - Cleared = Green  

### Validation KPIs
Stats row above the table:
- **Total Customers:** 26,831  
- **Unassigned:** 4,351 (16.2%)  
- **Zones Detected:** 45  
- **Zone Distribution:** Horizontal bar chart

---

## 3. Zoning Workspace

### Layout
- Split-screen:
  - Left (~30%) = Control Panel  
  - Right = Map (~60 vh) + Results Tabs  

### Control Panel
- **City Selector:** Dropdown (Riyadh, Jeddah, Dammam…)  
  > *Depot: Jeddah DC • 21.3447, 39.2054*
- **Target Zones:** Numeric stepper (min 4, max 24)  
  > *Each zone = 1 sales agent.*
- **Zoning Method:** Toggle pills  
  - **Polar:** Rotation offset (0°–90°), min/max customers per sector  
  - **Isochrone:** Thresholds (15/30/45/60 min) editable chips  
  - **Clustering:** Max customers per zone, balance tolerance (default 20%)  
  - **Manual:** “Start Drawing” → activates polygon draw tool  
- **Balancing:** Toggle + tolerance slider (0–40%)  
  > *Transfer log shows customer moves (finance clearance required).*  
- **Actions:**
  - Primary: *Generate Zones*  
  - Secondary: *Reset Parameters*
- **Status Cards:** Solver time, last run timestamp  

### Map Canvas
- **Framework:** React-Leaflet  
- **Layers:** Customers, Existing Zones, New Zones, Depots  
- **Visuals:**
  - Distinct colors for new zones  
  - Centroid pins visible  
  - Manual drawing toolbar  
- **Legend:** Existing / Proposed / Unassigned / Depots  

### Results Tabs
1. **Summary:** Zone ID, Customer Count, Delta %, Avg Distance  
   - Green = within ±20 %, Amber = outside  
2. **Transfers:** Customer moves (From → To, Distance km, Clearance status)  
3. **Downloads:** Summary JSON | Assignments CSV | GeoJSON  

> **Reminder:** Large reassignments trigger Finance clearance — coordinate before publishing.

### Responsive Behavior
Control panel collapses into accordion above map on small screens.

---

## 4. Routing Workspace

### Layout
Same global header/nav as zoning workspace.  
Left = Control Panel; Right = Map + Results Tabs.

### Control Panel
- **Zone Selector:** Searchable dropdown (Zone ID + Customer Count)  
- **Customer Filters:**  
  - Active only  
  - Pending finance clearance  
  - Specific agents  
- **Constraints:**  
  - Max customers per route  
  - Max duration (min)  
  - Max distance (km)  
  - Min customers  
  - Days (SUN–SAT; default SUN–THU + SAT)  
  > *Defaults: 25 customers / 600 min / 50 km*
- **OSRM Health:** Inline pill + tooltip if down  
- **Actions:**  
  - *Optimize Routes* (primary)  
  - *Download Last Run* (secondary)  
- **Summary Widget:** Solver run time, optimal status, vehicles used  

### Map
- Colored route polylines  
- Gradient by sequence + numbered markers  
- Tooltips: CusId & ETA  
- Toggle: Original vs Optimized routes  

### Results Tabs
1. **Route Metrics:**  
   Route ID | Day | Customers | Distance km | Duration min | Violations  
   - Pill badges for violations  
2. **Sequence:**  
   Accordion per route with ordered stops (sequence#, CusId, arrival time)  
3. **Exports:**  
   - customers_with_routes.csv  
   - route_metrics.csv  
   - route_sequences.csv  
   - GeoJSON  

**Alerts**
- Warning ribbon: *“Route JED001_R01 exceeds distance limit by 31.6 km.”*  
- Finance Reminder: *“5 customers require clearance; view list.”*

---

## 5. Reports Section

### Layout
- 2×2 grid on desktop, single column on mobile  

### Report Cards
Each card includes:
- **Title:** customers_with_routes.csv, route_metrics.csv, etc.  
- **Description:** Date/time + record count  
- **Actions:** Download | Open in Explorer | Share  
- **Badges:** Format (CSV/GeoJSON/PDF), file size, last updated  

### Filters & History
- Date range / Run ID filter  
- Search bar for report names  
- Side panel: *Run History* with quick links  

### Empty State
> *Run zoning or routing first to generate reports.*

### Notification Hook
Banner indicating if latest run had warnings or transfer issues.

---

## 6. Health & Notifications

- **Global Toast Area:** Success / error messages (e.g., “OSRM unreachable”)  
- **Status Chip:**  
  - Green = Healthy  
  - Red = Offline  
- **Warning Banner:**  
  Appears on Zoning/Routing pages with recovery instructions if OSRM is down.

---

## 7. General Styling Notes

- Tailwind spacing: 24 px gutters, rounded-lg cards, soft shadows  
- Buttons: Primary = violet/indigo; Secondary = gray  
- Tables: Sticky headers, compact rows  
- Map height: ≈ 60 vh, responsive  
- Tooltips for advanced fields  
- Aesthetic: Clean SaaS dashboard (MUI / Tailwind style)

---

## 8. Deliverables

From **Stitch** or equivalent handoff:
- Responsive multi-page layout  
- Placeholder data accepted (counts, tables, etc.)  
- Components ready for React + Tailwind integration  
- Use **Heroicons** or **Material Icons**

---

## ✅ Final Checklist Alignment
- [x] OSRM health chip in top bar  
- [x] “Start New Upload” CTA confirmed  
- [x] Finance clearance reminders in Upload/Zoning/Routing  
- [x] Validation summary includes Finance Clearance section  
- [x] KPI stats row with accurate mock data  
- [x] File upload includes status + 50 MB limit  
- [x] Saudi locales used for cities  
- [x] Redundant upload cards merged
