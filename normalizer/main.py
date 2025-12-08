import os
import subprocess
import sys

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NORMALIZER_DIR = os.path.join(BASE_DIR, "normalizer")
DATA_NORMALIZED = os.path.join(BASE_DIR, "data", "normalized")

SCRIPTS = [
    "normalize_ec2.py",
    "normalize_rds.py",
    "normalize_s3.py"
]

def main():
    if not os.path.exists(DATA_NORMALIZED):
        os.makedirs(DATA_NORMALIZED)

    print("Starting Normalization Engine...")
    
    for script in SCRIPTS:
        script_path = os.path.join(NORMALIZER_DIR, script)
        print(f"\n--- Running {script} ---")
        try:
            # Run in separate process to clear memory fully
            subprocess.run([sys.executable, script_path], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error running {script}: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")

    print("\nNormalization Complete.")

if __name__ == "__main__":
    main()
