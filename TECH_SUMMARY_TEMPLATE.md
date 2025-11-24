# Intelligent Zone Generator - Tech Summary Template

**Purpose:** Reference document for replicating this stack in similar projects.

---

## Quick Facts

| Component | Technology | Version |
|-----------|------------|---------|
| Frontend | React + TypeScript | 19.1.1 / 5.9.3 |
| Build Tool | Vite | 7.1.7 |
| Styling | Tailwind CSS | 3.4.13 |
| State | TanStack React Query | 5.90.5 |
| Maps | Leaflet + React-Leaflet | 1.9.4 / 5.0.0 |
| Backend | FastAPI + Python | 0.110.0 / 3.11 |
| Optimization | Google OR-Tools | 9.10.4067 |
| Routing Engine | OSRM (Docker) | latest |
| Deployment | Cloudflare Pages | - |
| Data Storage | File-based (CSV/Excel) | - |

---

## 1. UI Design System

### Color Palette
```css
/* Primary Brand */
--primary: #3713ec;        /* Deep purple - buttons, links, accents */

/* Backgrounds */
--bg-light: #f6f6f8;       /* Light mode background */
--bg-dark: #131022;        /* Dark mode background */

/* Grays (Tailwind defaults) */
--gray-100: #f3f4f6;       /* Cards, hover states */
--gray-200: #e5e7eb;       /* Borders */
--gray-500: #6b7280;       /* Muted text */
--gray-900: #111827;       /* Primary text */
```

### Typography
```css
/* Font Family */
font-family: 'Space Grotesk', sans-serif;

/* Import */
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&display=swap');

/* Weights Used */
300 - Light
400 - Regular
500 - Medium
600 - SemiBold
700 - Bold
```

### Border Radius
```css
--radius-default: 0.5rem;  /* 8px - buttons, inputs */
--radius-lg: 1rem;         /* 16px - cards */
--radius-xl: 1.5rem;       /* 24px - modals, large cards */
```

### Tailwind Config (tailwind.config.js)
```javascript
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: '#3713ec',
        'background-light': '#f6f6f8',
        'background-dark': '#131022',
      },
      fontFamily: {
        display: ['"Space Grotesk"', 'sans-serif'],
      },
      borderRadius: {
        DEFAULT: '0.5rem',
        lg: '1rem',
        xl: '1.5rem',
      },
    },
  },
  plugins: [require('@tailwindcss/forms')],
}
```

### Base CSS (index.css)
```css
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&display=swap');

@tailwind base;
@tailwind components;
@tailwind utilities;

html, body, #root {
  height: 100%;
}

body {
  @apply bg-background-light text-gray-900 font-display antialiased;
}

.dark body {
  @apply bg-background-dark text-gray-100;
}
```

---

## 2. Frontend Stack

### package.json Dependencies
```json
{
  "dependencies": {
    "@tanstack/react-query": "^5.90.5",
    "axios": "^1.13.1",
    "clsx": "^2.1.1",
    "leaflet": "^1.9.4",
    "leaflet-draw": "^1.0.4",
    "lucide-react": "^0.548.0",
    "react": "^19.1.1",
    "react-dom": "^19.1.1",
    "react-leaflet": "^5.0.0",
    "react-router-dom": "^7.9.5",
    "tailwind-merge": "^3.3.1"
  },
  "devDependencies": {
    "@eslint/js": "^9.36.0",
    "@tailwindcss/forms": "^0.5.10",
    "@types/leaflet-draw": "^1.0.13",
    "@types/node": "^24.6.0",
    "@types/react": "^19.1.16",
    "@types/react-dom": "^19.1.9",
    "@vitejs/plugin-react": "^5.0.4",
    "autoprefixer": "^10.4.21",
    "eslint": "^9.36.0",
    "postcss": "^8.5.6",
    "tailwindcss": "^3.4.13",
    "typescript": "~5.9.3",
    "vite": "^7.1.7"
  }
}
```

### Scripts
```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "cf-build": "vite build",
    "lint": "eslint .",
    "preview": "vite preview"
  }
}
```

### Key Patterns

#### API Client Setup (api/client.ts)
```typescript
import axios from 'axios';

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
  headers: { 'Content-Type': 'application/json' },
});
```

#### React Query Hook Pattern
```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';

export function useCustomers(filters?: Filters) {
  return useQuery({
    queryKey: ['customers', filters],
    queryFn: () => api.get('/customers/locations', { params: filters }).then(r => r.data),
  });
}

export function useUploadFile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (formData: FormData) => api.post('/customers/upload', formData),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['customers'] }),
  });
}
```

#### Component Structure
```
src/
├── api/              # Axios client config
├── components/       # Reusable UI components
│   ├── layout/       # App shell, navigation
│   └── ...           # Feature components
├── hooks/            # React Query hooks
├── pages/            # Route-level components
├── config/           # Constants, viewports
├── utils/            # Helpers (geometry, colors)
├── App.tsx           # Routes definition
├── main.tsx          # Entry point
└── index.css         # Tailwind directives
```

---

## 3. Backend Stack

