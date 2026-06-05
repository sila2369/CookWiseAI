"""
Uygulama Konfigürasyonu - Pydantic Settings
Environment değişkenlerini .env dosyasından ve sistem değişkenlerinden okur
Type-safe yapı ile hata tanıması sağlar
"""

from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List, Optional


class Settings(BaseSettings):
    """
    Uygulama ayarları - Tüm ortamlar (dev, staging, prod) için
    Eksik ortam değişkeni varsa uygulama başlamaz
    """
    
    # ==================== UYGULAMA AYARLARI ====================
    APP_NAME: str
    """Uygulama adı (örn: CookWise API)"""
    
    APP_ENV: str = "development"
    """Uygulama ortamı: development, staging, production"""
    
    APP_HOST: str = "0.0.0.0"
    """Sunucunun bind edileceği host adres"""
    
    APP_PORT: int = 8000
    """Sunucunun dinleyeceği port"""
    
    # ==================== MONGODB AYARLARI ====================
    MONGODB_URL: str
    """MongoDB bağlantı string'i (örn: mongodb://localhost:27017)"""
    
    MONGODB_DB: str
    """Kullanılacak veritabanı adı"""
    
    # ==================== JWT (JSON Web Token) AYARLARI ====================
    SECRET_KEY: str
    """JWT token'ları imzalamak için gizli anahtar (minimum 32 karakter)"""
    
    ALGORITHM: str = "HS256"
    """JWT token imzalama algoritması"""
    
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    """Access token'ın geçerlilik süresi (dakika)"""
    
    # ==================== CORS AYARLARI ====================
    CORS_ORIGINS: List[str] = ["*"]
    """CORS'ta izin verilecek origin'ler"""
    
    CORS_CREDENTIALS: bool = True
    """CORS'ta credentials (cookies) izni"""
    
    CORS_METHODS: List[str] = ["*"]
    """CORS'ta izin verilecek HTTP metotları"""
    
    CORS_HEADERS: List[str] = ["*"]
    """CORS'ta izin verilecek header'lar"""
    
    # ==================== FIREBASE AYARLARI (Kullanıcılar için) ====================
    USE_FIREBASE_AUTH: bool = False
    """True ise kullanıcılar Firebase'de tutulur (Auth + Firestore)"""
    
    FIREBASE_CREDENTIALS_PATH: Optional[str] = None
    """Service Account JSON dosya yolu (örn: firebase-credentials.json)"""
    
    FIREBASE_PROJECT_ID: Optional[str] = None
    """Firebase proje ID'si"""
    
    FIREBASE_API_KEY: Optional[str] = None
    """Firebase Web API Key - Login için gerekli (REST API)"""

    ADMIN_EMAILS: List[str] = ["admin@cookwise.com"]
    """Admin kabul edilecek e-posta adresleri"""

    # ==================== EMAIL / SMTP AYARLARI ====================
    SMTP_HOST: Optional[str] = None
    """SMTP sunucu adresi (örn: smtp.gmail.com)"""

    SMTP_PORT: int = 587
    """SMTP portu (TLS için genelde 587, SSL için 465)"""

    SMTP_USERNAME: Optional[str] = None
    """SMTP kullanıcı adı (çoğu sağlayıcıda e-posta adresi)"""

    SMTP_PASSWORD: Optional[str] = None
    """SMTP şifresi / app password"""

    SMTP_FROM_EMAIL: Optional[str] = None
    """Gönderici e-posta adresi"""

    SMTP_FROM_NAME: str = "CookWise"
    """Gönderici görünen adı"""

    SMTP_USE_TLS: bool = True
    """STARTTLS kullanılsın mı?"""

    SMTP_USE_SSL: bool = False
    """Doğrudan SSL (SMTPS) kullanılsın mı?"""
    
    # ==================== AI PROVIDER AYARLARI ====================
    # OPENAI_API_KEY is required only when AI_PROVIDER=openai
    OPENAI_API_KEY: Optional[str] = None
    """OpenAI API key (free tier/dev only)."""

    GEMINI_API_KEY: Optional[str] = None
    """Gemini API key."""

    GEMINI_MODEL: str = "gemini-1.5-flash"
    """Gemini chat model."""

    XAI_API_KEY: Optional[str] = None
    """xAI (Grok) API key."""

    XAI_BASE_URL: str = "https://api.x.ai/v1"
    """xAI API base URL."""

    GROK_MODEL: str = "grok-2-latest"
    """Grok model name."""

    GROQ_API_KEY: Optional[str] = None
    """Groq Cloud API key."""

    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    """Groq OpenAI-compatible API base URL."""

    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    """Groq model name."""

    GROQ_MAX_TOKENS: int = 1600
    """Groq yanıt uzunluğu üst sınırı (zengin tarif JSON için)."""

    GROQ_TEMPERATURE: float = 0.75
    """Groq için sıcaklık (0.7–0.8 aralığında daha doğal anlatım)."""

    OLLAMA_BASE_URL: str = "http://host.docker.internal:11434"
    """Ollama API base URL."""

    OLLAMA_MODEL: str = "llama3.1:8b"
    """Ollama model name."""

    # AI_PROVIDER: "openai", "gemini", "grok", "groq", "ollama" or "local"
    AI_PROVIDER: str = "local"
    """AI provider selection."""

    OPENAI_MODEL: str = "gpt-4o-mini"
    """OpenAI chat model."""

    AI_OPENAI_TIMEOUT_SECONDS: int = 30
    """Request timeout for OpenAI."""

    AI_TEMPERATURE: float = 0.7
    """LLM sıcaklığı (yaratıcılık/çeşitlilik)."""

    AI_STRICT_LLM: bool = False
    """True ise gemini/openai hatasında local fallback yapılmaz."""

    # ==================== API AYARLARI ====================
    API_PREFIX: str = "/api/v1"
    """API route'larının başında gelecek prefix"""
    
    DEBUG: bool = False
    """Debug modu (production'da False olmalı)"""
    
    NEXT_PUBLIC_API_URL: Optional[str] = None
    """Frontend API URL (to prevent pydantic validation error)"""

    RECIPES_DATASET_PATH: str = "recipes.json"
    """Raw Kaggle recipe dataset path used by import scripts."""

    CLEANED_RECIPES_PATH: str = "cleaned_recipes.json"
    """Cleaned recipe JSON output path used by import scripts."""
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "validate_default": True,
        "extra": "ignore"
    }


@lru_cache()
def get_settings() -> Settings:
    """
    Settings singleton instance'ını döndür
    
    Returns:
        Settings: Konfigürasyon instance'ı
        
    Raises:
        ValidationError: Gerekli environment değişkenleri eksikse
    """
    return Settings()


# Global settings instance - tüm yerde kullan
settings = get_settings()
