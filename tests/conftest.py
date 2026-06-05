"""
Pytest Configuration and Fixtures
==================================

Tüm testler için shared configuration ve fixtures.

Test çalıştırma:
    pytest                      # Tüm testleri çalıştır
    pytest -v                   # Verbose
    pytest --cov=app tests/     # Coverage raporu ile
    pytest -k test_health       # Sadece health test'leri

Fixtures:
    - app_fixture: FastAPI test app
    - client_fixture: TestClient
    - db_fixture: Test database (mocked)
"""

import pytest
import asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Generator

# Project imports
from app.main import app
from app.core.config import settings


# ==================== PYTEST CONFIGURATION ====================

def pytest_configure(config):
    """Pytest başlarken çalıştırılan configuration"""
    # Custom markers tanımla
    config.addinivalue_line(
        "markers", "asyncio: marks tests as async (deselect with '-m \"not asyncio\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )


@pytest.fixture(scope="session")
def event_loop():
    """
    Event loop'u session'ı ömrü boyunca yapıştır
    Async test'lerde kullanılır
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ==================== FASTAPI APP FIXTURES ====================

@pytest.fixture(scope="function")
def app_fixture():
    """FastAPI test uygulaması"""
    return app


@pytest.fixture(scope="function")
def client(app_fixture: FastAPI) -> TestClient:
    """
    FastAPI TestClient
    
    Kullanım test'lerde:
        def test_health(client):
            response = client.get("/api/v1/health/")
            assert response.status_code == 200
    """
    return TestClient(app_fixture)


# ==================== MOCKED DATABASE FIXTURES ====================

@pytest.fixture(scope="function")
async def mock_database():
    """
    Mocked MongoDB - gerçek öğe bağlantı yapmadan test et
    
    Kullanım:
        async def test_user_create(mock_database):
            mock_database["users"].insert_one = AsyncMock()
    """
    mock_db = MagicMock()
    
    # Mock collection'lar
    for collection_name in ["users", "products", "orders"]:
        mock_collection = AsyncMock()
        mock_db.__getitem__.return_value = mock_collection
        mock_db[collection_name] = mock_collection
    
    return mock_db


@pytest.fixture(scope="function")
async def mock_db_dependency(mock_database):
    """
    Database dependency'yi mock ile değiştir
    
    Kullanım:
        async def test_list_users(client, mock_db_dependency):
            with patch("get_database", return_value=mock_db_dependency):
                response = client.get("/api/v1/users")
    """
    return mock_database


# ==================== AUTHENTICATION FIXTURES ====================

@pytest.fixture
def test_user() -> dict:
    """Test kullanıcısı - mock user object"""
    return {
        "id": "507f1f77bcf86cd799439011",  # MongoDB ObjectId as string
        "email": "test@example.com",
        "full_name": "Test User",
        "role": "user",
        "is_active": True,
        "created_at": "2026-03-18T10:00:00",
    }


@pytest.fixture 
def test_admin() -> dict:
    """Test admin kullanıcısı"""
    return {
        "id": "507f1f77bcf86cd799439012",
        "email": "admin@example.com",
        "full_name": "Admin User",
        "role": "admin",
        "is_active": True,
        "created_at": "2026-03-18T10:00:00",
    }


@pytest.fixture
def test_jwt_token() -> str:
    """Test JWT token - mocked token"""
    from app.core.security import create_access_token
    from datetime import timedelta
    
    token_data = {"sub": "507f1f77bcf86cd799439011"}
    token = create_access_token(
        data=token_data,
        expires_delta=timedelta(hours=24)
    )
    return token


# ==================== MOCK RESPONSES ====================

@pytest.fixture
def mock_health_response() -> dict:
    """Health endpoint mock response"""
    return {
        "status": "healthy",
        "timestamp": "2026-03-18T10:30:00.000000",
        "app_name": "CookWise API",
        "version": "1.0.0",
    }


@pytest.fixture
def mock_db_health_response() -> dict:
    """Database health endpoint mock response"""
    return {
        "status": "ok",
        "database": {
            "connected": True,
            "name": "cookwise",
            "driver": "motor 3.3.2",
            "status": "connected"
        }
    }


# ==================== PATCHING FIXTURES ====================

@pytest.fixture
def mock_database_connect(mock_database):
    """
    Database.connect_db() fonksiyonunu mock ile değiştir
    
    Kullanım:
        def test_app_startup(mock_database_connect):
            # Database.connect_db() artık mock
    """
    with patch("app.core.database.Database.connect_db", 
               new_callable=AsyncMock) as mock:
        mock.return_value = None
        yield mock


@pytest.fixture
def mock_database_close(mock_database):
    """
    Database.close_db() fonksiyonunu mock ile değiştir
    """
    with patch("app.core.database.Database.close_db", 
               new_callable=AsyncMock) as mock:
        mock.return_value = None
        yield mock


# ==================== UTILITY FUNCTIONS ====================

def assert_valid_response(response: dict, 
                          required_fields: list = None):
    """
    Response'ın geçerli bir JSON olup olmadığını kontrol et
    
    Kullanım:
        response = client.get("/api/v1/health/")
        assert_valid_response(response.json(), 
                              ["status", "timestamp"])
    """
    if required_fields:
        for field in required_fields:
            assert field in response, f"Missing field: {field}"


def assert_pagination_response(response: dict,
                               expected_count: int = None):
    """
    Pagination'lı response'ın geçerli olup olmadığını kontrol et
    
    Kullanım:
        response = client.get("/api/v1/users?skip=0&limit=10")
        assert_pagination_response(response.json(), expected_count=10)
    """
    assert "items" in response
    assert "total" in response
    assert "skip" in response
    assert "limit" in response
    
    if expected_count is not None:
        assert len(response["items"]) == expected_count


# ==================== ASYNC TEST HELPERS ====================

@pytest.fixture
async def async_client(app_fixture):
    """Async HTTP client (httpx) - advanced testing için"""
    from httpx import AsyncClient
    
    async with AsyncClient(app=app_fixture, base_url="http://test") as client:
        yield client


# ==================== TEST MARKERS ====================

# Markers file'ı için - pytest.ini'de yapılabilir
"""
[tool:pytest]
markers =
    asyncio: marks tests as async
    unit: marks tests as unit tests
    integration: marks tests as integration tests
    slow: marks tests as slow
    security: marks tests as security tests
"""
