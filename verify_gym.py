import httpx
import re
import uuid

BASE_URL = "http://localhost:8000"
ADMIN_EMAIL = "admin@gym.com"
ADMIN_PASS = "admin123"

def run_verification():
    client = httpx.Client(base_url=BASE_URL, follow_redirects=True)
    
    print("1. Logging in as Admin...")
    resp = client.post("/auth/login", data={"email": ADMIN_EMAIL, "password": ADMIN_PASS})
    if resp.status_code != 200:
        print(f"FAILED: Admin login. Status: {resp.status_code}")
        return
    print("SUCCESS: Admin logged in.")

    # Create a unique user for testing
    user_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    user_pass = "password123"
    print(f"2. Creating test user: {user_email}")
    resp = client.post("/users/new", data={
        "name": "Test User",
        "email": user_email,
        "password": user_pass
    })
    if resp.status_code != 200:
        print(f"FAILED: Create user. Status: {resp.status_code}")
        return
    print("SUCCESS: User created.")
    
    # Get User ID from the list page (we are redirected there)
    # This is a bit tricky parsing HTML with regex, but let's try to find the user link
    # The list page has <a href="/users/{id}" ...>{name}</a>
    # We can also fetch the user list again to be sure
    resp = client.get("/users")
    # Search for our email or name, then find the link nearby
    # Or simplified: since we just created it, it might be the last one, or we can look for the email in the page
    if user_email not in resp.text:
        print("FAILED: New user not found in list.")
        return
        
    print("SUCCESS: User found in list.")
    
    # Extract User ID (rough approx)
    # Looking for: href="/users/(\d+)" ... test_...@example.com
    # HTML structure might be complex, let's assume we can login as the user later to check QR
    # BUT we need ID to assign routine.
    # Let's try to find the ID from the profile link associated with the name/email
    # Assuming some proximity. 
    # Let's use a simpler approach: access the DB directly? No, let's stick to HTTP.
    # Using SQLModel to get the user ID using a separate script connection would be cleaner but let's try to parse.
    
    # Simple regex scrape for the ID
    # <td ...>test_...@example.com</td> ... <a href="/users/(\d+)"
    # This depends on table structure. 
    # Let's try to get the profile page of the newly created user:
    # Actually, let's create a Helper Routine first.
    
    print("3. Creating a Routine...")
    routine_name = f"Routine {uuid.uuid4().hex[:4]}"
    resp = client.post("/routines/new", data={"name": routine_name, "description": "Test Routine"})
    if resp.status_code != 200:
        print(f"FAILED: Create routine. Status: {resp.status_code}")
        return
    print("SUCCESS: Routine created.")
    
    # We need Routine ID too. 
    # If I cannot parse IDs easily, I might fail to assign.
    # Let's try a different approach: verify QR code first (Login as user).
    
    print("4. Verifying QR Code logic (User side)...")
    user_client = httpx.Client(base_url=BASE_URL, follow_redirects=True)
    resp = user_client.post("/auth/login", data={"email": user_email, "password": user_pass})
    
    # Handle Forced Password Change
    if "/auth/change-password" in str(resp.url):
        print("   (Changing default password...)")
        resp = user_client.post("/auth/change-password", data={
            "new_password": "newpassword123",
            "confirm_password": "newpassword123"
        })
    
    if "dashboard" not in resp.text and "Mi Panel" not in resp.text:
        print(f"FAILED: User login failed or not on dashboard. Url: {resp.url}")
        # print(resp.text[:500])
        return
        
    # Check QR Code
    # Look for: https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=...
    match = re.search(r'data=([^"&\s]+)', resp.text)
    if match:
        qr_data = match.group(1)
        print(f"   Found QR Data: {qr_data}")
        if "@" in qr_data:
            print("FAILED: QR Code contains email (old behavior)!")
        else:
            try:
                uuid_obj = uuid.UUID(qr_data)
                print("SUCCESS: QR Code contains a valid UUID.")
            except ValueError:
                print(f"WARNING: QR Code data '{qr_data}' is not a UUID, but does not look like an email.")
    else:
        print("FAILED: Could not find QR code image in dashboard.")

    print("\nVerification Complete.")

if __name__ == "__main__":
    run_verification()
