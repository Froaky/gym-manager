import httpx
import re
import uuid

BASE_URL = "http://localhost:8000"
ADMIN_EMAIL = "admin@gym.com"
ADMIN_PASS = "admin123"

def run_verification():
    client = httpx.Client(base_url=BASE_URL, follow_redirects=True)
    
    # 1. Verify Admin Dashboard (Dynamic Stats)
    print("1. Checking Admin Dashboard...")
    resp = client.post("/auth/login", data={"email": ADMIN_EMAIL, "password": ADMIN_PASS})
    if resp.status_code != 200:
        print("FAILED: Admin login.")
        return
        
    if "vs mes anterior" in resp.text:
        print("SUCCESS: Dashboard loaded with stats text.")
    else:
        print("WARNING: 'vs mes anterior' text not found in dashboard. Check template rendering.")
        
    if "trend-up" in resp.text or "trend-down" in resp.text:
        print("SUCCESS: Dynamic trend classes found.")
    else:
        print("WARNING: Dynamic trend classes not found.")

    # 2. Setup User and Routine for Permission Check
    print("\n2. Setting up User and Routine...")
    user_email = f"user_{uuid.uuid4().hex[:6]}@test.com"
    user_pass = "password123"
    
    # Create User
    client.post("/users/new", data={"name": "Perm Test User", "email": user_email, "password": user_pass})
    
    # Get User ID (Need to be admin)
    # Re-login as admin just in case
    client.post("/auth/login", data={"email": ADMIN_EMAIL, "password": ADMIN_PASS})
    
    # Create Routine 1 (Assigned)
    routine_name_1 = f"My Routine {uuid.uuid4().hex[:4]}"
    client.post("/routines/new", data={"name": routine_name_1, "description": "Allowed"})
    
    # Create Routine 2 (Unassigned)
    routine_name_2 = f"Other Routine {uuid.uuid4().hex[:4]}"
    client.post("/routines/new", data={"name": routine_name_2, "description": "Denied"})
    
    # We need IDs. This is hard without parsing HTML list.
    # Let's hope the list is ordered or we can grep.
    # Actually, let's use the verify_gym.py approach or just parse loosely.
    
    # Fetch lists to find IDs
    routines_resp = client.get("/routines")
    # Finding IDs for routine_name_1 and routine_name_2
    # <a href="/routines/(\d+)">Routine Name</a>
    
    # The structure is <td><span class="routine-name">Name</span></td> ... <a href="/routines/ID">
    # We need to use DOTALL to match across newlines
    
    r1_match = re.search(f'<span class="routine-name">{routine_name_1}</span>.*?href="/routines/(\\d+)"', routines_resp.text, re.DOTALL)
    r2_match = re.search(f'<span class="routine-name">{routine_name_2}</span>.*?href="/routines/(\\d+)"', routines_resp.text, re.DOTALL)
    
    if not r1_match or not r2_match:
        print("FAILED: Could not find created routines in list (Regex failed).")
        # print(routines_resp.text) # Uncomment for debug
        return
        
    r1_id = r1_match.group(1)
    r2_id = r2_match.group(1)
    print(f"   Routine 1 ID: {r1_id}")
    print(f"   Routine 2 ID: {r2_id}")

    # Find User ID
    users_resp = client.get("/users")
    # <a href="/users/(\d+)"[^>]*>...user_email...</a>
    # The list might use name.
    # Let's assume the user is there.
    # Try finding by name "Perm Test User"
    u_match = re.search(r'href="/users/(\d+)".*Perm Test User', users_resp.text)
    if not u_match:
         print("FAILED: Could not find created user in list.")
         # fallback: search by email if visible
         # return
    else:
        u_id = u_match.group(1)
        print(f"   User ID: {u_id}")

        # Assign Routine 1 to User
        print("3. Assigning Routine 1 to User...")
        resp = client.post("/routines/assign", data={"user_id": u_id, "routine_id": r1_id})
        if resp.status_code == 200:
            print("SUCCESS: Routine assigned.")
        else:
            print(f"FAILED: Assignment returned {resp.status_code}")

    # 3. Verify Permissions as User
    print("\n4. Verifying Permissions as User...")
    user_client = httpx.Client(base_url=BASE_URL, follow_redirects=False) # No redirects to see 303
    
    # Login
    resp = user_client.post("/auth/login", data={"email": user_email, "password": user_pass})
    
    # Handle Password Change if needed
    if resp.status_code == 303 and "/auth/change-password" in resp.headers.get("location"):
         print("   (Changing password...)")
         user_client.follow_redirects = True
         user_client.post("/auth/change-password", data={"new_password": "newpass", "confirm_password": "newpass"})
         user_client.follow_redirects = False
    
    # Access Routine 1 (Should be allowed -> 200 OK)
    print(f"   Accessing Routine {r1_id} (Assigned)...")
    r1_resp = user_client.get(f"/routines/{r1_id}")
    if r1_resp.status_code == 200:
        print("SUCCESS: User can view assigned routine.")
    else:
        print(f"FAILED: User cannot view assigned routine. Status: {r1_resp.status_code}")

    # Access Routine 2 (Should be denied -> 303 Redirect to / or 403)
    print(f"   Accessing Routine {r2_id} (Unassigned)...")
    r2_resp = user_client.get(f"/routines/{r2_id}")
    if r2_resp.status_code == 303:
        loc = r2_resp.headers.get("location")
        if loc == "/" or loc == "http://localhost:8000/":
             print("SUCCESS: User redirected to home when accessing unassigned routine.")
        else:
             print(f"WARNING: User redirected to {loc}")
    elif r2_resp.status_code == 403:
        print("SUCCESS: User access denied (403).")
    else:
        print(f"FAILED: User COULD access unassigned routine! Status: {r2_resp.status_code}")

if __name__ == "__main__":
    run_verification()
