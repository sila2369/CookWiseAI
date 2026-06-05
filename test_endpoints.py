#!/usr/bin/env python3
"""
API Test Script
Tüm endpoint'leri test et
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"

print("\n" + "="*70)
print("FastAPI Backend - Endpoint Tests")
print("="*70 + "\n")

# Test 1: Root endpoint
print("1) Root Endpoint: GET /")
print("-" * 70)
try:
    response = requests.get(f"{BASE_URL}/")
    print(f"Status: {response.status_code} [OK]" if response.status_code == 200 else f"Status: {response.status_code} [ERR]")
    data = response.json()
    print(f"Title: {data['title']}")
    print(f"Version: {data['version']}")
    print(f"Environment: {data['environment']}")
    print(f"Endpoints:")
    for key, value in data.get('endpoints', {}).items():
        print(f"  - {key}: {value}")
except Exception as e:
    print(f"[ERR] Error: {e}")

print()

# Test 2: Status endpoint
print("2) Status Endpoint: GET /api/v1/status")
print("-" * 70)
try:
    response = requests.get(f"{BASE_URL}{API_PREFIX}/status")
    print(f"Status: {response.status_code} [OK]" if response.status_code == 200 else f"Status: {response.status_code} [ERR]")
    data = response.json()
    print(f"Status: {data['status']}")
    print(f"API Name: {data['api_name']}")
    print(f"Environment: {data['environment']}")
    print(f"Debug Mode: {data['debug_mode']}")
except Exception as e:
    print(f"[ERR] Error: {e}")

print()

# Test 3: Health check
print("3) Health Check: GET /api/v1/health/")
print("-" * 70)
try:
    response = requests.get(f"{BASE_URL}{API_PREFIX}/health/")
    print(f"Status: {response.status_code} [OK]" if response.status_code == 200 else f"Status: {response.status_code} [ERR]")
    data = response.json()
    print(f"Health: {data['status']}")
    print(f"App: {data['app_name']}")
    print(f"Version: {data['version']}")
    print(f"Timestamp: {data['timestamp']}")
except Exception as e:
    print(f"[ERR] Error: {e}")

print()

# Test 4: Detailed health check
print("4) Detailed Health Check: GET /api/v1/health/detailed")
print("-" * 70)
try:
    response = requests.get(f"{BASE_URL}{API_PREFIX}/health/detailed")
    print(f"Status: {response.status_code} [OK]" if response.status_code == 200 else f"Status: {response.status_code} [ERR]")
    data = response.json()
    print(f"Health: {data['status']}")
    print(f"App: {data['app_name']}")
    print(f"Environment: {data['environment']}")
    print(f"Database Status: {data['database']['status']}")
    print(f"Database Name: {data['database']['name']}")
except Exception as e:
    print(f"[ERR] Error: {e}")

print()

# Test 5: Swagger UI
print("5) Swagger UI: GET /docs")
print("-" * 70)
try:
    response = requests.get(f"{BASE_URL}/docs")
    print(f"Status: {response.status_code} [OK]" if response.status_code == 200 else f"Status: {response.status_code} [ERR]")
    print(f"Content-Type: {response.headers.get('content-type')}")
    print(f"Size: {len(response.content)} bytes")
except Exception as e:
    print(f"[ERR] Error: {e}")

print()

# Test 6: OpenAPI Schema
print("6) OpenAPI Schema: GET /openapi.json")
print("-" * 70)
try:
    response = requests.get(f"{BASE_URL}/openapi.json")
    print(f"Status: {response.status_code} [OK]" if response.status_code == 200 else f"Status: {response.status_code} [ERR]")
    data = response.json()
    print(f"OpenAPI Version: {data.get('openapi')}")
    print(f"API Title: {data.get('info', {}).get('title')}")
    print(f"API Version: {data.get('info', {}).get('version')}")
    print(f"Paths (Endpoints): {len(data.get('paths', {}))}")
    for path in sorted(data.get('paths', {}).keys())[:5]:
        print(f"  - {path}")
    if len(data.get('paths', {})) > 5:
        print(f"  ... ve {len(data.get('paths', {})) - 5} tane daha")
except Exception as e:
    print(f"[ERR] Error: {e}")

print()
print("="*70)
print("[OK] Testler Tamamlandi!")
print("="*70)
print("\n🔗 Erişim Linkler:")
print(f"  - Root: http://localhost:8000/")
print(f"  - Swagger UI: http://localhost:8000/docs")
print(f"  - ReDoc: http://localhost:8000/redoc")
print(f"  - OpenAPI: http://localhost:8000/openapi.json")
print()
