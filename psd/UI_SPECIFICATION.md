# UI Specification & Tech Stack

## Technology Stack (Simplest + Most Effective)

### Frontend
- **HTML5** - Single page app (index.html)
- **Vanilla JavaScript (ES6+)** - No frameworks, native fetch API
- **Tailwind CSS (CDN)** - Utility-first styling, no build step
- **Leaflet.js 1.9** - Map library
- **Leaflet.draw** - Drawing tools plugin
- **Leaflet.markercluster** - Point clustering
- **Chart.js** - Dashboard charts (optional)

### Backend
- **FastAPI 0.104+** - Modern Python API framework
- **Python 3.11+** - Core language
- **uvicorn** - ASGI server
- **SQLAlchemy 2.0** - ORM
- **Pydantic** - Data validation

### Database
- **PostgreSQL 15** - Relational database
- **PostGIS 3.3** - Spatial extension

### Optimization
- **OR-Tools 9.7+** - VRP solver (Google)
- **scikit-learn 1.3+** - K-Means clustering
- **pandas** - Data manipulation
- **numpy** - Numeric operations

### Routing Engine
- **OSRM (Docker)** - Routing engine
- **OSM Saudi Arabia Data** - Road network

### Deployment
- **Ubuntu 22.04 LTS** - OS
- **Nginx** - Reverse proxy
- **systemd** - Service management
- **Docker Compose** - OSRM container

### No Build Tools Required
- Pure HTML/CSS/JS served directly
- No npm, webpack, or bundlers
- CDN for all libraries

---

## UI Structure

```
/var/www/zone-generator/
├── index.html              # Main app
├── css/
│   └── custom.css         # Additional styles
├── js/
│   ├── app.js             # Main app logic
│   ├── map.js             # Map initialization
│   ├── zones.js           # Zone creation logic
│   ├── routes.js          # Route optimization
│   ├── data.js            # Data management
│   └── utils.js           # Helper functions
└── assets/
    ├── icons/             # Tool icons
    └── logo.png           # App logo
```

---

## Layout Design

### Main Interface (index.html)

```
┌─────────────────────────────────────────────────────────────┐
│  [Logo] Intelligent Zone Generator      [Settings] [Export] │ Header (60px)
├──────────┬──────────────────────────────────────┬───────────┤
│          │                                      │           │
│  Tools   │                                      │  Layers   │
│  & Menu  │                                      │  & Props  │
│  (280px) │         MAP CANVAS                   │  (320px)  │
│          │         (Leaflet)                    │           │
│          │                                      │           │
│          │                                      │           │
│          │                                      │           │
├──────────┴──────────────────────────────────────┴───────────┤
│  Status Bar: [Zone Count] [Customer Count] [Coordinates]    │ (30px)
└─────────────────────────────────────────────────────────────┘
```

### Responsive Breakpoints
- Desktop: >1200px (3-column layout)
- Tablet: 768-1200px (2-column, collapsible sidebars)
- Mobile: <768px (full-width map, drawer panels)

---

## Component Specifications

### 1. Header Bar

**HTML Structure**:
```html
<header class="flex items-center justify-between px-4 py-3 bg-blue-600 text-white">
  <div class="flex items-center gap-4">
    <img src="assets/logo.png" class="h-8" alt="Logo">
    <h1 class="text-xl font-semibold">Intelligent Zone Generator</h1>
  </div>
  <nav class="flex gap-2">
    <button class="btn-header">Upload Data</button>
    <button class="btn-header">Settings</button>
    <button class="btn-header">Export</button>
  </nav>
</header>
```

**Styling** (Tailwind classes):
- Background: `bg-blue-600`
- Text: `text-white text-xl font-semibold`
- Buttons: `px-4 py-2 bg-blue-700 hover:bg-blue-800 rounded`

---

### 2. Left Sidebar - Tools Panel

**Sections**:

#### 2.1 Data Management
```html
<div class="panel">
  <h3 class="panel-title">Data Management</h3>
  <button onclick="uploadData()" class="btn-primary">
    📁 Upload Customers
  </button>
  <button onclick="exportData()" class="btn-secondary">
    📥 Export Data
  </button>
</div>
```

