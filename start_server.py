#!/usr/bin/env python3
"""Start script for Railway deployment that properly handles PORT environment variable."""

import os
import sys
import subprocess

# Get PORT from environment, default to 8000
port = os.environ.get("PORT", "8000")

# Ensure port is a valid integer
try:
    port_int = int(port)
except ValueError:
    print(f"Warning: Invalid PORT value '{port}', using default 8000", file=sys.stderr)
    port_int = 8000

# Set PYTHONPATH to include src directory
pythonpath = os.environ.get("PYTHONPATH", "")
src_path = os.path.join(os.getcwd(), "src")
if pythonpath:
    os.environ["PYTHONPATH"] = f"{src_path}:{pythonpath}"
else:
    os.environ["PYTHONPATH"] = src_path

# Start uvicorn
cmd = [
    sys.executable,
    "-m",
    "uvicorn",
    "app.main:app",
    "--host",
    "0.0.0.0",
    "--port",
    str(port_int),
    "--workers",
    "2",
]

print(f"Starting server on port {port_int}...", file=sys.stderr)
print(f"PYTHONPATH={os.environ['PYTHONPATH']}", file=sys.stderr)

sys.exit(subprocess.call(cmd))

