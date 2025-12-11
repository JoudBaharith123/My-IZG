# Intelligent Zone Generator (IZG)

An internal logistics and sales planning platform that ingests customer master data and produces balanced delivery zones and optimized visit routes.

## 🚀 Features

- **Multiple Zoning Strategies:**
  - Polar sectors
  - OSRM isochrones
  - Constrained clustering (K-Means)
  - Manual polygon drawing

- **Route Optimization:**
  - OR-Tools VRP solver integration
  - Distance and time constraints
  - Workload balancing

- **Data Management:**
  - CSV/Excel file upload
  - Customer data validation
  - Geographic boundary validation
  - City-specific filtering

## 🛠️ Tech Stack

- **Backend:** FastAPI (Python 3.11+)
- **Frontend:** React + TypeScript + Vite + Tailwind CSS
- **Database:** Supabase (PostgreSQL + PostGIS)
- **Maps:** Leaflet.js
- **Optimization:** OR-Tools, scikit-learn

## 📦 Installation

### Prerequisites
- Python 3.11+
- Node.js 18+
- Supabase account (for database)

### Backend Setup

```powershell
# Create virtual environment
python -m venv .venv

# Activate (Windows)
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Create .env file (copy from .env.example)
# Add your Supabase credentials

# Start backend
python -m uvicorn app.main:app --reload --port 8001
```

### Frontend Setup

```powershell
cd ui

# Install dependencies
npm install

# Start dev server
npm run dev
```

## 🔧 Configuration

Create `.env` file in root directory:

```env
# Supabase (Required for database storage)
IZG_SUPABASE_URL=https://your-project.supabase.co
IZG_SUPABASE_KEY=your-service-role-key

# API
IZG_API_PREFIX=/api
IZG_FRONTEND_ALLOWED_ORIGINS=http://localhost:5173

# Data
IZG_DATA_ROOT=./data
IZG_CUSTOMER_FILE=./data/Easyterrritory_26831_29_oct_2025.CSV

# OSRM
IZG_OSRM_BASE_URL=http://localhost:5000
```

## 📊 Database Setup

1. Create Supabase project at https://supabase.com
2. Run `supabase/schema.sql` in Supabase SQL Editor
3. Get credentials from Settings → API
4. Add to `.env` file

See `SETUP_GUIDE.md` for detailed instructions.

## 🎯 Usage

1. Upload customer CSV file
2. Select city
3. Choose zoning method
4. Configure parameters
5. Generate zones
6. View on map
7. Download results

## 📝 License

Internal use only - Binder's Business