### requirements.txt
```
fastapi==0.110.0
uvicorn[standard]==0.29.0
pydantic==2.6.0
pydantic-settings==2.2.0
numpy==1.26.0
scikit-learn==1.4.0
shapely==2.0.3
httpx==0.27.0
openpyxl==3.1.2
ortools==9.10.4067
```

### FastAPI App Structure
```python
# src/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

def create_app() -> FastAPI:
    app = FastAPI(title="App Name")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router, prefix="/api")
    app.include_router(feature.router, prefix="/api")
    return app

app = create_app()
```

### Configuration Pattern (config.py)
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "Intelligent Zone Generator"
    api_prefix: str = "/api"
    data_root: str = "./data"
    osrm_base_url: str | None = None

    class Config:
        env_prefix = "IZG_"  # IZG_APP_NAME, IZG_DATA_ROOT, etc.

settings = Settings()
```

### Project Structure
```
src/app/
├── main.py           # FastAPI app factory
├── config.py         # Pydantic Settings
├── api/
│   └── routes/       # API routers
├── services/         # Business logic
├── schemas/          # Pydantic models
├── models/           # Domain models
├── data/             # Repository layer
└── persistence/      # File storage
```

---

## 4. Deployment (Cloudflare Pages)

### Build Command
```bash
cd ui && npm run cf-build
```

### Output Directory
```
ui/dist
```

### Environment Variables (Cloudflare Dashboard)
```
VITE_API_URL=https://api.your-domain.com
```

### vite.config.ts
```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'dist',
  },
});
```

---

## 5. Docker Setup

### docker-compose.yml
```yaml
version: "3.9"

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: app-api
    command: uvicorn src.app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - .:/app
    environment:
      - IZG_DATA_ROOT=/app/data
      - IZG_OSRM_BASE_URL=http://osrm:5000
    ports:
      - "8000:8000"
    depends_on:
      - osrm

  osrm:
    image: ghcr.io/project-osrm/osrm-backend:latest
    container_name: app-osrm
    command: osrm-routed --algorithm mld /data/region.osrm
    volumes:
      - ./osrm:/data
    ports:
      - "5000:5000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 5s
      retries: 5
```

### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY data/ data/

EXPOSE 8000

CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 6. Supabase Integration (Template)

**Note:** This project uses file-based storage. For Supabase PostgreSQL:

### Setup
```bash
npm install @supabase/supabase-js
```

### Client (supabase.ts)
```typescript
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

export const supabase = createClient(supabaseUrl, supabaseKey);
```

### Environment Variables
```
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
```

### Python Backend (supabase-py)
```python
# requirements.txt
supabase==2.0.0

# config.py
class Settings(BaseSettings):
    supabase_url: str
    supabase_key: str

# db.py
from supabase import create_client
from .config import settings

supabase = create_client(settings.supabase_url, settings.supabase_key)
```

---

## 7. Key UI Components Reference

### Navigation (Pill Buttons)
```tsx
<nav className="flex gap-2 bg-gray-100 p-1 rounded-full">
  <NavLink
    to="/upload"
    className={({ isActive }) =>
      clsx(
        'px-4 py-2 rounded-full text-sm font-medium transition',
        isActive
          ? 'bg-primary text-white'
          : 'text-gray-600 hover:text-gray-900'
      )
    }
  >
    Upload
  </NavLink>
</nav>
```

### Status Badge
```tsx
<span className={clsx(
  'px-2 py-1 rounded-full text-xs font-medium',
  status === 'online' && 'bg-green-100 text-green-800',
  status === 'offline' && 'bg-red-100 text-red-800',
  status === 'pending' && 'bg-yellow-100 text-yellow-800'
)}>
  {status}
</span>
```

### Card Component
```tsx
<div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
  <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
  <p className="mt-2 text-gray-600">{description}</p>
</div>
```

### Map Container
```tsx
<div className="h-[55vh] rounded-lg border border-gray-200 overflow-hidden">
  <MapContainer center={[lat, lng]} zoom={10}>
    <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
  </MapContainer>
</div>
```

---

## 8. Development Ports

| Service | Port | URL |
|---------|------|-----|
| Frontend (Vite) | 5173 | http://localhost:5173 |
| Backend (FastAPI) | 8000 | http://localhost:8000 |
| OSRM Routing | 5000 | http://localhost:5000 |
| API Docs | 8000 | http://localhost:8000/docs |

---

## 9. File Structure Template

```
project/
├── ui/                          # Frontend
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── pages/
│   │   ├── config/
│   │   ├── utils/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── index.css
│   ├── package.json
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   └── vite.config.ts
│
├── src/app/                     # Backend
│   ├── main.py
│   ├── config.py
│   ├── api/routes/
│   ├── services/
│   ├── schemas/
│   └── models/
│
├── data/                        # Data files
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## 10. Quick Start Commands

```bash
# Frontend development
cd ui && npm install && npm run dev

# Backend development
pip install -r requirements.txt
uvicorn src.app.main:app --reload --port 8000

# Docker (full stack)
docker-compose up -d

# Build for Cloudflare Pages
cd ui && npm run cf-build
```

---

**Note:** This project does NOT use Supabase - it uses file-based CSV/Excel storage. Section 6 provides a template for adding Supabase if needed.
