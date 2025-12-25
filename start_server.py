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
# Get absolute path to src directory
cwd = os.getcwd()
src_path = os.path.join(cwd, "src")
# Make sure src directory exists
if not os.path.isdir(src_path):
    # Try alternative: if we're in /app, src should be at /app/src
    # If that doesn't work, try current directory structure
    if os.path.isdir("src"):
        src_path = os.path.abspath("src")
    else:
        print(f"Warning: src directory not found at {src_path}", file=sys.stderr)
        src_path = cwd  # Fallback to current directory

if pythonpath:
    os.environ["PYTHONPATH"] = f"{src_path}:{pythonpath}"
else:
    os.environ["PYTHONPATH"] = src_path

# Start uvicorn
# Note: Using single worker for Railway (workers flag can cause issues)
# Railway requires specific configuration for proxy compatibility
cmd = [
    sys.executable,
    "-m",
    "uvicorn",
    "app.main:app",
    "--host",
    "0.0.0.0",
    "--port",
    str(port_int),
    "--proxy-headers",  # Trust proxy headers from Railway
    "--forwarded-allow-ips", "*",  # Allow forwarded headers from Railway proxy
    # Removed --workers flag - Railway works better with single worker
    # Add --log-level debug for troubleshooting if needed
]

print(f"Starting server on port {port_int}...", file=sys.stderr)
print(f"PYTHONPATH={os.environ['PYTHONPATH']}", file=sys.stderr)
print(f"Working directory: {os.getcwd()}", file=sys.stderr)
print(f"Python executable: {sys.executable}", file=sys.stderr)

# Check if app module can be imported before starting
try:
    import app.main
    print("✅ Successfully imported app.main", file=sys.stderr)
except ImportError as e:
    print(f"❌ Failed to import app.main (ImportError): {e}", file=sys.stderr)
    print(f"   PYTHONPATH: {os.environ.get('PYTHONPATH', 'NOT SET')}", file=sys.stderr)
    import traceback
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"❌ Failed to import app.main (Unexpected error): {e}", file=sys.stderr)
    print(f"   Error type: {type(e).__name__}", file=sys.stderr)
    import traceback
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)

# Run uvicorn
print("🚀 Starting uvicorn server...", file=sys.stderr)
try:
    result = subprocess.call(cmd)
    if result != 0:
        print(f"❌ Uvicorn exited with code {result}", file=sys.stderr)
    sys.exit(result)
except KeyboardInterrupt:
    print("⚠️ Server interrupted by user", file=sys.stderr)
    sys.exit(0)
except Exception as e:
    print(f"❌ Failed to start uvicorn: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)

