import requests
import json
import sys

BASE_URL = "http://localhost:8000/api/pricing"

def run_test(name, url, expected_status=200):
    print(f"--- TEST: {name} ---")
    print(f"GET {url}")
    try:
        res = requests.get(url)
        print(f"Status: {res.status_code}")
        if res.status_code != expected_status:
            print(f"FAIL: Expected {expected_status}, got {res.status_code}")
            try:
                 print(res.json())
            except:
                 print(res.text)
            return False
            
        try:
            data = res.json()
            # print(json.dumps(data, indent=2)[:500] + "...")
            if isinstance(data, list):
                print(f"Received list with {len(data)} items")
            elif isinstance(data, dict):
                 print(f"Received dict keys: {list(data.keys())}")
                 if 'items' in data:
                     print(f"Items count: {len(data['items'])}")
                     if len(data['items']) > 0:
                         print("Sample Item:", data['items'][0])
                 if 'instanceTypes' in data:
                     print(f"Instance Types count: {len(data['instanceTypes'])}")
            
            print("PASS")
            return True
        except Exception as e:
            print(f"FAIL: Not valid JSON - {e}")
            return False
            
    except Exception as e:
        print(f"FAIL: Connection Error - {e}")
        return False

def main():
    print("Verifying Backend Endpoints...")
    
    # Test 1: Metadata
    if not run_test("EC2 Metadata", f"{BASE_URL}/metadata/ec2"):
        print("Skipping further tests due to metadata failure")
        # Don't exit, might be a partial failure
        
    # Test 2: Catalog (No Filter)
    run_test("EC2 Catalog (Page 1)", f"{BASE_URL}/catalog/ec2?page=1&pageSize=5")
    
    # Test 3: Catalog (Filter)
    # We need a valid location from metadata to test this properly, but let's guess standard AWS
    run_test("EC2 Catalog (Filter Location)", f"{BASE_URL}/catalog/ec2?location=US East (N. Virginia)&pageSize=5")

if __name__ == "__main__":
    main()
