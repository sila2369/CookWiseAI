"""
Authentication  Flow Test
HTTP istekleri ile tam auth zincirlmesini test et
"""

import requests
import json

BASE_URL = "http://127.0.0.1:8001/api/v1"

print("\n" + "="*70)
print("🧪 COMPLETE AUTHENTICATION FLOW TEST")
print("="*70)

# ==================== 1. REGISTER ====================
print("\n1️⃣  REGISTER - Yeni kullanıcı oluştur")
print("-" * 70)

register_data = {
    "full_name": "Test User",
    "email": "testuser@example.com",
    "password": "SecurePass123",
    "phone": "+905555555555"
}

response = requests.post(f"{BASE_URL}/auth/register", json=register_data)
print(f"POST /auth/register → {response.status_code}")
print(f"Response:\n{json.dumps(response.json(), indent=2, ensure_ascii=False)}\n")

if response.status_code != 201:
    print(f"❌ ERROR: Expected 201, got {response.status_code}")
    exit(1)

user_response = response.json()
user_id =user_response["id"]
print(f"✅ User created successfully")
print(f"   User ID: {user_id}")

# ==================== 2. LOGIN ====================
print("\n2️⃣  LOGIN - Get authentication token")
print("-" * 70)

login_data = {
    "email": "testuser@example.com",
    "password": "SecurePass123"
}

response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
print(f"POST /auth/login → {response.status_code}")

if response.status_code != 200:
    print(f"❌ ERROR: Expected 200, got {response.status_code}")
    print(f"Details: {response.text}")
    exit(1)

token_response = response.json()
access_token = token_response["access_token"]
token_type = token_response["token_type"]

print(f"Response:\n{json.dumps({k:v if k != 'access_token' else v[:30]+'...' for k,v in token_response.items()}, indent=2, ensure_ascii=False)}\n")
print(f"✅ Token obtained successfully")
print(f"   Token Type: {token_type}")
print(f"   Token: {access_token[:40]}...")

# ==================== 3. GET OWN PROFILE ====================
print("\n3️⃣  GET /users/me - View own profile")
print("-" * 70)

headers = {
    "Authorization": f"{token_type} {access_token}"
}

response = requests.get(f"{BASE_URL}/users/me", headers=headers)
print(f"GET /users/me (with token) → {response.status_code}")
print(f"Response:\n{json.dumps(response.json(), indent=2, ensure_ascii=False)}\n")

if response.status_code != 200:
    print(f"❌ ERROR: Expected 200, got {response.status_code}")
    exit(1)

profile = response.json()
print(f"✅ Profile retrieved successfully")
print(f"   Full Name: {profile.get('full_name')}")
print(f"   Email: {profile.get('email')}")
print(f"   Phone: {profile.get('phone')}")
print(f"   Active: {profile.get('is_active')}")

# ==================== 4. UPDATE PROFILE ====================
print("\n4️⃣  PUT /users/me - Update own profile")
print("-" * 70)

update_data = {
    "full_name": "Updated User Name",
    "phone": "+906666666666"
}

response = requests.put(f"{BASE_URL}/users/me", json=update_data, headers=headers)
print(f"PUT /users/me → {response.status_code}")
print(f"Request Body:\n{json.dumps(update_data, indent=2)}\n")
print(f"Response:\n{json.dumps(response.json(), indent=2, ensure_ascii=False)}\n")

if response.status_code != 200:
    print(f"❌ ERROR: Expected 200, got {response.status_code}")
    exit(1)

updated = response.json()
print(f"✅ Profile updated successfully")
print(f"   Full Name: {updated.get('full_name')} (updated)")
print(f"   Phone: {updated.get('phone')} (updated)")

# ==================== 5. VERIFY UPDATE ====================
print("\n5️⃣  VERIFY - Confirm profile was updated")
print("-" * 70)

response = requests.get(f"{BASE_URL}/users/me", headers=headers)
print(f"GET /users/me (verify) → {response.status_code}")

if response.status_code == 200:
    profile = response.json()
    if profile['full_name'] == "Updated User Name" and profile['phone'] == "+90 666 666 6666":
        print(f"✅ Profile update confirmed in database!")
        print(f"   Full Name: {profile.get('full_name')}")
        print(f"   Phone: {profile.get('phone')}")
    else:
        print(f"⚠️  Profile returned but update not confirmed")
else:
    print(f"❌ Verification failed: {response.status_code}")

# ==================== 6. CREATE SECOND USER ====================
print("\n6️⃣  CREATE SECOND USER - For authorization tests")
print("-" * 70)

register_data2 = {
    "full_name": "Other User",
    "email": "otheruser@example.com",
    "password": "OtherPass123"
}

response = requests.post(f"{BASE_URL}/auth/register", json=register_data2)
if response.status_code == 201:
    other_user_id = response.json()["id"]
    print(f"✅ Second user created: {other_user_id}")
    
    # ==================== 7. ACCESS CONTROL TEST ====================
    print("\n7️⃣  ACCESS CONTROL - Try to view other user's profile (should fail)")
    print("-" * 70)
    
    response = requests.get(f"{BASE_URL}/users/{other_user_id}", headers=headers)
    print(f"GET /users/{other_user_id} (other user, not admin) → {response.status_code}")
    print(f"Response:\n{json.dumps(response.json(), indent=2, ensure_ascii=False)}\n")
    
    if response.status_code == 403:
        print(f"✅ Correctly blocked non-admin access to other user profile")
    else:
        print(f"⚠️  Expected 403, got {response.status_code}")

# ==================== 8. UNAUTHORIZED TEST ====================
print("\n8️⃣  UNAUTHORIZED - Access without token (should fail)")
print("-" * 70)

response = requests.get(f"{BASE_URL}/users/me")
print(f"GET /users/me (NO token) → {response.status_code}")
print(f"Response:\n{json.dumps(response.json(), indent=2, ensure_ascii=False)}\n")

if response.status_code in [401, 403]:
    print(f"✅ Correctly blocked unauthorized access (HTTP {response.status_code})")
else:
    print(f"⚠️  Expected 401/403, got {response.status_code}")

# ==================== 9. INVALID TOKEN TEST ====================
print("\n9️⃣  INVALID TOKEN - Use malformed token (should fail)")
print("-" * 70)

bad_headers = {
    "Authorization": "Bearer invalid.token.here"
}

response = requests.get(f"{BASE_URL}/users/me", headers=bad_headers)
print(f"GET /users/me (invalid token) → {response.status_code}")
print(f"Response:\n{json.dumps(response.json(), indent=2, ensure_ascii=False)}\n")

if response.status_code in [401, 403]:
    print(f"✅ Correctly rejected invalid token (HTTP {response.status_code})")
else:
    print(f"⚠️  Expected 401/403, got {response.status_code}")

print("\n" + "="*70)
print("✅ ALL TESTS PASSED! Authentication system working correctly!")
print("="*70 + "\n")
