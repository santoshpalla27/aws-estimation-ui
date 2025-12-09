from locust import HttpUser, task, between
import random

class EstimateUser(HttpUser):
    wait_time = between(1, 3)
    
    @task(3)
    def estimate_ec2(self):
        payload = {
            "instanceType": "t3.micro",
            "location": "US East (N. Virginia)",
            "operatingSystem": "Linux",
            "hours": 730,
            "count": 1
        }
        self.client.post("/api/estimate/ec2", json=payload, name="/api/estimate/ec2")
        
    @task(1)
    def estimate_s3(self):
         payload = {
            "storageGB": 100,
            "storageClass": "Standard",
            "location": "US East (N. Virginia)"
         }
         self.client.post("/api/estimate/s3", json=payload, name="/api/estimate/s3")

    @task(1)
    def get_services(self):
        self.client.get("/api/services", name="/api/services")
