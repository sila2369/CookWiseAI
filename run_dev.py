#!/usr/bin/env python3
"""
CookWise API - Development Server Launcher
.env dosyasını otomatik yükler ve FastAPI uygulamasını başlatır
"""

import os
import sys
from pathlib import Path

# .env dosyasını yükle
from dotenv import load_dotenv

# Workspace root
WORKSPACE_ROOT = Path(__file__).parent
env_file = WORKSPACE_ROOT / ".env"

if env_file.exists():
    load_dotenv(env_file)
    print(f"✓ .env dosyası yüklendi: {env_file}")
else:
    print(f"⚠️  .env dosyası bulunamadı: {env_file}")
    print(f"✓ .env.example kopyalanıyor...")
    import shutil
    shutil.copy(WORKSPACE_ROOT / ".env.example", env_file)
    print(f"✓ .env oluşturuldu. Lütfen düzelle ve tekrar çalıştır.")
    sys.exit(1)

# Çalıştır
if __name__ == "__main__":
    import uvicorn
    from app.core.config import settings
    
    print("\n" + "="*60)
    print("🚀 CookWise API - Development Server")
    print("="*60)
    print(f"App Name:    {settings.APP_NAME}")
    print(f"Environment: {settings.APP_ENV}")
    print(f"Host:        {settings.APP_HOST}")
    print(f"Port:        {settings.APP_PORT}")
    print(f"Debug Mode:  {settings.DEBUG}")
    print("-"*60)
    print(f"📖 Swagger UI: http://{settings.APP_HOST}:{settings.APP_PORT}/docs")
    print(f"🏥 Health Check: http://{settings.APP_HOST}:{settings.APP_PORT}{settings.API_PREFIX}/health/")
    print("="*60 + "\n")
    
    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG,
        log_level="info",
    )