#### 2.2 Zone Creation Tools
```html
<div class="panel">
  <h3 class="panel-title">Create Zones</h3>
  <button onclick="createPolarZones()" class="btn-tool">
    🧭 Polar Sectors
  </button>
  <button onclick="createIsochrones()" class="btn-tool">
    ⏱️ Travel Time Zones
  </button>
  <button onclick="clusterZones()" class="btn-tool">
    🎯 Geographic Clustering
  </button>
  <button onclick="drawManualZone()" class="btn-tool">
    ✏️ Draw Manually
  </button>
</div>
```

#### 2.3 Route Optimization
```html
<div class="panel">
  <h3 class="panel-title">Route Optimization</h3>
  <select id="zone-select" class="input-select">
    <option>Select Zone...</option>
  </select>
  <button onclick="optimizeRoutes()" class="btn-primary">
    🚚 Optimize Routes
  </button>
</div>
```

**Panel Styling**:
```css
.panel {
  @apply bg-white p-4 mb-4 rounded-lg shadow;
}
.panel-title {
  @apply text-lg font-semibold mb-3 text-gray-700;
}
.btn-tool {
  @apply w-full text-left px-4 py-2 mb-2 bg-gray-100 hover:bg-gray-200 rounded;
}
```

---

### 3. Map Canvas (Center)

**Leaflet Initialization**:
```javascript
const map = L.map('map', {
  center: [24.7136, 46.6753], // Riyadh
  zoom: 6,
  minZoom: 5,
  maxZoom: 18
});

// Base layer
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '© OpenStreetMap contributors'
}).addTo(map);
```

**Layer Groups**:
```javascript
const layers = {
  customers: L.layerGroup().addTo(map),
  zones: L.layerGroup().addTo(map),
  routes: L.layerGroup().addTo(map),
  dc: L.layerGroup().addTo(map)
};
```

**Controls**:
- Zoom: Default Leaflet controls (top-left)
- Scale: `L.control.scale().addTo(map)`
- Search: Nominatim geocoder (top-right)
- Drawing: Leaflet.draw toolbar (left side)

---

### 4. Right Sidebar - Layers & Properties

#### 4.1 Layer Control Panel
```html
<div class="panel">
  <h3 class="panel-title">Map Layers</h3>
  
  <div class="layer-item">
    <input type="checkbox" id="layer-customers" checked>
    <label>👥 Customers (1,234)</label>
    <input type="range" min="0" max="100" value="100" class="opacity-slider">
  </div>
  
  <div class="layer-item">
    <input type="checkbox" id="layer-zones" checked>
    <label>📍 Zones (8)</label>
    <input type="range" min="0" max="100" value="80" class="opacity-slider">
  </div>
  
  <div class="layer-item">
    <input type="checkbox" id="layer-routes">
    <label>🚚 Routes (24)</label>
    <input type="range" min="0" max="100" value="100" class="opacity-slider">
  </div>
</div>
```

#### 4.2 Properties Panel (Dynamic)
```html
<div id="properties-panel" class="panel">
  <h3 class="panel-title">Properties</h3>
  <div id="property-content">
    <!-- Dynamically populated based on selection -->
  </div>
</div>
```

**Example: Zone Properties**
```html
<div class="property-section">
  <label>Zone ID</label>
  <input type="text" value="RIY001" disabled class="input-field">
  
  <label>Zone Name</label>
  <input type="text" value="Riyadh Central" class="input-field">
  
  <label>Customer Count</label>
  <div class="stat-value">549</div>
  
  <label>Total Revenue</label>
  <div class="stat-value">2,450,000 SAR</div>
  
  <button class="btn-danger">Delete Zone</button>
</div>
```

---

### 5. Modals & Dialogs

