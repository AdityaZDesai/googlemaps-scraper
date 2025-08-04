#!/usr/bin/env python3
"""
Simple script to test the scrape endpoint for one business and save results to JSON
"""

import requests
import json
import time
import os
from datetime import datetime

def test_and_save_business(business_name, business_url=None, google_maps_url=None, trustpilot_url=None):
    """
    Test scraping for a single business and save results to JSON
    
    Args:
        business_name (str): Name of the business
        business_url (str, optional): Business website URL
        google_maps_url (str, optional): Google Maps URL
        trustpilot_url (str, optional): Trustpilot URL
    """
    
    base_url = "http://localhost:5000"
    
    # Prepare business data
    business_data = {"business_name": business_name}
    if business_url:
        business_data["business_url"] = business_url
    if google_maps_url:
        business_data["google_maps_url"] = google_maps_url
    if trustpilot_url:
        business_data["trustpilot_url"] = trustpilot_url
    
    print(f"🔍 Testing scraping for: {business_name}")
    print(f"📋 Provided URLs: {list(business_data.keys())}")
    
    # Check if Flask app is running
    try:
        response = requests.get(f"{base_url}/health")
        if response.status_code != 200:
            print("❌ Flask app is not running. Please start it with: python start_app.py")
            return
        print("✅ Flask app is running")
    except Exception as e:
        print(f"❌ Cannot connect to Flask app: {e}")
        return
    
    # Start scraping job
    try:
        print(f"\n🚀 Starting scraping job...")
        response = requests.post(
            f"{base_url}/scrape",
            json=business_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to start job: {response.text}")
            return
        
        result = response.json()
        job_id = result.get('job_id')
        print(f"✅ Job started with ID: {job_id}")
        
    except Exception as e:
        print(f"❌ Error starting job: {e}")
        return
    
    # Wait for completion
    print(f"\n⏳ Waiting for job to complete...")
    start_time = time.time()
    timeout = 600  # 10 minutes
    
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{base_url}/status/{job_id}")
            
            if response.status_code == 200:
                status_data = response.json()
                status = status_data.get('status', 'unknown')
                progress = status_data.get('progress', 0)
                
                print(f"📊 Status: {status}, Progress: {progress}%")
                
                if status == 'completed':
                    print("✅ Job completed!")
                    break
                elif status == 'failed':
                    error = status_data.get('error', 'Unknown error')
                    print(f"❌ Job failed: {error}")
                    return
            else:
                print(f"❌ Failed to get status: {response.status_code}")
                return
                
        except Exception as e:
            print(f"❌ Error checking status: {e}")
            return
        
        time.sleep(10)  # Check every 10 seconds
    else:
        print("⏰ Job timed out")
        return
    
    # Get results
    try:
        print(f"\n📥 Fetching results...")
        response = requests.get(f"{base_url}/results/{job_id}")
        
        if response.status_code != 200:
            print(f"❌ Failed to get results: {response.text}")
            return
        
        results = response.json()
        print(f"✅ Results retrieved successfully")
        
    except Exception as e:
        print(f"❌ Error getting results: {e}")
        return
    
    # Print summary
    print(f"\n📋 RESULTS SUMMARY")
    print("=" * 50)
    print(f"Business: {results.get('business_name', 'Unknown')}")
    print(f"Total Reviews: {results.get('total_reviews', 0)}")
    
    stats = results.get('statistics', {})
    print(f"\n📊 Breakdown by Source:")
    for source, count in stats.items():
        if source != 'total_unique':
            print(f"  {source.capitalize()}: {count}")
    
    # Save to JSON file
    try:
        # Create output directory
        os.makedirs('output', exist_ok=True)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = business_name.replace(' ', '_').replace('/', '_').lower()
        filename = f"scraping_results_{safe_name}_{timestamp}.json"
        filepath = os.path.join('output', filename)
        
        # Save results
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n💾 Results saved to: {filepath}")
        print(f"📁 File size: {os.path.getsize(filepath)} bytes")
        
    except Exception as e:
        print(f"❌ Error saving results: {e}")
        return
    
    print("=" * 50)
    print("🎉 Done!")

if __name__ == "__main__":
    # Example usage - modify these values for your business
    business_name = "Primal Queen"
    business_url = "https://primalqueen.com/"
    google_maps_url = "https://www.google.com/maps/place/Primal+Queen/@40.7128,-74.0060,17z/"
    trustpilot_url = "https://www.trustpilot.com/review/primalqueen.com"
    
    # You can also test with minimal data:
    # test_and_save_business("Example Business")  # No URLs provided
    
    test_and_save_business(
        business_name=business_name,
        business_url=business_url,
        google_maps_url=google_maps_url,
        trustpilot_url=trustpilot_url
    ) 