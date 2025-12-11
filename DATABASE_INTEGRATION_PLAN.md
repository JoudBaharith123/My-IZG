# 🗄️ Database Integration Plan

## Current State

**Storage:** File-based (CSV/JSON)  
**Database:** Schema ready, client ready, but NOT used  
**Goal:** Save everything to Supabase  

---

## What Needs to Change

### 1. Customer Data Storage

**Current:** `customers_repository.py` reads from CSV  
**New:** Read from Supabase, fallback to CSV  

**Files to update:**
- `src/app/data/customers_repository.py`
- `src/app/api/routes/customers.py` (upload endpoint)

---

### 2. Zone Storage

**Current:** Zones saved to JSON/CSV files  
**New:** Save to `zones` table in Supabase  

**Files to update:**
- `src/app/services/zoning/service.py`
- `src/app/persistence/filesystem.py` (add Supabase option)

---

### 3. Route Storage

**Current:** Routes saved to JSON/CSV files  
**New:** Save to `routes` table in Supabase  

**Files to update:**
- `src/app/services/routing/service.py`
- `src/app/persistence/filesystem.py`

---

## Implementation Strategy

### Phase 1: Customer Data
```python
# customers_repository.py
def get_customers_for_location(city: str):
    # Try Supabase first
    if supabase:
        return get_customers_from_supabase(city)
    # Fallback to CSV
    return get_customers_from_csv(city)
```

### Phase 2: Zone Storage
```python
# zoning/service.py
def process_zoning_request(...):
    # Generate zones
    result = strategy.generate(...)
    
    # Save to Supabase
    if supabase:
        save_zones_to_supabase(result)
    
    # Also save to file (backup)
    save_zones_to_file(result)
```

### Phase 3: Route Storage
```python
# routing/service.py
def optimize_routes(...):
    # Generate routes
    routes = solver.solve(...)
    
    # Save to Supabase
    if supabase:
        save_routes_to_supabase(routes)
    
    # Also save to file
    save_routes_to_file(routes)
```

---

## Database Schema (Already Ready!)

**Tables:**
- ✅ `customers` - Customer master data
- ✅ `zones` - Zone definitions (PostGIS geometry)
- ✅ `routes` - Route assignments
- ✅ `depots` - Distribution centers
- ✅ `reports` - Generated reports

**See:** `supabase/schema.sql`

---

## Migration Steps

### Step 1: Test Connection
```python
from src.app.db.supabase import get_supabase_client
client = get_supabase_client()
if client:
    print("✅ Connected!")
```

### Step 2: Update Customers Repository
- Add Supabase queries
- Keep CSV as fallback
- Test with sample data

### Step 3: Update Zone Storage
- Save zones to database
- Include geometry (PostGIS)
- Link to customers

### Step 4: Update Route Storage
- Save routes to database
- Link to zones
- Store sequence and metrics

---

## Benefits of Database

1. ✅ **Persistent storage** - Data survives restarts
2. ✅ **Multi-user support** - Multiple users can access
3. ✅ **Historical tracking** - See past zone generations
4. ✅ **Better queries** - Fast filtering and search
5. ✅ **Data integrity** - Constraints and validation
6. ✅ **Backup/recovery** - Automatic backups

---

## Next Steps

**After you:**
1. ✅ Push to GitHub
2. ✅ Create Supabase project
3. ✅ Run schema
4. ✅ Create `.env` file

**I will:**
1. ✅ Update `customers_repository.py` to use Supabase
2. ✅ Update zone storage to save to database
3. ✅ Update route storage to save to database
4. ✅ Test end-to-end data flow
5. ✅ Verify data in Supabase dashboard

---

**Ready when you are!** 🎯

