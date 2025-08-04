#!/usr/bin/env python3
"""
Example usage of the Flask scraping app
"""

import requests
import json
import time
from datetime import datetime

class ScrapingAppClient:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def health_check(self):
        """Check if the app is running"""
        try:
            response = self.session.get(f"{self.base_url}/health")
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            print(f"Health check failed: {e}")
            return None
    
    def start_scraping(self, business_name, business_url, google_maps_url, trustpilot_url):
        """Start a scraping job"""
        data = {
            "business_name": business_name,
            "business_url": business_url,
            "google_maps_url": google_maps_url,
            "trustpilot_url": trustpilot_url
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/scrape",
                json=data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                return response.json().get('job_id')
            else:
                print(f"Failed to start scraping: {response.text}")
                return None
        except Exception as e:
            print(f"Error starting scraping: {e}")
            return None
    
    def get_job_status(self, job_id):
        """Get the status of a scraping job"""
        try:
            response = self.session.get(f"{self.base_url}/status/{job_id}")
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            print(f"Error getting job status: {e}")
            return None
    
    def get_job_results(self, job_id):
        """Get the results of a completed scraping job"""
        try:
            response = self.session.get(f"{self.base_url}/results/{job_id}")
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            print(f"Error getting job results: {e}")
            return None
    
    def wait_for_completion(self, job_id, timeout=600, check_interval=10):
        """Wait for a job to complete"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status_data = self.get_job_status(job_id)
            
            if not status_data:
                print("Failed to get job status")
                return False
            
            status = status_data.get('status', 'unknown')
            progress = status_data.get('progress', 0)
            
            print(f"Job {job_id}: {status} ({progress}%)")
            
            if status == 'completed':
                print("Job completed successfully!")
                return True
            elif status == 'failed':
                print(f"Job failed: {status_data.get('error', 'Unknown error')}")
                return False
            
            time.sleep(check_interval)
        
        print(f"Job timed out after {timeout} seconds")
        return False
    
    def list_jobs(self):
        """List all scraping jobs"""
        try:
            response = self.session.get(f"{self.base_url}/jobs")
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            print(f"Error listing jobs: {e}")
            return None
    
    def cleanup_old_jobs(self, max_age_hours=24):
        """Clean up old completed jobs"""
        try:
            response = self.session.post(
                f"{self.base_url}/cleanup",
                json={"max_age_hours": max_age_hours},
                headers={"Content-Type": "application/json"}
            )
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            print(f"Error cleaning up jobs: {e}")
            return None

def example_usage():
    """Example usage of the scraping app"""
    
    # Initialize the client
    client = ScrapingAppClient()
    
    # Check if the app is running
    print("Checking app health...")
    health = client.health_check()
    if not health:
        print("App is not running. Please start the Flask app first.")
        return
    
    print(f"App is healthy: {health}")
    
    # Example business data
    business_data = {
        "business_name": "Primal Queen",
        "business_url": "https://primalqueen.com/",
        "google_maps_url": "https://www.google.com/maps/place/Primal+Queen/@40.7128,-74.0060,17z/",
        "trustpilot_url": "https://www.trustpilot.com/review/primalqueen.com"
    }
    
    # Start scraping
    print(f"\nStarting scraping for {business_data['business_name']}...")
    job_id = client.start_scraping(**business_data)
    
    if not job_id:
        print("Failed to start scraping job")
        return
    
    print(f"Scraping job started with ID: {job_id}")
    
    # Wait for completion
    print("\nWaiting for job to complete...")
    if client.wait_for_completion(job_id, timeout=300):  # 5 minutes timeout
        # Get results
        print("\nGetting results...")
        results = client.get_job_results(job_id)
        
        if results:
            print(f"\nScraping completed successfully!")
            print(f"Total reviews found: {results.get('total_reviews', 0)}")
            
            # Show statistics
            stats = results.get('statistics', {})
            print("\nBreakdown by source:")
            for source, count in stats.items():
                if source != 'total_unique':
                    print(f"  {source.capitalize()}: {count}")
            
            # Show sample reviews
            all_reviews = results.get('all_reviews', [])
            if all_reviews:
                print(f"\nSample reviews (showing first 3):")
                for i, review in enumerate(all_reviews[:3]):
                    print(f"\nReview {i+1}:")
                    print(f"  Source: {review.get('source', 'Unknown')}")
                    print(f"  Username: {review.get('username', 'Unknown')}")
                    print(f"  Rating: {review.get('rating', 'N/A')}")
                    print(f"  Sentiment: {review.get('sentiment', 'Unknown')}")
                    print(f"  Caption: {review.get('caption', '')[:100]}...")
        else:
            print("Failed to get results")
    else:
        print("Job did not complete successfully")
    
    # List all jobs
    print("\nListing all jobs...")
    jobs = client.list_jobs()
    if jobs:
        print(f"Total jobs: {jobs.get('total_jobs', 0)}")
        for job in jobs.get('jobs', []):
            print(f"  {job['job_id']}: {job['status']} ({job.get('total_reviews', 0)} reviews)")
    
    # Cleanup old jobs
    print("\nCleaning up old jobs...")
    cleanup_result = client.cleanup_old_jobs(max_age_hours=1)
    if cleanup_result:
        print(f"Cleanup result: {cleanup_result}")

def batch_scraping_example():
    """Example of scraping multiple businesses"""
    
    client = ScrapingAppClient()
    
    # Check app health
    if not client.health_check():
        print("App is not running")
        return
    
    # List of businesses to scrape
    businesses = [
        {
            "business_name": "Primal Queen",
            "business_url": "https://primalqueen.com/",
            "google_maps_url": "https://www.google.com/maps/place/Primal+Queen/@40.7128,-74.0060,17z/",
            "trustpilot_url": "https://www.trustpilot.com/review/primalqueen.com"
        },
        {
            "business_name": "Example Business",
            "business_url": "https://example.com/",
            "google_maps_url": "https://www.google.com/maps/place/Example+Business/@40.7128,-74.0060,17z/",
            "trustpilot_url": "https://www.trustpilot.com/review/example.com"
        }
    ]
    
    job_ids = []
    
    # Start scraping for all businesses
    for business in businesses:
        print(f"\nStarting scraping for {business['business_name']}...")
        job_id = client.start_scraping(**business)
        if job_id:
            job_ids.append(job_id)
            print(f"Job started: {job_id}")
        else:
            print(f"Failed to start job for {business['business_name']}")
    
    # Monitor all jobs
    print(f"\nMonitoring {len(job_ids)} jobs...")
    completed_jobs = []
    
    while job_ids:
        for job_id in job_ids[:]:  # Copy list to avoid modification during iteration
            status_data = client.get_job_status(job_id)
            
            if status_data:
                status = status_data.get('status', 'unknown')
                progress = status_data.get('progress', 0)
                
                print(f"Job {job_id}: {status} ({progress}%)")
                
                if status == 'completed':
                    completed_jobs.append(job_id)
                    job_ids.remove(job_id)
                elif status == 'failed':
                    print(f"Job {job_id} failed: {status_data.get('error', 'Unknown error')}")
                    job_ids.remove(job_id)
        
        if job_ids:
            time.sleep(10)  # Wait 10 seconds before checking again
    
    # Get results for all completed jobs
    print(f"\nGetting results for {len(completed_jobs)} completed jobs...")
    for job_id in completed_jobs:
        results = client.get_job_results(job_id)
        if results:
            print(f"\nJob {job_id}:")
            print(f"  Business: {results.get('business_name', 'Unknown')}")
            print(f"  Total reviews: {results.get('total_reviews', 0)}")
            print(f"  Duration: {results.get('start_time', '')} to {results.get('end_time', '')}")

if __name__ == "__main__":
    print("Flask Scraping App - Example Usage")
    print("=" * 50)
    
    # Run single business example
    example_usage()
    
    # Uncomment to run batch example
    # print("\n" + "=" * 50)
    # print("Batch Scraping Example")
    # print("=" * 50)
    # batch_scraping_example() 