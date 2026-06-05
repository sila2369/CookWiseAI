#!/usr/bin/env python
"""
Auth Endpoints Test Script
"""

import requests
import json
import time

print('=' * 70)
print('🧪 CookWise Auth API - Endpoint Test')
print('=' * 70)

# Wait for server to be ready
time.sleep(2)

try:
    # ==================== 1️⃣ TEST REGISTER ====================
    print('\n1️⃣ POST /api/v1/auth/register')
    print('-' * 70)
    
    register_payload = {
        'full_name': 'John Doe',
        'email': 'john@example.com',
        'password': 'SecurePass123',
        'phone': '+905551234567'
    }
    
    print('Request:')
    print(json.dumps(register_payload, indent=2))
    
    response = requests.post(
        'http://localhost:8000/api/v1/auth/register',
        json=register_payload,
        timeout=5
    )
    
    print(f'\nResponse Status: {response.status_code}')
    response_data = response.json()
    print('Response:')
    print(json.dumps(response_data, indent=2, default=str))
    
    if response.status_code == 201:
        print('\n✅ Register endpoint working!')
    else:
        print(f'\n⚠️ Unexpected status code: {response.status_code}')
    
    
    # ==================== 2️⃣ TEST LOGIN ====================
    print('\n' + '=' * 70)
    print('2️⃣ POST /api/v1/auth/login')
    print('-' * 70)
    
    login_payload = {
        'email': 'john@example.com',
        'password': 'SecurePass123'
    }
    
    print('Request:')
    print(json.dumps(login_payload, indent=2))
    
    response = requests.post(
        'http://localhost:8000/api/v1/auth/login',
        json=login_payload,
        timeout=5
    )
    
    print(f'\nResponse Status: {response.status_code}')
    response_data = response.json()
    
    # Show response (but truncate token)
    if 'access_token' in response_data:
        response_data_display = response_data.copy()
        response_data_display['access_token'] = response_data_display['access_token'][:50] + '...'
        print('Response:')
        print(json.dumps(response_data_display, indent=2, default=str))
    else:
        print('Response:')
        print(json.dumps(response_data, indent=2, default=str))
    
    if response.status_code == 200:
        print('\n✅ Login endpoint working!')
        print(f'\n📊 Token Details:')
        print(f'   - Type: {response_data.get("token_type")}')
        print(f'   - Expires in: {response_data.get("expires_in")} seconds')
        print(f'   - User: {response_data.get("user", {}).get("full_name")}')
        print(f'   - Email: {response_data.get("user", {}).get("email")}')
    else:
        print(f'\n⚠️ Unexpected status code: {response.status_code}')
    
    
    # ==================== 3️⃣ TEST LOGIN ERROR (WRONG PASSWORD) ====================
    print('\n' + '=' * 70)
    print('3️⃣ POST /api/v1/auth/login (Wrong Password Test)')
    print('-' * 70)
    
    wrong_login = {
        'email': 'john@example.com',
        'password': 'WrongPassword123'
    }
    
    print('Request:')
    print(json.dumps(wrong_login, indent=2))
    
    response = requests.post(
        'http://localhost:8000/api/v1/auth/login',
        json=wrong_login,
        timeout=5
    )
    
    print(f'\nResponse Status: {response.status_code}')
    response_data = response.json()
    print('Response:')
    print(json.dumps(response_data, indent=2, default=str))
    
    if response.status_code == 401:
        print('\n✅ Error handling working! (401 Unauthorized for wrong password)')
    else:
        print(f'\n⚠️ Expected 401, got {response.status_code}')
    
    
    # ==================== 4️⃣ TEST DUPLICATE EMAIL ====================
    print('\n' + '=' * 70)
    print('4️⃣ POST /api/v1/auth/register (Duplicate Email Test)')
    print('-' * 70)
    
    duplicate_register = {
        'full_name': 'Jane Doe',
        'email': 'john@example.com',  # Same email!
        'password': 'AnotherPass123'
    }
    
    print('Request:')
    print(json.dumps(duplicate_register, indent=2))
    
    response = requests.post(
        'http://localhost:8000/api/v1/auth/register',
        json=duplicate_register,
        timeout=5
    )
    
    print(f'\nResponse Status: {response.status_code}')
    response_data = response.json()
    print('Response:')
    print(json.dumps(response_data, indent=2, default=str))
    
    if response.status_code == 409:
        print('\n✅ Duplicate email detection working! (409 Conflict)')
    else:
        print(f'\n⚠️ Expected 409, got {response.status_code}')
    
    
    print('\n' + '=' * 70)
    print('✅ All tests completed!')
    print('=' * 70)
    print('\n📚 Swagger UI: http://localhost:8000/docs')
    print('📚 ReDoc: http://localhost:8000/redoc')
    
except Exception as e:
    print(f'\n❌ Error: {type(e).__name__}: {e}')
    import traceback
    traceback.print_exc()
