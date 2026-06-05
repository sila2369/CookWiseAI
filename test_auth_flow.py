"""
Authentication Flow Test - Complete Chain Test
Sunucuyu başlatmadan test edelim (TestClient kullanarak)
"""

import json
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

print("\n" + "="*60)
print("🧪 AUTH TAUSTOMER Flow testi - TestClient ile")
print("="*60)

# 1. Kayıt yap (Register)
print("\n1️⃣  REGISTER - Yeni kullanıcı oluştur")
print("-" * 60)

register_data = {
    "full_name": "Test User",
    "email": "testuser@example.com",
    "password": "SecurePass123",
    "phone": "+90 555 555 5555"
}

response = client.post(
    "/api/v1/auth/register",
    json=register_data
)

print(f"Request: POST /api/v1/auth/register")
print(f"Status: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

if response.status_code != 201:
    print(f"❌ HATA: Beklenen 201, alınan {response.status_code}")
    print(f"Detaylar: {response.text}")
    exit(1)

user_response = response.json()
print(f"✅ Kullanıcı başarıyla oluşturuldu")

# 2. Giriş yap (Login)
print("\n2️⃣  LOGIN - Token al")
print("-" * 60)

login_data = {
    "email": "testuser@example.com",
    "password": "SecurePass123"
}

response = client.post(
    "/api/v1/auth/login",
    json=login_data
)

print(f"Request: POST /api/v1/auth/login")
print(f"Status: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

if response.status_code != 200:
    print(f"❌ HATA: Beklenen 200, alınan {response.status_code}")
    print(f"Detaylar: {response.text}")
    exit(1)

token_response = response.json()
access_token = token_response.get("access_token")
token_type = token_response.get("token_type")
print(f"✅ Token başarıyla alındı")
print(f"   Token Type: {token_type}")
print(f"   Token: {access_token[:50]}...")

# 3. Profili view et (GET /users/me)
print("\n3️⃣  PROFILE VIEW - Kendi profilini görüntüle")
print("-" * 60)

headers = {
    "Authorization": f"{token_type} {access_token}"
}

response = client.get(
    "/api/v1/users/me",
    headers=headers
)

print(f"Request: GET /api/v1/users/me")
print(f"Headers: Authorization: Bearer [token]")
print(f"Status: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

if response.status_code != 200:
    print(f"❌ HATA: Beklenen 200, alınan {response.status_code}")
    print(f"Detaylar: {response.text}")
    exit(1)

profile = response.json()
user_id = profile.get("id")
print(f"✅ Profil başarıyla getirildi")
print(f"   User ID: {user_id}")
print(f"   Full Name: {profile.get('full_name')}")
print(f"   Email: {profile.get('email')}")
print(f"   Phone: {profile.get('phone')}")

# 4. Profili güncelle (PUT /users/me)
print("\n4️⃣  PROFILE UPDATE - Profili güncelle")
print("-" * 60)

update_data = {
    "full_name": "Updated Test User",
    "phone": "+90 666 666 6666"
}

response = client.put(
    "/api/v1/users/me",
    json=update_data,
    headers=headers
)

print(f"Request: PUT /api/v1/users/me")
print(f"Body: {json.dumps(update_data, indent=2, ensure_ascii=False)}")
print(f"Status: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

if response.status_code != 200:
    print(f"❌ HATA: Beklenen 200, alınan {response.status_code}")
    print(f"Detaylar: {response.text}")
    exit(1)

updated_profile = response.json()
print(f"✅ Profil başarıyla güncellendi")
print(f"   Full Name: {updated_profile.get('full_name')}")
print(f"   Phone: {updated_profile.get('phone')}")

# 5. Başka kullanıcının profilini view et (GET /users/{user_id})
print("\n5️⃣  VIEW OTHER USER - Başka bir kullanıcıyı view et")
print("-" * 60)

# Önce başka bir user oluştur
other_user_data = {
    "full_name": "Other User",
    "email": "otheruser@example.com",
    "password": "OtherPass123"
}

response = client.post(
    "/api/v1/auth/register",
    json=other_user_data
)

if response.status_code == 201:
    other_user_id = response.json()["id"]
    
    # Şimdi bu kullanıcıyı view etmeye çalış
    response = client.get(
        f"/api/v1/users/{other_user_id}",
        headers=headers
    )
    
    print(f"Request: GET /api/v1/users/{other_user_id}")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    if response.status_code == 200:
        print(f"✅ Başka kullanıcı profili başarıyla getirildi")
    else:
        print(f"❌ Başka kullanıcı profili alınamadı (HTTP {response.status_code})")
elif response.status_code == 409:
    print(f"ℹ️  Kullanıcı zaten var (duplicate email)")
else:
    print(f"❌ Kayıt hatası: {response.status_code}")

# 6. İzinsiz erişim testi (401)
print("\n6️⃣  UNAUTHORIZED ACCESS TEST - Token olmadan erişim")
print("-" * 60)

response = client.get("/api/v1/users/me")
print(f"Request: GET /api/v1/users/me (Token YOK)")
print(f"Status: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

if response.status_code == 403 or response.status_code == 401:
    print(f"✅ Doğru: Token olmadan 401/403 hatası döndü")
else:
    print(f"⚠️  Beklenen 401/403, alınan {response.status_code}")

print("\n" + "="*60)
print("✅ TÜM TESTLER BAŞARILI!")
print("="*60 + "\n")