#### 5.1 File Upload Modal
```html
<div id="upload-modal" class="modal hidden">
  <div class="modal-content">
    <h2 class="modal-title">Upload Customer Data</h2>
    
    <div class="dropzone" id="dropzone">
      <p>Drag & drop Excel/CSV file here</p>
      <p class="text-sm text-gray-500">or</p>
      <button class="btn-secondary">Browse Files</button>
      <input type="file" id="file-input" hidden accept=".xlsx,.csv">
    </div>
    
    <div id="upload-progress" class="hidden">
      <div class="progress-bar">
        <div id="progress-fill" class="progress-fill"></div>
      </div>
      <p id="progress-text">Uploading... 45%</p>
    </div>
    
    <div id="validation-results" class="hidden">
      <h3>Validation Results</h3>
      <ul id="validation-list"></ul>
    </div>
    
    <div class="modal-footer">
      <button onclick="closeModal()" class="btn-secondary">Cancel</button>
      <button onclick="confirmUpload()" class="btn-primary">Confirm</button>
    </div>
  </div>
</div>
```

**Modal Styling**:
```css
.modal {
  @apply fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50;
}
.modal-content {
  @apply bg-white rounded-lg p-6 max-w-lg w-full max-h-screen overflow-y-auto;
}
.modal-title {
  @apply text-2xl font-bold mb-4;
}
.modal-footer {
  @apply flex justify-end gap-2 mt-6;
}
```

#### 5.2 Polar Sectors Wizard
```html
<div id="polar-modal" class="modal hidden">
  <div class="modal-content">
    <h2 class="modal-title">Create Polar Sectors</h2>
    
    <label>Distribution Center</label>
    <input type="text" id="dc-coords" placeholder="24.7136, 46.6753" class="input-field">
    <button onclick="pickFromMap()" class="btn-secondary text-sm">Pick from Map</button>
    
    <label>Number of Sectors</label>
    <input type="range" id="sector-count" min="4" max="24" value="12" class="range-slider">
    <span id="sector-value">12</span>
    
    <label>Filter Customers</label>
    <select id="area-filter" class="input-select">
      <option value="">All Areas</option>
      <option value="RIYADH">RIYADH</option>
      <option value="Jeddah">Jeddah</option>
    </select>
    
    <div class="modal-footer">
      <button onclick="closeModal()" class="btn-secondary">Cancel</button>
      <button onclick="previewPolarZones()" class="btn-secondary">Preview</button>
      <button onclick="savePolarZones()" class="btn-primary">Create Zones</button>
    </div>
  </div>
</div>
```

#### 5.3 Route Optimization Dialog
```html
<div id="optimize-modal" class="modal hidden">
  <div class="modal-content">
    <h2 class="modal-title">Optimize Routes - Zone RIY001</h2>
    
    <div class="grid grid-cols-2 gap-4">
      <div>
        <label>Max Customers per Route</label>
        <input type="number" value="25" class="input-field">
      </div>
      <div>
        <label>Max Distance (km)</label>
        <input type="number" value="50" class="input-field">
      </div>
      <div>
        <label>Max Duration (min)</label>
        <input type="number" value="600" class="input-field">
      </div>
      <div>
        <label>Solver Time Limit (sec)</label>
        <input type="number" value="30" class="input-field">
      </div>
    </div>
    
    <div id="optimization-progress" class="hidden mt-4">
      <div class="spinner"></div>
      <p>Optimizing routes... This may take 30-60 seconds</p>
    </div>
    
    <div id="optimization-results" class="hidden mt-4">
      <h3>Results</h3>
      <table class="results-table">
        <thead>
          <tr>
            <th>Route</th>
            <th>Customers</th>
            <th>Distance</th>
            <th>Time</th>
            <th>Day</th>
          </tr>
        </thead>
        <tbody id="results-tbody"></tbody>
      </table>
    </div>
    
    <div class="modal-footer">
      <button onclick="closeModal()" class="btn-secondary">Cancel</button>
      <button onclick="startOptimization()" class="btn-primary">Optimize</button>
    </div>
  </div>
</div>
```

---

### 6. Map Feature Styling

#### 6.1 Customer Points
```javascript
function styleCustomerPoint(feature) {
  const areaColors = {
    'RIYADH': '#3b82f6',    // blue
    'Jeddah': '#ef4444',    // red
    'Makkah': '#10b981',    // green
    'Dammam': '#f59e0b'     // orange
  };
  
  return {
    radius: 6,
    fillColor: areaColors[feature.properties.area] || '#6b7280',
    color: '#fff',
    weight: 1,
    opacity: 1,
    fillOpacity: 0.8
  };
}
```

