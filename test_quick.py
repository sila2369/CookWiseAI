#!/usr/bin/env python3
"""
Quick Test - MongoDB olmadan hızlı test
FastAPI ve temel bileşenlerin çalışıp çalışmadığını kontrol eder
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

WORKSPACE_ROOT = Path(__file__).parent
sys.path.insert(0, str(WORKSPACE_ROOT))

# .env dosyasını yükle
env_file = WORKSPACE_ROOT / ".env"
if env_file.exists():
    load_dotenv(env_file)

def test_fastapi():
    """FastAPI app'i test et"""
    print("\n" + "="*60)
    print("CookWise API - Quick Test")
    print("="*60 + "\n")
    
    print("1) FastAPI uygulamasi yukleme...")
    try:
        from app.main import app
        print("   [OK] FastAPI app yuklendi")
    except Exception as e:
        print(f"   [ERR] FastAPI yukleme hatasi: {e}")
        return False
    
    print("\n2) Konfigurasyon dogrulama...")
    try:
        from app.core.config import settings
        print(f"   [OK] Settings: {settings.APP_NAME} ({settings.APP_ENV})")
    except Exception as e:
        print(f"   [ERR] Settings hatasi: {e}")
        return False
    
    print("\n3) TestClient ile test etme...")
    try:
        from fastapi.testclient import TestClient
        client = TestClient(app)
        
        # Root endpoint test
        response = client.get("/")
        if response.status_code == 200:
            print(f"   [OK] GET / -> {response.status_code}")
        else:
            print(f"   [ERR] GET / -> {response.status_code}")
            return False
        
        # Health check test
        response = client.get(f"{settings.API_PREFIX}/health/")
        if response.status_code == 200:
            print(f"   [OK] GET {settings.API_PREFIX}/health/ -> {response.status_code}")
            health_data = response.json()
            print(f"      Status: {health_data.get('status')}")
            print(f"      App: {health_data.get('app_name')}")
        else:
            print(f"   [ERR] GET {settings.API_PREFIX}/health/ -> {response.status_code}")
            return False
        
        # Swagger UI test
        response = client.get("/docs")
        if response.status_code == 200:
            print(f"   [OK] GET /docs (Swagger UI) -> {response.status_code}")
        else:
            print(f"   [ERR] GET /docs -> {response.status_code}")
            return False
        
    except Exception as e:
        print(f"   [ERR] Test hatasi: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Başarı
    print("\n" + "="*60)
    print("[OK] Tum testler basarili!")
    print("="*60 + "\n")
    print("Sorun yok! Simdi development server'i baslatabilirsin:")
    print(f"   python run_dev.py")
    print(f"\nVeya production'a kurmak icin:")
    print(f"   docker-compose up")
    print()
    
    return True

if __name__ == "__main__":
    success = test_fastapi()
    sys.exit(0 if success else 1)
