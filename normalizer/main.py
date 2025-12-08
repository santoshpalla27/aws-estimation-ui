import os
import subprocess
import sys
import glob
import json
import importlib.util

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NORMALIZER_DIR = os.path.join(BASE_DIR, "normalizer")
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
NORMALIZED_DIR = os.path.join(BASE_DIR, "data", "normalized")
METADATA_FILE = os.path.join(BASE_DIR, "data", "service_metadata.json")

# Import normalizers
sys.path.append(NORMALIZER_DIR)
import normalize_generic

def get_specific_normalizer(service_name):
    script_name = f"normalize_{service_name}.py"
    script_path = os.path.join(NORMALIZER_DIR, script_name)
    if os.path.exists(script_path):
        return script_name
    return None

def generate_metadata_summary():
    print("\nGenerating Service Metadata Summary...")
    summary = {}
    
    files = glob.glob(os.path.join(NORMALIZED_DIR, "*.json"))
    for fpath in files:
        fname = os.path.basename(fpath)
        service = fname.replace(".json", "")
        
        try:
            with open(fpath, 'r') as f:
                # Read first few items to detect schema
                # large files? json.load reads all. 
                # For summary, we might accept reading all or stream.
                data = json.load(f)
                if not data:
                    continue
                
                regions = set()
                attribute_keys = set()
                
                for item in data:
                    if "region" in item:
                        regions.add(item["region"])
                    
                    # Generic stores in 'attributes' dict
                    if "attributes" in item and isinstance(item["attributes"], dict):
                        attribute_keys.update(item["attributes"].keys())
                    else:
                        # Specific normalizers (EC2/RDS) have flat keys
                        attribute_keys.update(item.keys())
                
                summary[service] = {
                    "regions": sorted(list(regions)),
                    "attributes": sorted(list(attribute_keys)),
                    "count": len(data)
                }
        except Exception as e:
            print(f"  Error processing metadata for {service}: {e}")
            
    with open(METADATA_FILE, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"Saved metadata summary to {METADATA_FILE}")

def main():
    if not os.path.exists(NORMALIZED_DIR):
        os.makedirs(NORMALIZED_DIR)

    print("Starting Normalization Engine...")
    
    # Find all downloaded raw pricing files
    raw_files = glob.glob(os.path.join(RAW_DIR, "*_pricing.json"))
    
    for raw_file in raw_files:
        filename = os.path.basename(raw_file)
        # format: {service}_pricing.json -> service
        # e.g. amazonec2_pricing.json -> amazonec2
        service_name = filename.replace("_pricing.json", "")
        output_file = os.path.join(NORMALIZED_DIR, f"{service_name}.json")
        
        print(f"\nProcessing {service_name}...")
        
        # Mapping: Downloader uses 'amazonec2', Normalizer script is 'normalize_ec2.py'
        # We need to try mapping 'amazonec2' -> 'ec2' if direct match failing looks likely
        # Actually 'normalize_amazonec2.py' doesn't exist.
        
        target_script = None
        
        # 1. Try exact name (e.g. normalize_awsbackup.py if we had one)
        if get_specific_normalizer(service_name):
            target_script = get_specific_normalizer(service_name)
        
        # 2. Try removing 'amazon' or 'aws' prefix
        if not target_script:
            if service_name.startswith("amazon"):
                short_name = service_name.replace("amazon", "")
                if get_specific_normalizer(short_name):
                    target_script = get_specific_normalizer(short_name)
            elif service_name.startswith("aws"):
                short_name = service_name.replace("aws", "")
                if get_specific_normalizer(short_name):
                    target_script = get_specific_normalizer(short_name)
                    
        if target_script:
            print(f"  Using Specific Normalizer: {target_script}")
            try:
                # Pass raw_file and output_file as arguments
                subprocess.run([sys.executable, os.path.join(NORMALIZER_DIR, target_script), raw_file, output_file], check=True)
            except Exception as e:
                print(f"  Error: {e}")
        else:
            print(f"  Using Generic Normalizer")
            try:
                normalize_generic.normalize_generic(service_name, raw_file, output_file)
            except Exception as e:
                print(f"  Error: {e}")

    # After all valid files are processed
    generate_metadata_summary()
    print("\nNormalization Complete.")

if __name__ == "__main__":
    main()
