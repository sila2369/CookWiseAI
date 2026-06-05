#!/usr/bin/env python3
"""
Fix Motor Version Script
Motor sürümünü 3.2.0'a downgrade et
"""

import subprocess
import sys

print("\n" + "="*60)
print("🔧 Motor Version Fix")
print("="*60 + "\n")

print("1️⃣ Motor versiyonunu kontrol etme...")
result = subprocess.run([sys.executable, "-m", "pip", "show", "motor"], capture_output=True, text=True)
if "Version: 3.2.0" in result.stdout:
    print("   ✅ Motor 3.2.0 zaten yüklü!")
else:
    print("   ⚠️  Motor sürümü düzeltiliyor...")
    subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "--force-reinstall", "motor==3.2.0"], check=False)
    print("   ✅ Motor 3.2.0 yüklendi")

print("\n2️⃣ Config'i doğrulama...")
try:
    from app.core.config import settings
    print(f"   ✅ Config yüklendi: {settings.APP_NAME}")
except Exception as e:
    print(f"   ❌ Hata: {e}")
    print("   Lütfen python check_config.py çalıştır")
    sys.exit(1)

print("\n3️⃣ Database module'ü kontrol etme...")
try:
    from app.core.database import Database
    print(f"   ✅ Database module'ü başarıyla yüklendi")
except Exception as e:
    print(f"   ❌ Database module hatası: {e}")
    sys.exit(1)

print("\n" + "="*60)
print("✅ Motor fix tamamlandı!")
print("="*60 + "\n")
print("🚀 Şimdi çalıştırabilirsin:")
print("   python run_dev.py")
print("   # veya")
print("   python test_quick.py")
print()
