#!/usr/bin/env python3
"""Helper script to check and create .env file for Supabase configuration."""

from pathlib import Path
import os

def main():
    project_root = Path(__file__).parent
    env_file = project_root / ".env"
    
    print("=" * 60)
    print("Supabase Environment Variables Checker")
    print("=" * 60)
    print()
    
    # Check if .env exists
    if env_file.exists():
        print(f"✅ Found .env file at: {env_file}")
        print()
        print("Current contents:")
        print("-" * 60)
        with open(env_file, "r", encoding="utf-8") as f:
            content = f.read()
            # Mask the key for security
            lines = content.split("\n")
            for line in lines:
                if "IZG_SUPABASE_KEY" in line and "=" in line:
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        key_value = parts[1].strip()
                        if len(key_value) > 20:
                            masked = key_value[:20] + "..." + key_value[-10:]
                            print(f"{parts[0]}={masked}")
                        else:
                            print(line)
                    else:
                        print(line)
                else:
                    print(line)
        print("-" * 60)
        print()
    else:
        print(f"❌ .env file NOT found at: {env_file}")
        print()
        print("Creating template .env file...")
        print()
        
        template = """# Supabase Configuration (Required for database storage)
# Get these from: https://supabase.com/dashboard → Your Project → Settings → API
IZG_SUPABASE_URL=https://your-project-id.supabase.co
IZG_SUPABASE_KEY=your-service-role-key-here

# API Configuration
IZG_API_PREFIX=/api
# IZG_FRONTEND_ALLOWED_ORIGINS - Leave commented to use defaults
# If you need to override, use JSON array format: ["http://localhost:5173","http://127.0.0.1:5173"]
# Or comma-separated: http://localhost:5173,http://127.0.0.1:5173

# Data Paths
IZG_DATA_ROOT=./data
IZG_CUSTOMER_FILE=./data/Easyterrritory_26831_29_oct_2025.CSV
IZG_DC_LOCATIONS_FILE=./data/dc_locations.xlsx

# OSRM Routing (Optional - leave empty if not using OSRM)
IZG_OSRM_BASE_URL=http://localhost:5000
"""
        
        with open(env_file, "w", encoding="utf-8") as f:
            f.write(template)
        
        print(f"✅ Created .env file at: {env_file}")
        print()
        print("⚠️  Please edit .env and add your Supabase credentials!")
        print("   Get them from: https://supabase.com/dashboard → Settings → API")
        print()
        return
    
    # Check environment variables
    print("Checking environment variables...")
    print()
    
    supabase_url = os.getenv("IZG_SUPABASE_URL")
    supabase_key = os.getenv("IZG_SUPABASE_KEY")
    
    if supabase_url:
        print(f"✅ IZG_SUPABASE_URL (from environment): {supabase_url[:30]}...")
    else:
        print("❌ IZG_SUPABASE_URL not found in environment")
    
    if supabase_key:
        print(f"✅ IZG_SUPABASE_KEY (from environment): {supabase_key[:20]}...")
    else:
        print("❌ IZG_SUPABASE_KEY not found in environment")
    
    print()
    
    # Test loading from config
    print("Testing config loading...")
    print()
    
    try:
        import sys
        sys.path.insert(0, str(project_root / "src"))
        from app.config import settings
        
        if settings.supabase_url:
            print(f"✅ Config loaded SUPABASE_URL: {settings.supabase_url[:30]}...")
        else:
            print("❌ Config SUPABASE_URL is None")
        
        if settings.supabase_key:
            print(f"✅ Config loaded SUPABASE_KEY: {settings.supabase_key[:20]}...")
        else:
            print("❌ Config SUPABASE_KEY is None")
        
        print()
        
        if settings.supabase_url and settings.supabase_key:
            print("=" * 60)
            print("✅ SUCCESS: Supabase is configured!")
            print("=" * 60)
        else:
            print("=" * 60)
            print("❌ ERROR: Supabase is NOT configured")
            print("=" * 60)
            print()
            print("Troubleshooting:")
            print("1. Make sure .env file exists in project root")
            print("2. Make sure variables start with IZG_ prefix")
            print("3. Make sure there are no spaces around = sign")
            print("4. Restart backend after editing .env")
            print()
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        print()
        print("Make sure you're running this from the project root directory")

if __name__ == "__main__":
    main()

