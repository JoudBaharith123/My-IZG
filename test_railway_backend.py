#!/usr/bin/env python3
"""Diagnostic script to test Railway backend connectivity."""

import sys
import requests
from urllib.parse import urljoin

# Railway backend URL
RAILWAY_URL = "https://intelligentzonegenerator-production.up.railway.app"

def test_endpoint(path, description):
    """Test an endpoint and return results."""
    url = urljoin(RAILWAY_URL, path)
    print(f"\n{'='*60}")
    print(f"Testing: {description}")
    print(f"URL: {url}")
    print(f"{'='*60}")
    
    try:
        response = requests.get(url, timeout=10)
        print(f"✅ Status Code: {response.status_code}")
        print(f"✅ Response Headers:")
        for key, value in response.headers.items():
            if key.lower() in ['content-type', 'server', 'date', 'content-length']:
                print(f"   {key}: {value}")
        
        try:
            data = response.json()
            print(f"✅ Response Body (JSON):")
            import json
            print(json.dumps(data, indent=2))
        except:
            print(f"✅ Response Body (Text):")
            print(response.text[:500])
            
        return True, response.status_code
        
    except requests.exceptions.Timeout:
        print(f"❌ TIMEOUT: Request took longer than 10 seconds")
        return False, None
    except requests.exceptions.ConnectionError as e:
        print(f"❌ CONNECTION ERROR: {e}")
        return False, None
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP ERROR: {e}")
        return False, None
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {type(e).__name__}: {e}")
        return False, None

def main():
    print("🔍 Railway Backend Diagnostic Test")
    print(f"Target URL: {RAILWAY_URL}")
    
    # Test root endpoint
    success_root, status_root = test_endpoint("/", "Root Endpoint")
    
    # Test health endpoint
    success_health, status_health = test_endpoint("/api/health", "Health Endpoint")
    
    # Test OSRM health endpoint
    success_osrm, status_osrm = test_endpoint("/api/health/osrm", "OSRM Health Endpoint")
    
    # Test docs endpoint
    success_docs, status_docs = test_endpoint("/docs", "API Documentation")
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Root (/):           {'✅' if success_root else '❌'} - Status: {status_root}")
    print(f"Health (/api/health): {'✅' if success_health else '❌'} - Status: {status_health}")
    print(f"OSRM Health:        {'✅' if success_osrm else '❌'} - Status: {status_osrm}")
    print(f"Docs (/docs):       {'✅' if success_docs else '❌'} - Status: {status_docs}")
    
    if not any([success_root, success_health, success_osrm, success_docs]):
        print("\n❌ ALL TESTS FAILED - Backend is not accessible")
        print("\nPossible issues:")
        print("1. Backend is not running or crashed")
        print("2. Railway networking configuration issue")
        print("3. DNS/URL routing problem")
        print("4. Firewall or security group blocking access")
    elif success_health:
        print("\n✅ Backend is accessible and responding!")
    else:
        print("\n⚠️  Partial connectivity - some endpoints work, others don't")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Diagnostic script error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

