# Data Storage & Output Conventions

## Directory Layout

```
data/
├── Easyterrritory_26831_29_oct_2025.CSV   # Customer master dataset
├── dc_locations.xlsx                       # Depot coordinates
└── outputs/
    ├── zones_<method>_<timestamp>/         # Zoning runs
    │   ├── summary.json
    │   └── assignments.csv
    └── routes_<zone>_<timestamp>/          # Routing runs
        ├── summary.json
        └── assignments.csv
```

## Output Files

- `summary.json`: serialized response (zoning or routing) with metadata and metrics.
- `assignments.csv`: per-customer row for zones or per-stop row for routes.

## Run Lifecycle

- Each zoning or routing execution creates a timestamped directory (UTC, `YYYYMMDDTHHMMSSZ`).
- Files are written via `FileStorage` abstraction (`src/app/persistence/filesystem.py`).

## Data Retention

- Local development: directories remain under `data/outputs/`; clean up manually as needed.
- Production: ensure `/mnt/ephemeral/data/outputs/` is included in nightly backups.
