#!/usr/bin/env python3
"""
Test script for the Flask scraping app
"""

import requests
import json
import time
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:5000"

def test_health_check():
    """Test the health check endpoint"""
    print("=== Testing Health Check ===")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_start_scraping():
    """Test starting a scraping job"""
    print("\n=== Testing Start Scraping ===")
    
    # Example data for testing - with all URLs
    test_data = {
        "business_name": "Primal Queen",
        "business_url": "https://primalqueen.com/",
        "google_maps_url": "https://www.google.com/maps/place/Primal+Queen/@40.7128,-74.0060,17z/",
        "trustpilot_url": "https://www.trustpilot.com/review/primalqueen.com"
    }
    
    # Example with missing URLs (will skip some platforms)
    test_data_minimal = {
        "business_name": "Example Business"
        # Missing URLs - will skip Google, Trustpilot, Reddit, YouTube, TikTok, and Internet search
    }
    
    try:
        # Test with full data first
        print("Testing with full data (all URLs provided):")
        response = requests.post(
            f"{BASE_URL}/scrape",
            json=test_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            job_id = response.json().get('job_id')
            
            # Also test with minimal data
            print("\nTesting with minimal data (missing URLs):")
            response_minimal = requests.post(
                f"{BASE_URL}/scrape",
                json=test_data_minimal,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"Status Code: {response_minimal.status_code}")
            print(f"Response: {json.dumps(response_minimal.json(), indent=2)}")
            
            return job_id
        else:
            print(f"Failed to start scraping: {response.text}")
            return None
            
    except Exception as e:
        print(f"Error: {e}")
        return None

def test_get_job_status(job_id):
    """Test getting job status"""
    print(f"\n=== Testing Job Status for {job_id} ===")
    
    try:
        response = requests.get(f"{BASE_URL}/status/{job_id}")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.json()
    except Exception as e:
        print(f"Error: {e}")
        return None

def test_get_job_results(job_id):
    """Test getting job results"""
    print(f"\n=== Testing Job Results for {job_id} ===")
    
    try:
        response = requests.get(f"{BASE_URL}/results/{job_id}")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Total Reviews: {result.get('total_reviews', 0)}")
            print(f"Statistics: {json.dumps(result.get('statistics', {}), indent=2)}")
            
            # Show a few sample reviews
            all_reviews = result.get('all_reviews', [])
            if all_reviews:
                print(f"\nSample Reviews (showing first 3):")
                for i, review in enumerate(all_reviews[:3]):
                    print(f"\nReview {i+1}:")
                    print(f"  Source: {review.get('source', 'Unknown')}")
                    print(f"  Username: {review.get('username', 'Unknown')}")
                    print(f"  Rating: {review.get('rating', 'N/A')}")
                    print(f"  Caption: {review.get('caption', '')[:100]}...")
                    print(f"  URL: {review.get('url_user', 'N/A')}")
            else:
                print("\nNote: No reviews found. This might be because:")
                print("  - Missing business_url (required for Reddit, YouTube, TikTok, Internet)")
                print("  - Missing google_maps_url (required for Google Reviews)")
                print("  - Missing trustpilot_url (required for Trustpilot Reviews)")
            
            return result
        else:
            print(f"Failed to get results: {response.text}")
            return None
            
    except Exception as e:
        print(f"Error: {e}")
        return None

def test_list_jobs():
    """Test listing all jobs"""
    print("\n=== Testing List Jobs ===")
    
    try:
        response = requests.get(f"{BASE_URL}/jobs")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.json()
    except Exception as e:
        print(f"Error: {e}")
        return None

def test_cleanup_jobs():
    """Test cleaning up old jobs"""
    print("\n=== Testing Cleanup Jobs ===")
    
    try:
        response = requests.post(
            f"{BASE_URL}/cleanup",
            json={"max_age_hours": 1},  # Clean up jobs older than 1 hour
            headers={"Content-Type": "application/json"}
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.json()
    except Exception as e:
        print(f"Error: {e}")
        return None

def monitor_job_progress(job_id, max_wait_time=300):  # 5 minutes max wait
    """Monitor a job's progress"""
    print(f"\n=== Monitoring Job Progress for {job_id} ===")
    
    start_time = time.time()
    
    while time.time() - start_time < max_wait_time:
        status_data = test_get_job_status(job_id)
        
        if not status_data:
            print("Failed to get job status")
            return False
        
        status = status_data.get('status', 'unknown')
        progress = status_data.get('progress', 0)
        
        print(f"Status: {status}, Progress: {progress}%")
        
        if status == 'completed':
            print("Job completed successfully!")
            return True
        elif status == 'failed':
            print(f"Job failed: {status_data.get('error', 'Unknown error')}")
            return False
        
        # Wait 10 seconds before checking again
        time.sleep(10)
    
    print(f"Job monitoring timed out after {max_wait_time} seconds")
    return False

def main():
    """Main test function"""
    print("Flask Scraping App Test Suite")
    print("=" * 50)
    
    # Test 1: Health check
    if not test_health_check():
        print("Health check failed. Make sure the Flask app is running.")
        return
    
    # Test 2: List existing jobs
    test_list_jobs()
    
    # Test 3: Start a new scraping job
    job_id = test_start_scraping()
    
    if job_id:
        print(f"\nStarted scraping job with ID: {job_id}")
        
        # Test 4: Monitor job progress
        if monitor_job_progress(job_id):
            # Test 5: Get final results
            test_get_job_results(job_id)
        
        # Test 6: List jobs again
        test_list_jobs()
        
        # Test 7: Cleanup old jobs
        test_cleanup_jobs()
    else:
        print("Failed to start scraping job")

if __name__ == "__main__":
    main() 