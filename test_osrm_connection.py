#!/usr/bin/env python3
"""Test script to verify OSRM connectivity."""

import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from app.config import settings
from app.services.routing.osrm_client import OSRMClient, check_health


def main():
    print("=" * 60)
    print("OSRM Connection Test")
    print("=" * 60)
    print()
    
    # Check configuration
    print("1. Checking OSRM configuration...")
    if not settings.osrm_base_url:
        print("   [ERROR] OSRM_BASE_URL is not configured")
        print("   Please set IZG_OSRM_BASE_URL in your .env file")
        return 1
    
    print(f"   [OK] OSRM Base URL: {settings.osrm_base_url}")
    print(f"   [OK] OSRM Profile: {settings.osrm_profile}")
    print()
    
    # Test health check
    print("2. Testing OSRM health check...")
    try:
        is_healthy = check_health()
        if is_healthy:
            print("   [OK] OSRM service is healthy and accessible!")
        else:
            print("   [ERROR] OSRM service is not responding")
            return 1
    except Exception as e:
        print(f"   [ERROR] Error during health check: {e}")
        return 1
    print()
    
    # Test table request
    print("3. Testing OSRM table request...")
    try:
        client = OSRMClient()
        # Test with two coordinates (Berlin area)
        test_coords = [
            (52.517037, 13.388860),  # Berlin, Germany
            (52.496891, 13.385983),  # Berlin, Germany
        ]
        result = client.table(test_coords)
        
        if "durations" in result and "distances" in result:
            durations = result["durations"]
            distances = result["distances"]
            print(f"   [OK] Table request successful!")
            print(f"   [OK] Received {len(durations)}x{len(durations[0]) if durations else 0} duration matrix")
            print(f"   [OK] Received {len(distances)}x{len(distances[0]) if distances else 0} distance matrix")
            if durations and len(durations) > 0 and len(durations[0]) > 0:
                print(f"   [OK] Sample duration: {durations[0][1]:.2f} seconds")
            if distances and len(distances) > 0 and len(distances[0]) > 0:
                print(f"   [OK] Sample distance: {distances[0][1]:.2f} meters")
        else:
            print("   [ERROR] Invalid response format")
            return 1
    except Exception as e:
        print(f"   [ERROR] Error during table request: {e}")
        return 1
    print()
    
    print("=" * 60)
    print("[SUCCESS] OSRM is connected and working!")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())