#### 6.2 Zone Polygons
```javascript
function styleZone(feature) {
  const zoneColors = [
    '#fca5a5', '#fdba74', '#fcd34d', '#a7f3d0',
    '#a5f3fc', '#bfdbfe', '#ddd6fe', '#f9a8d4'
  ];
  
  return {
    fillColor: zoneColors[feature.properties.zone_index % 8],
    weight: 2,
    opacity: 1,
    color: '#334155',
    fillOpacity: 0.3
  };
}
```

#### 6.3 Route Lines
```javascript
function styleRoute(feature) {
  const dayColors = {
    'SUN': '#ef4444',
    'MON': '#f97316',
    'TUE': '#eab308',
    'WED': '#22c55e',
    'THU': '#06b6d4',
    'SAT': '#8b5cf6'
  };
  
  return {
    color: dayColors[feature.properties.route_day],
    weight: 3,
    opacity: 0.7,
    dashArray: '5, 5'
  };
}
```

---

### 7. Interactive States

#### Hover Effects
```css
.btn-primary:hover {
  @apply bg-blue-700 shadow-lg;
}

.layer-item:hover {
  @apply bg-gray-50;
}

/* Map feature hover */
.leaflet-interactive:hover {
  stroke-width: 3px;
  stroke: #1e293b;
}
```

#### Selected State
```css
.zone-selected {
  stroke: #0ea5e9 !important;
  stroke-width: 4px !important;
  fill-opacity: 0.5 !important;
}

.btn-active {
  @apply bg-blue-700 ring-2 ring-blue-300;
}
```

#### Loading State
```html
<div class="spinner">
  <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
</div>
```

---

### 8. Color Palette

```css
:root {
  /* Primary */
  --color-primary: #2563eb;
  --color-primary-hover: #1d4ed8;
  
  /* Secondary */
  --color-secondary: #64748b;
  --color-secondary-hover: #475569;
  
  /* Success */
  --color-success: #22c55e;
  
  /* Warning */
  --color-warning: #f59e0b;
  
  /* Error */
  --color-error: #ef4444;
  
  /* Neutrals */
  --color-gray-50: #f9fafb;
  --color-gray-100: #f3f4f6;
  --color-gray-700: #374151;
  
  /* Zone Colors (8 distinct) */
  --zone-1: #fca5a5;
  --zone-2: #fdba74;
  --zone-3: #fcd34d;
  --zone-4: #a7f3d0;
  --zone-5: #a5f3fc;
  --zone-6: #bfdbfe;
  --zone-7: #ddd6fe;
  --zone-8: #f9a8d4;
}
```

---

### 9. Typography

```css
/* Font: System UI Stack (no external fonts) */
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 
               Roboto, 'Helvetica Neue', Arial, sans-serif;
}

/* Scale */
.text-xs { font-size: 0.75rem; }   /* 12px */
.text-sm { font-size: 0.875rem; }  /* 14px */
.text-base { font-size: 1rem; }    /* 16px */
.text-lg { font-size: 1.125rem; }  /* 18px */
.text-xl { font-size: 1.25rem; }   /* 20px */
.text-2xl { font-size: 1.5rem; }   /* 24px */

/* Weights */
.font-normal { font-weight: 400; }
.font-semibold { font-weight: 600; }
.font-bold { font-weight: 700; }
```

---

### 10. Reusable Components

#### Button Classes
```css
.btn-primary {
  @apply px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 
         transition duration-150 ease-in-out;
}

.btn-secondary {
  @apply px-4 py-2 bg-gray-200 text-gray-800 rounded hover:bg-gray-300;
}

.btn-danger {
  @apply px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700;
}

.btn-sm {
  @apply px-2 py-1 text-sm;
}
```

#### Input Classes
```css
.input-field {
  @apply w-full px-3 py-2 border border-gray-300 rounded 
         focus:outline-none focus:ring-2 focus:ring-blue-500;
}

.input-select {
  @apply w-full px-3 py-2 border border-gray-300 rounded bg-white;
}

.range-slider {
  @apply w-full;
}
```

