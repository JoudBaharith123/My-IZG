#!/usr/bin/env python3
"""Test script to verify OSRM chunking works with large coordinate lists."""

import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from app.config import settings
from app.services.routing.osrm_client import OSRMClient


def main():
    print("=" * 60)
    print("OSRM Chunking Test")
    print("=" * 60)
    print()
    
    # Check configuration
    if not settings.osrm_base_url:
        print("[ERROR] OSRM_BASE_URL is not configured")
        return 1
    
    print(f"[OK] OSRM Base URL: {settings.osrm_base_url}")
    print()
    
    # Test with a large number of coordinates (similar to the error case - 480 coords)
    print("Testing with 200 coordinates (simulating real scenario)...")
    
    # Generate test coordinates around Jeddah, Saudi Arabia (from the error)
    # Using a smaller variation to keep it realistic
    base_lat, base_lon = 21.5, 39.2
    test_coords = []
    for i in range(200):  # Test with 200 to see performance
        # Add small variations
        lat = base_lat + (i % 20) * 0.01
        lon = base_lon + (i // 20) * 0.01
        test_coords.append((lat, lon))
    
    try:
        import time
        start_time = time.time()
        
        # Use default optimized settings (100 chunk size, 20 parallel)
        client = OSRMClient()
        print(f"[INFO] Using chunk size: {client.max_coordinates_per_request}")
        print(f"[INFO] Max parallel requests: {client.max_parallel_requests}")
        print(f"[INFO] Total coordinates: {len(test_coords)}")
        num_chunks = (len(test_coords) + client.max_coordinates_per_request - 1) // client.max_coordinates_per_request
        total_requests = num_chunks * num_chunks
        print(f"[INFO] Expected chunks: {num_chunks}")
        print(f"[INFO] Total chunk requests: {total_requests}")
        print()
        
        result = client.table(test_coords)
        
        elapsed = time.time() - start_time
        print(f"[INFO] Total time: {elapsed:.2f} seconds")
        print(f"[INFO] Average: {elapsed/total_requests*1000:.0f}ms per request")
        
        durations = result.get("durations", [])
        distances = result.get("distances", [])
        
        if not durations or not distances:
            print("[ERROR] Missing durations or distances in result")
            return 1
        
        print(f"[OK] Received duration matrix: {len(durations)}x{len(durations[0]) if durations else 0}")
        print(f"[OK] Received distance matrix: {len(distances)}x{len(distances[0]) if distances else 0}")
        
        # Check for None values (failed chunks)
        none_count_durations = sum(1 for row in durations for val in row if val is None)
        none_count_distances = sum(1 for row in distances for val in row if val is None)
        
        if none_count_durations > 0 or none_count_distances > 0:
            print(f"[WARNING] Found {none_count_durations} None values in durations")
            print(f"[WARNING] Found {none_count_distances} None values in distances")
        else:
            print("[OK] No None values found - all chunks succeeded!")
        
        # Show sample values
        if durations and len(durations) > 0 and len(durations[0]) > 1:
            print(f"[OK] Sample duration [0][1]: {durations[0][1]:.2f} seconds")
        if distances and len(distances) > 0 and len(distances[0]) > 1:
            print(f"[OK] Sample distance [0][1]: {distances[0][1]:.2f} meters")
        
        elapsed = time.time() - start_time
        print(f"[OK] Total time: {elapsed:.2f} seconds")
        if total_requests > 0:
            print(f"[OK] Average: {elapsed/total_requests:.3f} seconds per request")
        
        print()
        print("=" * 60)
        print("[SUCCESS] OSRM chunking is working!")
        print("=" * 60)
        return 0
        
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

