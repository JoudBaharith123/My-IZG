# 🚀 Quick Start Guide

## Start the Application

### Option 1: Use Helper Scripts (Easiest)

**Terminal 1 - Start Backend:**
```bash
cd /root/openai_projects/Binder_intelligent_zone_generator_v1/Intelligent_zone_generator
./start_backend.sh
```

**Terminal 2 - Start Frontend:**
```bash
cd /root/openai_projects/Binder_intelligent_zone_generator_v1/Intelligent_zone_generator/ui
npm run dev
```

### Option 2: Manual Start

**Terminal 1 - Backend:**
```bash
cd /root/openai_projects/Binder_intelligent_zone_generator_v1/Intelligent_zone_generator
source ../.venv/bin/activate
export PYTHONPATH="${PWD}/src:${PYTHONPATH}"
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd /root/openai_projects/Binder_intelligent_zone_generator_v1/Intelligent_zone_generator/ui
npm run dev
```

---

## Access the Application

- **Frontend:** http://localhost:5173 (or URL shown by vite)
- **API Docs:** http://localhost:8000/docs
- **API:** http://localhost:8000/api

---

## What to Test

See **QUICK_TEST_REFERENCE.md** for a 10-minute test guide covering all 5 new features:

1. ✅ **Column Mapping** - Smart CSV/Excel column detection
2. ✅ **Filter Selection** - Choose which columns to use as filters
3. ✅ **View All Customers** - "All Cities" option with performance optimization
4. ✅ **Download Fixes** - Fixed file downloads with toast notifications
5. ✅ **GeoJSON Export** - EasyTerritory format export

---

## Testing Documentation

- **QUICK_TEST_REFERENCE.md** - Fast 10-minute test guide
- **TESTING_GUIDE.md** - Comprehensive testing manual
- **manual_testing/sample_data_custom_columns.csv** - Test data

---

## Troubleshooting

### Backend won't start
```bash
# Reinstall dependencies
cd /root/openai_projects/Binder_intelligent_zone_generator_v1
source .venv/bin/activate
pip install -r Intelligent_zone_generator/requirements.txt
```

### Frontend won't start
```bash
# Reinstall dependencies
cd ui
npm install
```

### Port already in use
```bash
# Backend (8000)
lsof -ti:8000 | xargs kill -9

# Frontend (5173)
lsof -ti:5173 | xargs kill -9
```

---

## Next Steps

1. ✅ Start both servers (see above)
2. ✅ Open http://localhost:5173
3. ✅ Follow **QUICK_TEST_REFERENCE.md**
4. ✅ Report any issues you find

**Happy Testing!** 🧪
