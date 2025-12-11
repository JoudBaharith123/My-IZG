# 🚀 Complete Setup Guide: GitHub + Supabase

## 📋 Overview

This guide will help you:
1. ✅ Push project to GitHub
2. ✅ Create Supabase project
3. ✅ Connect Supabase to your repo
4. ✅ Enable database storage

---

## Step 1: Push to GitHub

### Current Status:
- ✅ Repository initialized
- ✅ Remote updated to: `https://github.com/JoudBaharith123/My-IZG.git`

### Commands to Run:

```powershell
# 1. Stage all changes
git add .

# 2. Commit
git commit -m "Complete IZG project: All features implemented"

# 3. Push to GitHub
git push -u origin main
```

**If you get authentication errors:**
- Use GitHub Personal Access Token (not password)
- Or set up SSH keys

---

## Step 2: Create Supabase Project

### Go to Supabase:
1. Visit: https://supabase.com
2. Sign up / Log in
3. Click: **"New Project"**

### Project Settings:
- **Name:** `My-IZG` (or your choice)
- **Database Password:** ⚠️ **SAVE THIS!** You'll need it
- **Region:** Choose closest to you
- **Pricing Plan:** Free tier is fine

### Wait:
- Project creation takes 2-3 minutes
- You'll see a progress indicator

---

## Step 3: Run Database Schema

### In Supabase Dashboard:

1. **Click:** SQL Editor (left sidebar)
2. **Click:** "New Query"
3. **Open:** `supabase/schema.sql` from this project
4. **Copy** entire contents
5. **Paste** into SQL Editor
6. **Click:** "Run" (or Ctrl+Enter)

**This creates:**
- ✅ `customers` table
- ✅ `zones` table (with PostGIS geometry)
- ✅ `routes` table
- ✅ `depots` table
- ✅ `reports` table
- ✅ Indexes and functions

**Verify:**
- Go to: Table Editor
- You should see all 5 tables listed

---

## Step 4: Get Supabase Credentials

### In Supabase Dashboard:

1. **Go to:** Settings → API
2. **Copy these values:**

```
Project URL: https://xxxxx.supabase.co
Service Role Key: eyJhbGc... (long string)
```

**⚠️ Security Note:**
- Service Role Key has **admin access**
- Never commit it to GitHub!
- Keep it in `.env` file only

---

## Step 5: Create Environment File

### In Project Root:

1. **Copy:** `.env.example` to `.env`
2. **Edit:** `.env` file
3. **Add your Supabase credentials:**

```env
# Supabase Configuration
IZG_SUPABASE_URL=https://xxxxx.supabase.co
IZG_SUPABASE_KEY=eyJhbGc...your-service-role-key

# Other settings (already configured)
IZG_API_PREFIX=/api
IZG_FRONTEND_ALLOWED_ORIGINS=http://localhost:5173
IZG_DATA_ROOT=./data
IZG_OSRM_BASE_URL=http://localhost:5000
```

**⚠️ Important:**
- `.env` is in `.gitignore` - won't be committed
- Never share your Service Role Key!

---

## Step 6: Connect Supabase to GitHub (Optional)

### Option A: Supabase GitHub Integration

**Benefits:**
- Automatic database migrations
- Track schema changes in git
- Easy deployments

**Steps:**
1. In Supabase Dashboard: Settings → Integrations
2. Click: "GitHub"
3. Authorize Supabase
4. Select repository: `JoudBaharith123/My-IZG`
5. Enable: "Database Migrations"

**Result:**
- Schema changes tracked in `supabase/migrations/`
- Automatic deployments

### Option B: Manual (Current)

Just use environment variables - no GitHub integration needed.

---

## Step 7: Test Database Connection

### After creating `.env`:

```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Test connection
python -c "from src.app.db.supabase import get_supabase_client; client = get_supabase_client(); print('✅ Connected!' if client else '❌ Check .env file')"
```

**Expected:** `✅ Connected!`

---

## Step 8: Enable Database Storage (Next)

After Supabase is connected, I'll help you:
1. ✅ Update `customers_repository.py` to use Supabase
2. ✅ Save zones to database
3. ✅ Save routes to database
4. ✅ Keep file-based as fallback

**This will be done in next steps!**

---

## 📋 Quick Checklist

### GitHub:
- [ ] Remote updated to your repo ✅
- [ ] Stage files (`git add .`)
- [ ] Commit changes
- [ ] Push to GitHub
- [ ] Verify on GitHub website

### Supabase:
- [ ] Create project
- [ ] Run `supabase/schema.sql`
- [ ] Get credentials (URL + Key)
- [ ] Create `.env` file
- [ ] Test connection

### Next Steps:
- [ ] Update code to use database
- [ ] Test saving data
- [ ] Verify in Supabase dashboard

---

## 🎯 Ready to Start?

**Run these commands now:**

```powershell
# 1. Stage all files
git add .

# 2. Commit
git commit -m "Complete IZG project with all features"

# 3. Push
git push -u origin main
```

**Then:**
1. Create Supabase project
2. Run schema
3. Get credentials
4. Create `.env` file
5. Let me know when done!

**I'll help integrate the database next!** 🎯

