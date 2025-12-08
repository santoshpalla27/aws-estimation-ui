import os
import requests
from tqdm import tqdm

# AWS Pricing API Endpoint
BASE_URL = "https://pricing.us-east-1.amazonaws.com"
OFFERS_URL = f"{BASE_URL}/offers/v1.0/aws/{{}}/current/index.json"

# Comprehensive Service List provided by user and standards
# We use the Offer Code as the key identifier
SERVICE_CODES = [
    "AmazonEC2",
    "AmazonES", # OpenSearch
    "ACM", # AWS Certificate Manager
    "AmazonApiGateway",
    "AmazonCloudFront",
    "AmazonCloudWatch",
    "AWSCloudTrail",
    "AmazonDynamoDB",
    "AmazonECR",
    "AmazonECRPublic",
    "AmazonECS",
    "AmazonEFS",
    "AmazonEKS",
    "AmazonElastiCache",
    "AmazonMQ",
    "AmazonMSK",
    "AmazonRDS",
    "AmazonRoute53",
    "AmazonS3",
    "AmazonS3GlacierDeepArchive",
    "AmazonSNS",
    "AmazonStates", # Step Functions
    "AmazonVPC",
    "AWSCloudFormation",
    "AWSCodeArtifact",
    "CodeBuild", # User provided 'CodeBuild', usually AWSCodeBuild, we will try both or just this
    "AWSCodeCommit",
    "AWSCodeDeploy",
    "AWSCodePipeline",
    "AWSConfig",
    "AWSELB", # Elastic Load Balancing (Classic? Or generic?)
    "AWSElasticDisasterRecovery",
    "AWSEvents",
    "awskms", # will title case this if needed, usually uppercase
    "AWSLambda",
    "AWSQueueService", # SQS
    "AWSSecretsManager",
    "AWSServiceCatalog",
    "AWSShield",
    "AWSSystemsManager",
    "AWSXRay",
    "awswaf",
    "AmazonSES",
    "AmazonPinpoint",
    "AmazonKinesis",
    "AmazonFSx",
    "AWSBackup",
    "AWSDataTransfer",
    "AWSGlobalAccelerator",
    "AWSFMS"
]

# Ensure uniqueness and formatting
SERVICE_CODES = sorted(list(set(SERVICE_CODES)))

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "raw")

def download_file(url, filename):
    try:
        response = requests.get(url, stream=True)
        if response.status_code == 404:
             # Try Common variations if 404?
             # e.g. CodeBuild -> AWSCodeBuild
             print(f"  [404] Not Found: {url}")
             return False
        if response.status_code != 200:
            print(f"  [Error] Status {response.status_code} for {url}")
            return False

        total_size = int(response.headers.get('content-length', 0))
        block_size = 1024 * 1024 # 1MB

        print(f"  Downloading ({total_size // (1024*1024)} MB)...")
        
        with open(filename, 'wb') as file, tqdm(
            desc=os.path.basename(filename),
            total=total_size,
            unit='iB',
            unit_scale=True,
            unit_divisor=1024,
            leave=False
        ) as bar:
            for data in response.iter_content(block_size):
                size = file.write(data)
                bar.update(size)
        return True
    except Exception as e:
        print(f"  [Exception] {str(e)}")
        return False

def main():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    print(f"Starting download for {len(SERVICE_CODES)} services...")
    
    success_count = 0
    fail_count = 0

    for code in SERVICE_CODES:
        # url
        url = OFFERS_URL.format(code)
        # filename: lowercase for consistency
        filename = os.path.join(DATA_DIR, f"{code.lower()}_pricing.json")
        
        print(f"Processing {code}...")
        
        if os.path.exists(filename):
            print(f"  File exists: {filename} (Skipping)")
            success_count += 1
            continue
            
        if download_file(url, filename):
            print(f"  Saved: {filename}")
            success_count += 1
        else:
            # Retry logic or variation check?
            # Example: 'CodeBuild' might be 'AWSCodeBuild'
            if not code.startswith('AWS') and not code.startswith('Amazon'):
                alt_code = f"AWS{code}"
                print(f"  Retrying with {alt_code}...")
                alt_url = OFFERS_URL.format(alt_code)
                if download_file(alt_url, filename): # Save to original name usually? Or update?
                     print(f"  Saved: {filename} (using {alt_code})")
                     success_count += 1
                else:
                     fail_count += 1
            else:
                fail_count += 1

    print(f"\nDownload Complete.")
    print(f"Success: {success_count}")
    print(f"Failed: {fail_count}")

if __name__ == "__main__":
    main()
