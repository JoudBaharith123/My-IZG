# 🚀 GitHub & Supabase Setup Guide

## Step 1: Prepare Repository for GitHub

### Current Status
✅ Repository already initialized  
✅ Connected to remote (check with `git remote -v`)  

### Files to Commit

**Important files:**
- ✅ All source code (`src/`, `ui/`)
- ✅ Configuration files (`requirements.txt`, `package.json`)
- ✅ Schema files (`supabase/schema.sql`)
- ✅ Documentation (`docs/`, `psd/`)

**Excluded (in .gitignore):**
- ❌ `.env` files (sensitive)
- ❌ `data/outputs/` (generated files)
- ❌ `data/uploads/` (user uploads)
- ❌ `.venv/` (virtual environment)
- ❌ Temporary `.md` files

---

## Step 2: Push to GitHub

### Commands to Run:

```powershell
# 1. Check current remote
git remote -v

# 2. If remote is different, update it:
git remote set-url origin https://github.com/JoudBaharith123/My-IZG.git

# 3. Stage all changes
git add .

# 4. Commit changes
git commit -m "Initial commit: Intelligent Zone Generator with all features"

# 5. Push to GitHub
git push -u origin main
```

**Note:** If you get authentication errors, you may need to:
- Use GitHub Personal Access Token instead of password
- Or set up SSH keys

---

## Step 3: Create Supabase Project

### Steps:

1. **Go to:** https://supabase.com
2. **Sign up / Log in**
3. **Click:** "New Project"
4. **Fill in:**
   - Project name: `My-IZG` (or your choice)
   - Database password: (save this!)
   - Region: Choose closest to you
   - Pricing: Free tier is fine for development

5. **Wait for project to be created** (2-3 minutes)

---

## Step 4: Run Database Schema

### In Supabase Dashboard:

1. **Go to:** SQL Editor (left sidebar)
2. **Click:** "New Query"
3. **Copy contents** of `supabase/schema.sql`
4. **Paste** into editor
5. **Click:** "Run" (or press Ctrl+Enter)

**This creates:**
- ✅ All tables (customers, zones, routes, depots, reports)
- ✅ PostGIS extension
- ✅ Indexes for performance
- ✅ Stored procedures for geospatial queries

---

## Step 5: Get Supabase Credentials

### In Supabase Dashboard:

1. **Go to:** Settings → API
2. **Copy:**
   - **Project URL:** `https://xxxxx.supabase.co`
   - **Service Role Key:** `eyJhbGc...` (long string)

**⚠️ Important:** Service Role Key has admin access - keep it secret!

---

## Step 6: Connect Supabase to GitHub (Optional)

### Option A: Supabase GitHub Integration

1. **In Supabase Dashboard:**
   - Go to: Settings → Integrations
   - Click: "GitHub"
   - Authorize Supabase
   - Select repository: `JoudBaharith123/My-IZG`

**Benefits:**
- Automatic migrations
- Database changes tracked in git
- Easy deployments

### Option B: Manual Connection (Current)

Just use environment variables (no GitHub integration needed)

---

## Step 7: Configure Environment Variables

### Create `.env` file (DO NOT commit this!):

```env
# Supabase Configuration
IZG_SUPABASE_URL=https://xxxxx.supabase.co
IZG_SUPABASE_KEY=eyJhbGc...your-service-role-key

# Other settings
IZG_API_PREFIX=/api
IZG_FRONTEND_ALLOWED_ORIGINS=http://localhost:5173
IZG_DATA_ROOT=./data
IZG_OSRM_BASE_URL=http://localhost:5000
```

**Location:** Root directory (same as `requirements.txt`)

**⚠️ Security:** `.env` is in `.gitignore` - never commit it!

---

## Step 8: Update Code to Use Database

### Current Status:
- ✅ Database schema ready
- ✅ Supabase client code ready
- ❌ Data repositories still use CSV files

### Next Steps (I'll help with this):
1. Update `customers_repository.py` to use Supabase
2. Update zone storage to save to database
3. Keep file-based as fallback

---

## Step 9: Test Database Connection

### After setting up `.env`:

```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Test Supabase connection
python -c "from src.app.db.supabase import get_supabase_client; client = get_supabase_client(); print('✅ Connected!' if client else '❌ Not configured')"
```

**Expected:** `✅ Connected!`

---

## 📋 Checklist

### GitHub Setup:
- [ ] Update remote URL to `https://github.com/JoudBaharith123/My-IZG.git`
- [ ] Stage all files (`git add .`)
- [ ] Commit changes
- [ ] Push to GitHub
- [ ] Verify on GitHub website

### Supabase Setup:
- [ ] Create Supabase project
- [ ] Run `supabase/schema.sql` in SQL Editor
- [ ] Get Project URL and Service Role Key
- [ ] Create `.env` file with credentials
- [ ] Test connection

### Code Updates (Next):
- [ ] Update customers repository to use Supabase
- [ ] Update zone storage to use Supabase
- [ ] Test data saving to database
- [ ] Verify data appears in Supabase dashboard

---

## 🎯 Quick Start Commands

```powershell
# 1. Update remote
git remote set-url origin https://github.com/JoudBaharith123/My-IZG.git

# 2. Stage and commit
git add .
git commit -m "Complete IZG project with all features"

# 3. Push
git push -u origin main

# 4. After Supabase setup, create .env:
# Copy .env.example to .env
# Add your Supabase credentials
```

---

## ✅ Status

**Ready to push:** ✅ Yes  
**Supabase ready:** ⏳ After you create project  
**Database integration:** ⏳ Next step (I'll help)  

---

**Let me know when you've:**
1. ✅ Pushed to GitHub
2. ✅ Created Supabase project
3. ✅ Run the schema

**Then I'll help integrate the database!** 🎯