#### Card/Panel
```css
.card {
  @apply bg-white rounded-lg shadow p-6 mb-4;
}
```

---

### 11. Responsive Design

```css
/* Mobile First */
@media (max-width: 767px) {
  .sidebar {
    @apply fixed inset-y-0 left-0 w-64 transform -translate-x-full 
           transition-transform z-40;
  }
  
  .sidebar.open {
    @apply translate-x-0;
  }
  
  .map-container {
    @apply w-full;
  }
}

/* Tablet */
@media (min-width: 768px) and (max-width: 1199px) {
  .sidebar {
    @apply w-64;
  }
}

/* Desktop */
@media (min-width: 1200px) {
  .sidebar-left {
    @apply w-80;
  }
  
  .sidebar-right {
    @apply w-96;
  }
}
```

---

### 12. Accessibility

```html
<!-- ARIA Labels -->
<button aria-label="Create polar sectors" class="btn-tool">
  🧭 Polar Sectors
</button>

<!-- Keyboard Navigation -->
<div role="tablist">
  <button role="tab" tabindex="0">Zones</button>
  <button role="tab" tabindex="-1">Routes</button>
</div>

<!-- Focus Indicators -->
<style>
  *:focus {
    @apply outline-none ring-2 ring-blue-500 ring-offset-2;
  }
</style>
```

---

### 13. CDN Links (index.html <head>)

```html
<!-- Tailwind CSS -->
<script src="https://cdn.tailwindcss.com"></script>

<!-- Leaflet -->
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>

<!-- Leaflet Draw -->
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet.draw/1.0.4/leaflet.draw.css" />
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet.draw/1.0.4/leaflet.draw.js"></script>

<!-- Leaflet MarkerCluster -->
<link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css" />
<link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css" />
<script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>

<!-- Chart.js (optional) -->
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js"></script>
```

---

## JavaScript API Integration Pattern

```javascript
// Utility: API Call
async function apiCall(endpoint, method = 'GET', body = null) {
  const options = {
    method,
    headers: { 'Content-Type': 'application/json' }
  };
  
  if (body) options.body = JSON.stringify(body);
  
  const response = await fetch(`http://localhost:8000${endpoint}`, options);
  if (!response.ok) throw new Error(await response.text());
  return await response.json();
}

// Example: Load Customers
async function loadCustomers() {
  try {
    const data = await apiCall('/api/customers?isactive=1');
    displayCustomersOnMap(data.customers);
  } catch (error) {
    showError('Failed to load customers: ' + error.message);
  }
}

// Example: Create Polar Zones
async function savePolarZones() {
  const payload = {
    dc_coords: [24.7136, 46.6753],
    num_sectors: 12,
    customer_filter: { area: 'RIYADH' }
  };
  
  try {
    const result = await apiCall('/api/zones/polar', 'POST', payload);
    displayZonesOnMap(result.zones);
    showSuccess(`Created ${result.zones.length} zones`);
  } catch (error) {
    showError('Failed to create zones: ' + error.message);
  }
}
```

---

## Performance Optimizations

1. **Lazy Load Layers**: Only fetch data in viewport bounds
2. **Marker Clustering**: Use Leaflet.markercluster for >1000 points
3. **Debounce User Input**: 300ms delay on search/filter
4. **Canvas Renderer**: Use L.canvas() for large datasets
5. **Pagination**: Load customers in batches of 1000
6. **WebSocket (Optional)**: Real-time progress updates for long operations

---

## Summary

**Zero Build Setup**:
- Direct HTML/CSS/JS files
- All libraries from CDN
- No npm, webpack, or bundlers
- Deploy directly to Nginx static directory

**Why This Stack**:
- **Fast Development**: No build configuration
- **Simple Deployment**: Copy files to server
- **Easy Debugging**: No transpilation, native browser tools
- **Minimal Dependencies**: Only essential libraries
- **High Performance**: Vanilla JS is faster than frameworks
- **Easy Maintenance**: Standard web technologies
