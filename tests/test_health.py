"""
Unit Tests - Health Check Endpoints
===================================

Tüm health check endpoint'lerinin test'i

Çalıştır:
    pytest tests/test_health.py -v
    pytest tests/test_health.py::test_basic_health_check -v
"""

import pytest
from fastapi.testclient import TestClient
from app.core.config import settings


class TestHealthCheckEndpoints:
    """Health check endpoint'lerinin test suite'ı"""
    
    # ==================== GET / (Root) ====================
    
    def test_root_endpoint(self, client: TestClient):
        """GET / - Root endpoint yanıt mu?"""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        
        # Gerekli alanlar kontrol
        assert "title" in data
        assert "version" in data
        assert "environment" in data
        assert data["title"] == settings.APP_NAME
    
    def test_root_endpoint_documentation_links(self, client: TestClient):
        """GET / - Documentation linkler var mı?"""
        response = client.get("/")
        data = response.json()
        
        assert "documentation" in data
        docs = data["documentation"]
        
        assert "swagger" in docs
        assert "redoc" in docs
        assert "openapi" in docs
        
        # URLs doğru mı?
        assert docs["swagger"] == "/docs"
        assert docs["redoc"] == "/redoc"
        assert docs["openapi"] == "/openapi.json"
    
    def test_root_endpoint_has_endpoints_list(self, client: TestClient):
        """GET / - Endpoint'ler listeleniyor mu?"""
        response = client.get("/")
        data = response.json()
        
        assert "endpoints" in data
        endpoints = data["endpoints"]
        
        # Health endpoint'leri bulunmalı
        assert "health" in endpoints
        assert endpoints["health"].startswith(settings.API_PREFIX)
    
    # ==================== GET /status ====================
    
    def test_status_endpoint(self, client: TestClient):
        """GET /api/v1/status - API status endpoint"""
        response = client.get(f"{settings.API_PREFIX}/status")
        
        assert response.status_code == 200
        data = response.json()
        
        # Gerekli alanlar
        assert data["status"] == "ok"
        assert data["api_name"] == settings.APP_NAME
        assert "environment" in data
        assert "debug_mode" in data
        assert "timestamp" in data
    
    def test_status_debug_mode_from_config(self, client: TestClient):
        """GET /api/v1/status - Debug mode config'ten gelir"""
        response = client.get(f"{settings.API_PREFIX}/status")
        data = response.json()
        
        assert data["debug_mode"] == settings.DEBUG
    
    # ==================== GET /health/ (Basic) ====================
    
    def test_basic_health_check(self, client: TestClient):
        """GET /api/v1/health/ - Basit health check"""
        response = client.get(f"{settings.API_PREFIX}/health/")
        
        assert response.status_code == 200
        data = response.json()
        
        # Temel alanlar
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["app_name"] == settings.APP_NAME
        assert data["version"] == "1.0.0"
    
    def test_health_check_timestamp_format(self, client: TestClient):
        """GET /api/v1/health/ - Timestamp ISO format'ta mı?"""
        response = client.get(f"{settings.API_PREFIX}/health/")
        data = response.json()
        
        timestamp = data["timestamp"]
        
        # ISO format check (basic)
        assert "T" in timestamp  # 2026-03-18T10:30:00
        assert "-" in timestamp
        assert ":" in timestamp
    
    # ==================== GET /health/db (Database) ====================
    
    def test_database_health_endpoint_status(self, client: TestClient):
        """GET /api/v1/health/db - Veritabanı status'u"""
        response = client.get(f"{settings.API_PREFIX}/health/db")
        
        assert response.status_code == 200
        data = response.json()
        
        # Response structure
        assert "status" in data  # "ok"
        assert "database" in data
    
    def test_database_health_structure(self, client: TestClient):
        """GET /api/v1/health/db - Database object'inin yapısı"""
        response = client.get(f"{settings.API_PREFIX}/health/db")
        data = response.json()
        
        db = data["database"]
        
        # Gerekli alanlar
        assert "connected" in db
        assert "name" in db
        assert "driver" in db
        assert "status" in db
        
        # Değerler uygun mu?
        assert db["name"] == settings.MONGODB_DB
        assert "motor" in db["driver"].lower()
    
    def test_database_health_graceful_fallback(self, client: TestClient):
        """GET /api/v1/health/db - MongoDB devre dışıysa graceful fallback"""
        response = client.get(f"{settings.API_PREFIX}/health/db")
        
        # MongoDB bağlı değilse de durum 200 olmalı (graceful)
        assert response.status_code in [200]  # Fallback çalıştığında 200
        
        data = response.json()
        
        # Status "disabled" veya "connected" veya "error" olabilir
        assert data["database"]["status"] in [
            "connected", 
            "disabled", 
            "error: ConnectFailure"
        ]
    
    # ==================== GET /health/detailed ====================
    
    def test_detailed_health_check(self, client: TestClient):
        """GET /api/v1/health/detailed - Detaylı sistem raporu"""
        response = client.get(f"{settings.API_PREFIX}/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        
        # Temel alanlar
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "environment" in data
        assert "debug" in data
    
    def test_detailed_health_api_section(self, client: TestClient):
        """GET /api/v1/health/detailed - API section'ı tam mı?"""
        response = client.get(f"{settings.API_PREFIX}/health/detailed")
        data = response.json()
        
        api = data["api"]
        
        # Gerekli alanlar
        assert api["name"] == settings.APP_NAME
        assert api["version"] == "1.0.0"
        assert "host" in api
        assert "port" in api
        assert "cors_enabled" in api
    
    def test_detailed_health_database_section(self, client: TestClient):
        """GET /api/v1/health/detailed - Database section'ı tam mı?"""
        response = client.get(f"{settings.API_PREFIX}/health/detailed")
        data = response.json()
        
        db = data["database"]
        
        # Gerekli alanlar
        assert "status" in db
        assert "name" in db
        assert "driver" in db
        assert "pool" in db
        assert "collections" in db
    
    def test_detailed_health_collections_list(self, client: TestClient):
        """GET /api/v1/health/detailed - Collections list'i"""
        response = client.get(f"{settings.API_PREFIX}/health/detailed")
        data = response.json()
        
        collections = data["database"]["collections"]
        
        # Bir dizi olmalı (MongoDB bağlı değilse boş)
        assert isinstance(collections, list)
    
    # ==================== GET /health/ready (Readiness Probe) ====================
    
    def test_readiness_probe_endpoint(self, client: TestClient):
        """GET /api/v1/health/ready - Readiness probe"""
        response = client.get(f"{settings.API_PREFIX}/health/ready")
        
        # Status 200 veya 503 (MongoDB durumuna bağlı)
        assert response.status_code in [200, 503]
        
        data = response.json()
        
        # Response yapısı
        assert "ready" in data
        assert "reason" in data
        assert isinstance(data["ready"], bool)
    
    def test_readiness_probe_graceful(self, client: TestClient):
        """GET /api/v1/health/ready - Graceful fallback"""
        response = client.get(f"{settings.API_PREFIX}/health/ready")
        data = response.json()
        
        # MongoDB olmasa bile ready olmalı (opsiyonel olduğu için)
        # veya "ready: true" ile MongoDB optional mesajı
        if response.status_code == 200:
            assert data["ready"] is True or "optional" in data["reason"].lower()
    
    # ==================== GET /health/live (Liveness Probe) ====================
    
    def test_liveness_probe_endpoint(self, client: TestClient):
        """GET /api/v1/health/live - Liveness probe"""
        response = client.get(f"{settings.API_PREFIX}/health/live")
        
        assert response.status_code == 200
        data = response.json()
        
        # Response yapısı
        assert "alive" in data
        assert data["alive"] is True
        assert "app" in data
        assert "timestamp" in data
    
    def test_liveness_probe_always_responds(self, client: TestClient):
        """GET /api/v1/health/live - Her zaman 200 dönmeli"""
        # 3 kez çağır
        for _ in range(3):
            response = client.get(f"{settings.API_PREFIX}/health/live")
            assert response.status_code == 200
    
    # ==================== HTTP Method Tests ====================
    
    def test_health_endpoint_post_not_allowed(self, client: TestClient):
        """POST /api/v1/health/ - POST method izinli değil"""
        response = client.post(f"{settings.API_PREFIX}/health/")
        
        # 405 Method Not Allowed veya 404 Not Found
        assert response.status_code in [405, 404]
    
    def test_health_endpoint_delete_not_allowed(self, client: TestClient):
        """DELETE /api/v1/health/ - DELETE method izinli değil"""
        response = client.delete(f"{settings.API_PREFIX}/health/")
        
        assert response.status_code in [405, 404]
    
    # ==================== Performance Tests ====================
    
    def test_health_endpoint_response_time(self, client: TestClient):
        """GET /health/ - Response zamanı hızlı mı? (<500ms)"""
        import time
        
        start = time.time()
        response = client.get(f"{settings.API_PREFIX}/health/")
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 0.5  # 500ms'den az
    
    def test_detailed_health_response_time(self, client: TestClient):
        """GET /health/detailed - Response zamanı hızlı mı? (<1s)"""
        import time
        
        start = time.time()
        response = client.get(f"{settings.API_PREFIX}/health/detailed")
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 1.0  # 1 saniyeden az
    
    # ==================== Integration Tests ====================
    
    def test_all_health_endpoints_accessible(self, client: TestClient):
        """Tüm health endpoint'leri erişilebilir mi?"""
        endpoints = [
            f"{settings.API_PREFIX}/health/",
            f"{settings.API_PREFIX}/health/db",
            f"{settings.API_PREFIX}/health/detailed",
            f"{settings.API_PREFIX}/health/ready",
            f"{settings.API_PREFIX}/health/live",
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code in [200, 503], \
                f"Endpoint {endpoint} failed with {response.status_code}"
    
    def test_health_endpoints_return_json(self, client: TestClient):
        """Tüm health endpoint'leri JSON döndürür mü?"""
        endpoints = [
            f"{settings.API_PREFIX}/health/",
            f"{settings.API_PREFIX}/health/db",
            f"{settings.API_PREFIX}/health/detailed",
            f"{settings.API_PREFIX}/health/ready",
            f"{settings.API_PREFIX}/health/live",
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            
            # Content-Type JSON olmalı
            assert "application/json" in response.headers.get("content-type", "")
            
            # JSON parse'lanabilir olmalı
            data = response.json()
            assert isinstance(data, dict)


# ==================== PARAMETRIZE TEST EXAMPLE ====================

@pytest.mark.parametrize("endpoint,expected_fields", [
    (f"{settings.API_PREFIX}/health/", ["status", "timestamp", "app_name"]),
    (f"{settings.API_PREFIX}/health/db", ["status", "database"]),
    (f"{settings.API_PREFIX}/health/live", ["alive", "app"]),
])
def test_health_endpoints_have_required_fields(
    client: TestClient,
    endpoint: str,
    expected_fields: list
):
    """Parametrized test - endpoint'ler gerekli alanları içeriyor mu?"""
    response = client.get(endpoint)
    
    assert response.status_code in [200, 503]
    data = response.json()
    
    for field in expected_fields:
        assert field in data, f"Missing field '{field}' in {endpoint}"
