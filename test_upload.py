import requests
import json
import time

BASE_URL = "https://ragbot-zwv0.onrender.com/api/v1"

def main():
    with open("upload_log.txt", "w", encoding="utf-8") as f:
        email = f"testUser{int(time.time())}@example.com"
        pwd = "Password123!"
        
        f.write(f"1. Registering: {email} / {pwd}\n")
        res = requests.post(f"{BASE_URL}/auth/register", json={"email": email, "password": pwd})
        if res.status_code not in (200, 201):
            f.write(f"Failed to register: {res.status_code} - {res.text}\n")
            return
            
        f.write("2. Logging in...\n")
        res = requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": pwd})
        if res.status_code != 200:
            f.write(f"Failed to login: {res.status_code} - {res.text}\n")
            return
            
        token = res.json()["access_token"]
        
        f.write("3. Uploading document...\n")
        headers = {"Authorization": f"Bearer {token}"}
        files = {"file": ("test.txt", b"This is a dummy document.", "text/plain")}
        
        res = requests.post(f"{BASE_URL}/documents/", headers=headers, files=files)
        f.write(f"Upload Status Code: {res.status_code}\n")
        f.write(f"Upload Response: {res.text}\n")

if __name__ == "__main__":
    main()
