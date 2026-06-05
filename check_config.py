#!/usr/bin/env python3
"""
Config Checker Script
Environment değişkenlerini ve ayarları doğrula
"""

import sys
from pathlib import Path

# .env dosyasını yükle
from dotenv import load_dotenv

# Workspace root'u bulma
WORKSPACE_ROOT = Path(__file__).parent
sys.path.insert(0, str(WORKSPACE_ROOT))

env_file = WORKSPACE_ROOT / ".env"
if env_file.exists():
    load_dotenv(env_file)

def check_config():
    """Config'i doğrula ve rapor ver"""
    print("\n" + "="*60)
    print("🔍 CookWise Config Checker")
    print("="*60 + "\n")
    
    # 1. .env dosyası kontrolü
    print("1️⃣ Environment dosyası kontrolü:")
    if env_file.exists():
        print(f"   ✅ .env found: {env_file}")
    else:
        print(f"   ❌ .env bulunamadı!")
        print(f"      Çözüm: cp .env.example .env")
        return False
    
    # 2. requirements.txt kontrolü
    req_file = WORKSPACE_ROOT / "requirements.txt"
    print("\n2️⃣ requirements.txt kontrolü:")
    if req_file.exists():
        print(f"   ✅ requirements.txt found")
    else:
        print(f"   ❌ requirements.txt bulunamadı!")
        return False
    
    # 3. Pydantic Settings'i yükle
    print("\n3️⃣ Pydantic Settings yükleme:")
    try:
        from app.core.config import settings
        print(f"   ✅ Config yüklendi başarıyla")
    except Exception as e:
        print(f"   ❌ Config yükleme hatası: {e}")
        print(f"      Lütfen .env dosyasını kontrol et")
        return False
    
    # 4. Ayarları göster
    print("\n4️⃣ Konfigürasyon Özeti:")
    print(f"   App Name:        {settings.APP_NAME}")
    print(f"   Environment:     {settings.APP_ENV}")
    print(f"   Host:            {settings.APP_HOST}")
    print(f"   Port:            {settings.APP_PORT}")
    print(f"   API Prefix:      {settings.API_PREFIX}")
    print(f"   MongoDB DB:      {settings.MONGODB_DB}")
    print(f"   MongoDB URL:     {settings.MONGODB_URL}")
    print(f"   JWT Algorithm:   {settings.ALGORITHM}")
    print(f"   Token Expires:   {settings.ACCESS_TOKEN_EXPIRE_MINUTES} dakika")
    print(f"   Debug Mode:      {settings.DEBUG}")
    
    # 5. SECRET_KEY kontrolü
    print("\n5️⃣ Güvenlik Kontrolü:")
    if len(settings.SECRET_KEY) < 32:
        print(f"   ⚠️  SECRET_KEY çok kısa ({len(settings.SECRET_KEY)}/32)")
        print(f"      Production'da güçlü bir key oluştur:")
        print(f"      python -c \"import secrets; print(secrets.token_urlsafe(32))\"")
    else:
        print(f"   ✅ SECRET_KEY güçlü ({len(settings.SECRET_KEY)} karakter)")
    
    # 6. Motor import kontrolü
    print("\n6️⃣ Motor (Async MongoDB) Kontrolü:")
    try:
        import motor.motor_asyncio
        print(f"   ✅ Motor kütüphanesi yüklü")
    except Exception as e:
        print(f"   ❌ Motor import hatası: {e}")
        return False
    
    # 7. MongoDB Bağlantısı Kontrolü
    print("\n7️⃣ MongoDB Bağlantısı Kontrolü:")
    try:
        import asyncio
        from app.core.database import Database
        
        async def test_mongodb():
            try:
                await Database.connect_db()
                print(f"   ✅ MongoDB bağlantısı başarılı")
                await Database.close_db()
                return True
            except Exception as e:
                print(f"   ⚠️  MongoDB bağlantı hatası (opsiyonel): {e}")
                print(f"      MongoDB'nin çalıştığını kontrol et")
                print(f"      URL: {settings.MONGODB_URL}")
                print(f"      💡 Docker ile: docker run -d -p 27017:27017 mongo:7.0")
                return None  # Warning but not fatal
        
        result = asyncio.run(test_mongodb())
        
    except Exception as e:
        print(f"   ⚠️  MongoDB test hatası: {e}")
    
    # Başarı
    print("\n" + "="*60)
    print("✅ Tüm zorunlu kontroller başarılı!")
    print("="*60 + "\n")
    print("🚀 Çalıştırmaya hazır! Şu komutlardan birini kullan:")
    print(f"   python run_dev.py")
    print(f"   # veya")
    print(f"   python -m uvicorn app.main:app --reload --host {settings.APP_HOST} --port {settings.APP_PORT}")
    print(f"\n📖 API Docs: http://localhost:{settings.APP_PORT}/docs")
    print(f"🏥 Health Check: http://localhost:{settings.APP_PORT}{settings.API_PREFIX}/health/")
    print()
    
    return True

if __name__ == "__main__":
    success = check_config()
    sys.exit(0 if success else 1)
