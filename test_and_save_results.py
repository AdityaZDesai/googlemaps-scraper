#!/usr/bin/env python3
"""
Script to test the scrape endpoint and save results to a JSON file
"""

import requests
import json
import time
import os
from datetime import datetime
from typing import Dict, Any, Optional

class ScrapingTester:
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def health_check(self) -> bool:
        """Check if the Flask app is running"""
        try:
            response = self.session.get(f"{self.base_url}/health")
            if response.status_code == 200:
                print("✅ Flask app is running")
                return True
            else:
                print(f"❌ Flask app returned status {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Cannot connect to Flask app: {e}")
            return False
    
    def start_scraping_job(self, business_data: Dict[str, str]) -> Optional[str]:
        """Start a scraping job and return the job ID"""
        try:
            print(f"\n🚀 Starting scraping job for: {business_data.get('business_name', 'Unknown')}")
            
            response = self.session.post(
                f"{self.base_url}/scrape",
                json=business_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                job_id = result.get('job_id')
                print(f"✅ Job started successfully with ID: {job_id}")
                return job_id
            else:
                print(f"❌ Failed to start job: {response.status_code}")
                print(f"Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error starting job: {e}")
            return None
    
    def wait_for_completion(self, job_id: str, timeout: int = 600, check_interval: int = 10) -> bool:
        """Wait for a job to complete"""
        print(f"\n⏳ Waiting for job {job_id} to complete...")
        print(f"Timeout: {timeout} seconds, Check interval: {check_interval} seconds")
        
        start_time = time.time()
        last_progress = -1
        
        while time.time() - start_time < timeout:
            try:
                response = self.session.get(f"{self.base_url}/status/{job_id}")
                
                if response.status_code == 200:
                    status_data = response.json()
                    status = status_data.get('status', 'unknown')
                    progress = status_data.get('progress', 0)
                    
                    # Only print progress if it changed
                    if progress != last_progress:
                        print(f"📊 Status: {status}, Progress: {progress}%")
                        last_progress = progress
                    
                    if status == 'completed':
                        print("✅ Job completed successfully!")
                        return True
                    elif status == 'failed':
                        error = status_data.get('error', 'Unknown error')
                        print(f"❌ Job failed: {error}")
                        return False
                    
                else:
                    print(f"❌ Failed to get job status: {response.status_code}")
                    return False
                    
            except Exception as e:
                print(f"❌ Error checking job status: {e}")
                return False
            
            time.sleep(check_interval)
        
        print(f"⏰ Job timed out after {timeout} seconds")
        return False
    
    def get_job_results(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get the complete results of a completed job"""
        try:
            print(f"\n📥 Fetching results for job {job_id}...")
            
            response = self.session.get(f"{self.base_url}/results/{job_id}")
            
            if response.status_code == 200:
                results = response.json()
                print(f"✅ Successfully retrieved results")
                return results
            else:
                print(f"❌ Failed to get results: {response.status_code}")
                print(f"Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error getting results: {e}")
            return None
    
    def save_results_to_json(self, results: Dict[str, Any], filename: str = None) -> str:
        """Save results to a JSON file"""
        if filename is None:
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            business_name = results.get('business_name', 'unknown').replace(' ', '_').lower()
            filename = f"scraping_results_{business_name}_{timestamp}.json"
        
        try:
            # Create output directory if it doesn't exist
            os.makedirs('output', exist_ok=True)
            filepath = os.path.join('output', filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False, default=str)
            
            print(f"💾 Results saved to: {filepath}")
            return filepath
            
        except Exception as e:
            print(f"❌ Error saving results: {e}")
            return None
    
    def print_summary(self, results: Dict[str, Any]):
        """Print a summary of the scraping results"""
        print(f"\n📋 SCRAPING SUMMARY")
        print("=" * 50)
        print(f"Business: {results.get('business_name', 'Unknown')}")
        print(f"Total Reviews: {results.get('total_reviews', 0)}")
        print(f"Job ID: {results.get('job_id', 'Unknown')}")
        print(f"Status: {results.get('status', 'Unknown')}")
        
        # Show statistics
        stats = results.get('statistics', {})
        print(f"\n📊 Breakdown by Source:")
        for source, count in stats.items():
            if source != 'total_unique':
                print(f"  {source.capitalize()}: {count}")
        
        # Show sample reviews
        all_reviews = results.get('all_reviews', [])
        if all_reviews:
            print(f"\n📝 Sample Reviews (showing first 3):")
            for i, review in enumerate(all_reviews[:3]):
                print(f"\n  Review {i+1}:")
                print(f"    Source: {review.get('source', 'Unknown')}")
                print(f"    Username: {review.get('username', 'Unknown')}")
                print(f"    Rating: {review.get('rating', 'N/A')}")
                print(f"    Sentiment: {review.get('sentiment', 'Unknown')}")
                print(f"    Caption: {review.get('caption', '')[:100]}...")
        else:
            print(f"\n⚠️  No reviews found. This might be because:")
            print(f"    - Missing business_url (required for Reddit, YouTube, TikTok, Internet)")
            print(f"    - Missing google_maps_url (required for Google Reviews)")
            print(f"    - Missing trustpilot_url (required for Trustpilot Reviews)")
        
        print("=" * 50)

def main():
    """Main function to test scraping and save results"""
    print("🔍 Flask Scraping App - Test and Save Results")
    print("=" * 60)
    
    # Initialize tester
    tester = ScrapingTester()
    
    # Check if app is running
    if not tester.health_check():
        print("❌ Cannot proceed without a running Flask app")
        print("Please start the Flask app with: python start_app.py")
        return
    
    # Test data - you can modify this for different businesses
    test_cases = [
        {
            "name": "Full Scraping Test",
            "data": {
                "business_name": "Primal Queen",
                "business_url": "https://primalqueen.com/",
                "google_maps_url": "https://www.google.com/maps/place/Primal+Queen/@40.7128,-74.0060,17z/",
                "trustpilot_url": "https://www.trustpilot.com/review/primalqueen.com"
            }
        },
        {
            "name": "Minimal Scraping Test",
            "data": {
                "business_name": "Example Business"
                # No URLs provided - will skip most platforms
            }
        },
        {
            "name": "Partial Scraping Test",
            "data": {
                "business_name": "Test Business",
                "business_url": "https://example.com/",
                "google_maps_url": "https://www.google.com/maps/place/Test+Business/@40.7128,-74.0060,17z/"
                # Missing trustpilot_url - will skip Trustpilot
            }
        }
    ]
    
    # Run each test case
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🧪 TEST CASE {i}: {test_case['name']}")
        print("-" * 40)
        
        # Start scraping job
        job_id = tester.start_scraping_job(test_case['data'])
        
        if job_id:
            # Wait for completion
            if tester.wait_for_completion(job_id, timeout=300):  # 5 minutes timeout
                # Get results
                results = tester.get_job_results(job_id)
                
                if results:
                    # Print summary
                    tester.print_summary(results)
                    
                    # Save to JSON file
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"test_case_{i}_{timestamp}.json"
                    filepath = tester.save_results_to_json(results, filename)
                    
                    if filepath:
                        print(f"✅ Test case {i} completed successfully!")
                        print(f"📁 Results saved to: {filepath}")
                    else:
                        print(f"❌ Failed to save results for test case {i}")
                else:
                    print(f"❌ Failed to get results for test case {i}")
            else:
                print(f"❌ Job did not complete for test case {i}")
        else:
            print(f"❌ Failed to start job for test case {i}")
        
        print("\n" + "=" * 60)
    
    print("🎉 All test cases completed!")
    print("📁 Check the 'output' directory for saved JSON files")

if __name__ == "__main__":
    main() 