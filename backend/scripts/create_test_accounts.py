import requests
import json

API_URL = "http://localhost:8000"

# Test accounts to create
test_accounts = [
    {
        "register_number": "RA2311047010001",
        "name": "Test Student 1",
        "email": "test1@jobswipe.com",
        "password": "Test123"
    },
    {
        "register_number": "RA2311047010002",
        "name": "Test Student 2",
        "email": "test2@jobswipe.com",
        "password": "Test123"
    },
    {
        "register_number": "RA2311047010003",
        "name": "Test Student 3",
        "email": "test3@jobswipe.com",
        "password": "Test123"
    }
]

print("🔐 Creating test accounts...\n")

for account in test_accounts:
    try:
        response = requests.post(
            f"{API_URL}/auth/signup",
            json=account,
            timeout=5
        )
        
        if response.status_code == 200:
            print(f"✅ Created: {account['register_number']}")
            print(f"   Name: {account['name']}")
            print(f"   Password: {account['password']}")
            print()
        elif response.status_code == 400:
            print(f"⚠️  {account['register_number']} already exists\n")
        else:
            print(f"❌ Error creating {account['register_number']}: {response.text}\n")
        
    except Exception as e:
        print(f"❌ Error creating {account['register_number']}: {str(e)}\n")

print("\n" + "="*60)
print("🎯 TEST ACCOUNTS - USE THESE TO LOGIN:")
print("="*60)
print("\nRegister Number: RA2311047010001")
print("Password: Test123")
print("\nRegister Number: RA2311047010002")
print("Password: Test123")
print("\nRegister Number: RA2311047010003")
print("Password: Test123")
print("\n" + "="*60)

