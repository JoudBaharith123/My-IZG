# 📊 DATABASE STATUS

## Current State

### ✅ Database Schema EXISTS
**Location:** `supabase/schema.sql`

**Tables Defined:**
- `customers` - Customer master data
- `zones` - Zone definitions with PostGIS geometry
- `routes` - Route assignments
- `depots` - Distribution center locations
- `reports` - Generated reports

**Features:**
- PostgreSQL 15 + PostGIS extension
- Spatial indexes (GIST)
- Stored procedures for geospatial queries
- Row Level Security (RLS) ready

---

### ✅ Database Client Code EXISTS
**Location:** `src/app/db/supabase.py`

**Features:**
- Supabase client wrapper
- Cached connection
- Example usage patterns
- Optional (returns None if not configured)

---

### ❌ Database NOT ACTIVELY USED
**Current Implementation:** File-based storage

**Storage Method:**
- Customer data: CSV files (`data/Easyterrritory_*.CSV`)
- Zone outputs: JSON + CSV files (`data/outputs/zones_*/`)
- Route outputs: JSON + CSV files (`data/outputs/routes_*/`)
- Depot data: Excel file (`data/dc_locations.xlsx`)

**Code:** `src/app/persistence/filesystem.py` (FileStorage class)

---

## Why No Database?

**From Documentation:**
> "Storage: versioned CSV customer master, JSON+CSV run outputs, 
> JSON/YAML configs (no PostgreSQL per decision)."

**Decision:** Use file-based storage for simplicity during development phase.

---

## Database Configuration

**Environment Variables (Optional):**
```env
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=your_service_role_key
```

**If not set:**
- `get_supabase_client()` returns `None`
- System falls back to file-based storage
- No errors, just uses files

---

## Migration Path

### To Enable Database:

**Step 1:** Set up Supabase/PostgreSQL
```bash
# Create Supabase project
# Or set up PostgreSQL + PostGIS locally
```

**Step 2:** Run schema
```sql
-- Execute supabase/schema.sql
-- Creates all tables, indexes, functions
```

**Step 3:** Configure environment
```env
SUPABASE_URL=your_url
SUPABASE_KEY=your_key
```

**Step 4:** Update data repositories
- Modify `src/app/data/customers_repository.py`
- Replace CSV reading with Supabase queries
- Keep file-based as fallback

---

## Current Data Flow

```
CSV Upload → Parse → In-Memory → Process → File Output
     ↓
  No database
  No persistence
  Stateless API
```

---

## Future Database Flow

```
CSV Upload → Parse → Supabase → Query → Process → Supabase + File Output
     ↓
  Persistent storage
  Historical tracking
  Multi-user support
```

---

## Summary

| Aspect | Status |
|--------|--------|
| **Schema defined** | ✅ Yes (`supabase/schema.sql`) |
| **Client code** | ✅ Yes (`src/app/db/supabase.py`) |
| **Currently used** | ❌ No (file-based) |
| **Can be enabled** | ✅ Yes (set env vars) |
| **Migration needed** | ⏳ Yes (update repositories) |

---

## Recommendation

**Current:** File-based is fine for development/testing  
**Future:** Enable database for:
- Multi-user support
- Historical tracking
- Better query performance
- Data integrity
- Backup/recovery

**To enable:** Just set environment variables and update data loading code!

