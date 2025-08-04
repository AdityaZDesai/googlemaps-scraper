from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
import json
from datetime import datetime
import uuid
from typing import List, Dict, Any, Set
import threading
import time

# Import all scrapers
from google_scraper import get_google_reviews
from trust_reviews import scrape_trustpilot_reviews
from reddit_scraper import scrape_reddit
from youtube_scraper import scrape_youtube
from tiktok_analyzer import analyze_tiktok_content_for_business, get_business_description_from_url
from internet_scraper import scrape_internet_for_business

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

class ScrapingOrchestrator:
    def __init__(self):
        self.scraping_jobs = {}  # Store active scraping jobs
        
    def generate_unique_id(self) -> str:
        """Generate a unique job ID for tracking scraping progress"""
        return str(uuid.uuid4())
    
    def normalize_url(self, url: str) -> str:
        """Normalize URL to prevent duplicates"""
        if not url:
            return ""
        
        # Remove protocol
        url = url.lower().replace('https://', '').replace('http://', '')
        
        # Remove www
        if url.startswith('www.'):
            url = url[4:]
            
        # Remove trailing slash
        if url.endswith('/'):
            url = url[:-1]
            
        # Remove common tracking parameters
        if '?' in url:
            base_url = url.split('?')[0]
            return base_url
            
        return url
    
    def is_duplicate(self, new_review: Dict, existing_urls: Set[str]) -> bool:
        """Check if a review is a duplicate based on URL"""
        review_url = new_review.get('url_user', '') or new_review.get('review_url', '')
        normalized_url = self.normalize_url(review_url)
        
        if normalized_url in existing_urls:
            return True
            
        # Also check if the review ID already exists
        review_id = new_review.get('id_review', '')
        if review_id:
            # Check against existing review IDs in the job
            return False  # We'll handle this in the main scraping function
            
        return False
    
    def scrape_all_sources(self, business_name: str, business_url: str, 
                          google_maps_url: str, trustpilot_url: str) -> Dict[str, Any]:
        """
        Scrape all sources for a business and return results without duplicates
        
        Args:
            business_name (str): Name of the business
            business_url (str): Main business website URL
            google_maps_url (str): Google Maps URL for the business
            trustpilot_url (str): Trustpilot URL for the business
            
        Returns:
            Dict[str, Any]: Complete scraping results with statistics
        """
        # Find the job that's currently running for this business
        job_id = None
        for jid, job in self.scraping_jobs.items():
            if (job['status'] == 'running' and 
                job.get('business_name') == business_name):
                job_id = jid
                break
        
        if not job_id:
            print(f"[ERROR] No running job found for business: {business_name}")
            return None
        
        print(f"[INFO] Starting comprehensive scraping for: {business_name}")
        print(f"[INFO] Job ID: {job_id}")
        
        # Get business description from the main URL
        if business_url:
            try:
                business_description = get_business_description_from_url(business_url, business_name)
                print(f"[INFO] Business description: {business_description[:100]}...")
            except Exception as e:
                print(f"[ERROR] Failed to get business description: {e}")
                business_description = f"{business_name} - Business information"
        else:
            business_description = f"{business_name} - Business information"
            print(f"[INFO] Using default business description (no business_url provided)")
        
        # Track all URLs to prevent duplicates
        all_urls = set()
        all_review_ids = set()
        all_reviews = []        
        # Step 1: Google Reviews
        if google_maps_url:
            print(f"[INFO] Step 1/6: Scraping Google Reviews...")
            try:
                google_reviews = get_google_reviews(google_maps_url, max_reviews=100, sort_by='newest')
                for review in google_reviews:
                    review['source'] = 'Google'
                    review['business_name'] = business_name
                    review['business_url'] = business_url
                    
                    # Check for duplicates
                    review_url = review.get('url_user', '') or review.get('review_url', '')
                    normalized_url = self.normalize_url(review_url)
                    review_id = review.get('id_review', '')
                    
                    if normalized_url not in all_urls and review_id not in all_review_ids:
                        all_urls.add(normalized_url)
                        all_review_ids.add(review_id)
                        all_reviews.append(review)
                        self.scraping_jobs[job_id]['results']['google'].append(review)
                
                self.scraping_jobs[job_id]['statistics']['google'] = len(self.scraping_jobs[job_id]['results']['google'])
                print(f"[INFO] Google Reviews: {self.scraping_jobs[job_id]['statistics']['google']} unique reviews")
                
            except Exception as e:
                print(f"[ERROR] Google scraping failed: {e}")
        else:
            print(f"[INFO] Step 1/6: Skipping Google Reviews (no google_maps_url provided)")
        
        # Update progress based on available platforms
        total_steps = 6
        completed_steps = 1
        if not google_maps_url:
            total_steps -= 1
        if not trustpilot_url:
            total_steps -= 1
        if not business_url:
            total_steps -= 4  # Reddit, YouTube, TikTok, and Internet search all require business_url
        self.scraping_jobs[job_id]['progress'] = int((completed_steps / total_steps) * 100)
        
        # Step 2: Trustpilot Reviews
        if trustpilot_url:
            print(f"[INFO] Step 2/6: Scraping Trustpilot Reviews...")
            try:
                trustpilot_reviews = scrape_trustpilot_reviews(trustpilot_url, business_name=business_name)
                for review in trustpilot_reviews:
                    # Trustpilot scraper already sets the source and business info
                    # Just ensure business_url is set correctly
                    review['business_url'] = business_url
                    
                    # Check for duplicates
                    review_url = review.get('url_user', '') or review.get('review_url', '')
                    normalized_url = self.normalize_url(review_url)
                    review_id = review.get('id_review', '')
                    
                    if normalized_url not in all_urls and review_id not in all_review_ids:
                        all_urls.add(normalized_url)
                        all_review_ids.add(review_id)
                        all_reviews.append(review)
                        self.scraping_jobs[job_id]['results']['trustpilot'].append(review)
                
                self.scraping_jobs[job_id]['statistics']['trustpilot'] = len(self.scraping_jobs[job_id]['results']['trustpilot'])
                print(f"[INFO] Trustpilot Reviews: {self.scraping_jobs[job_id]['statistics']['trustpilot']} unique reviews")
                
            except Exception as e:
                print(f"[ERROR] Trustpilot scraping failed: {e}")
        else:
            print(f"[INFO] Step 2/6: Skipping Trustpilot Reviews (no trustpilot_url provided)")
        
        # Update progress
        completed_steps = 2
        self.scraping_jobs[job_id]['progress'] = int((completed_steps / total_steps) * 100)
        
        # Step 3: Reddit
        if business_url:
            print(f"[INFO] Step 3/6: Scraping Reddit...")
            try:
                reddit_reviews = scrape_reddit(business_name, business_url, results_limit=50)
                for review in reddit_reviews:
                    # Reddit scraper should already set the source and business info
                    # Just ensure business_url is set correctly
                    review['business_url'] = business_url
                    
                    # Check for duplicates
                    review_url = review.get('url_user', '') or review.get('review_url', '')
                    normalized_url = self.normalize_url(review_url)
                    review_id = review.get('id_review', '')
                    
                    if normalized_url not in all_urls and review_id not in all_review_ids:
                        all_urls.add(normalized_url)
                        all_review_ids.add(review_id)
                        all_reviews.append(review)
                        self.scraping_jobs[job_id]['results']['reddit'].append(review)
                
                self.scraping_jobs[job_id]['statistics']['reddit'] = len(self.scraping_jobs[job_id]['results']['reddit'])
                print(f"[INFO] Reddit: {self.scraping_jobs[job_id]['statistics']['reddit']} unique reviews")
                
            except Exception as e:
                print(f"[ERROR] Reddit scraping failed: {e}")
        else:
            print(f"[INFO] Step 3/6: Skipping Reddit (no business_url provided)")
        
        # Update progress
        completed_steps = 3
        self.scraping_jobs[job_id]['progress'] = int((completed_steps / total_steps) * 100)
        
        # Step 4: YouTube
        if business_url:
            print(f"[INFO] Step 4/6: Scraping YouTube...")
            try:
                youtube_reviews = scrape_youtube(business_name, business_url, results_limit=50)
                for review in youtube_reviews:
                    # YouTube scraper should already set the source and business info
                    # Just ensure business_url is set correctly
                    review['business_url'] = business_url
                    
                    # Check for duplicates
                    review_url = review.get('url_user', '') or review.get('review_url', '')
                    normalized_url = self.normalize_url(review_url)
                    review_id = review.get('id_review', '')
                    
                    if normalized_url not in all_urls and review_id not in all_review_ids:
                        all_urls.add(normalized_url)
                        all_review_ids.add(review_id)
                        all_reviews.append(review)
                        self.scraping_jobs[job_id]['results']['youtube'].append(review)
                
                self.scraping_jobs[job_id]['statistics']['youtube'] = len(self.scraping_jobs[job_id]['results']['youtube'])
                print(f"[INFO] YouTube: {self.scraping_jobs[job_id]['statistics']['youtube']} unique reviews")
                
            except Exception as e:
                print(f"[ERROR] YouTube scraping failed: {e}")
        else:
            print(f"[INFO] Step 4/6: Skipping YouTube (no business_url provided)")
        
        # Update progress
        completed_steps = 4
        self.scraping_jobs[job_id]['progress'] = int((completed_steps / total_steps) * 100)
        
        # Step 5: TikTok
        if business_url:
            print(f"[INFO] Step 5/6: Scraping TikTok...")
            try:
                tiktok_reviews = analyze_tiktok_content_for_business(business_name, business_description)
                for review in tiktok_reviews:
                    # TikTok scraper should already set the source and business info
                    # Just ensure business_url is set correctly
                    review['business_url'] = business_url
                    
                    # Check for duplicates
                    review_url = review.get('url_user', '') or review.get('review_url', '')
                    normalized_url = self.normalize_url(review_url)
                    review_id = review.get('id_review', '')
                    
                    if normalized_url not in all_urls and review_id not in all_review_ids:
                        all_urls.add(normalized_url)
                        all_review_ids.add(review_id)
                        all_reviews.append(review)
                        self.scraping_jobs[job_id]['results']['tiktok'].append(review)
                
                self.scraping_jobs[job_id]['statistics']['tiktok'] = len(self.scraping_jobs[job_id]['results']['tiktok'])
                print(f"[INFO] TikTok: {self.scraping_jobs[job_id]['statistics']['tiktok']} unique reviews")
                
            except Exception as e:
                print(f"[ERROR] TikTok scraping failed: {e}")
        else:
            print(f"[INFO] Step 5/6: Skipping TikTok (no business_url provided)")
        
        # Update progress
        completed_steps = 5
        self.scraping_jobs[job_id]['progress'] = int((completed_steps / total_steps) * 100)
        
        # Step 6: Internet Search
        if business_url:
            print(f"[INFO] Step 6/6: Scraping Internet Search...")
            try:
                internet_reviews = scrape_internet_for_business(business_name, business_description, max_results_per_term=20)
                for review in internet_reviews:
                    # Internet scraper should already set the source and business info
                    # Just ensure business_url is set correctly
                    review['business_url'] = business_url
                    
                    # Check for duplicates
                    review_url = review.get('url_user', '') or review.get('review_url', '')
                    normalized_url = self.normalize_url(review_url)
                    review_id = review.get('id_review', '')
                    
                    if normalized_url not in all_urls and review_id not in all_review_ids:
                        all_urls.add(normalized_url)
                        all_review_ids.add(review_id)
                        all_reviews.append(review)
                        self.scraping_jobs[job_id]['results']['internet'].append(review)
                
                self.scraping_jobs[job_id]['statistics']['internet'] = len(self.scraping_jobs[job_id]['results']['internet'])
                print(f"[INFO] Internet: {self.scraping_jobs[job_id]['statistics']['internet']} unique reviews")
                
            except Exception as e:
                print(f"[ERROR] Internet scraping failed: {e}")
        else:
            print(f"[INFO] Step 6/6: Skipping Internet Search (no business_url provided)")
        
        # Update progress to 100%
        self.scraping_jobs[job_id]['progress'] = 100
        
        # Calculate final statistics
        total_unique = len(all_reviews)
        self.scraping_jobs[job_id]['statistics']['total_unique'] = total_unique
        self.scraping_jobs[job_id]['total_reviews'] = total_unique
        self.scraping_jobs[job_id]['status'] = 'completed'
        self.scraping_jobs[job_id]['end_time'] = datetime.utcnow()
        
        print(f"[INFO] Scraping completed! Total unique reviews: {total_unique}")
        print(f"[INFO] Breakdown: Google={self.scraping_jobs[job_id]['statistics']['google']}, "
              f"Trustpilot={self.scraping_jobs[job_id]['statistics']['trustpilot']}, "
              f"Reddit={self.scraping_jobs[job_id]['statistics']['reddit']}, "
              f"YouTube={self.scraping_jobs[job_id]['statistics']['youtube']}, "
              f"TikTok={self.scraping_jobs[job_id]['statistics']['tiktok']}, "
              f"Internet={self.scraping_jobs[job_id]['statistics']['internet']}")
        
        return {
            'status': 'completed',
            'business_name': business_name,
            'total_reviews': total_unique,
            'statistics': self.scraping_jobs[job_id]['statistics'],
            'results': self.scraping_jobs[job_id]['results'],
            'all_reviews': all_reviews
        }

# Initialize the orchestrator
orchestrator = ScrapingOrchestrator()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'active_jobs': len([job for job in orchestrator.scraping_jobs.values() if job['status'] == 'running'])
    })

@app.route('/scrape', methods=['POST'])
def start_scraping():
    """Start comprehensive scraping for a business"""
    try:
        data = request.get_json()
        
        # Validate required fields - only business_name is required
        if 'business_name' not in data or not data['business_name']:
            return jsonify({
                'error': 'Missing required field: business_name'
            }), 400
        
        # Get optional URLs
        business_url = data.get('business_url', '')
        google_maps_url = data.get('google_maps_url', '')
        trustpilot_url = data.get('trustpilot_url', '')
        
        # Log which platforms will be skipped
        skipped_platforms = []
        if not business_url:
            skipped_platforms.extend([
                'Internet Search (requires business_url for description)',
                'Reddit (requires business_url for description)',
                'YouTube (requires business_url for description)',
                'TikTok (requires business_url for description)'
            ])
        if not google_maps_url:
            skipped_platforms.append('Google Reviews')
        if not trustpilot_url:
            skipped_platforms.append('Trustpilot Reviews')
        
        if skipped_platforms:
            print(f"[INFO] Will skip platforms due to missing URLs: {', '.join(skipped_platforms)}")
        
        business_name = data['business_name']
        business_url = data['business_url']
        google_maps_url = data['google_maps_url']
        trustpilot_url = data['trustpilot_url']
        
        # Generate job ID first
        job_id = orchestrator.generate_unique_id()
        
        # Initialize the job in the orchestrator
        orchestrator.scraping_jobs[job_id] = {
            'status': 'running',
            'progress': 0,
            'total_reviews': 0,
            'start_time': datetime.utcnow(),
            'business_name': business_name,
            'results': {
                'google': [],
                'trustpilot': [],
                'reddit': [],
                'youtube': [],
                'tiktok': [],
                'internet': []
            },
            'statistics': {
                'google': 0,
                'trustpilot': 0,
                'reddit': 0,
                'youtube': 0,
                'tiktok': 0,
                'internet': 0,
                'total_unique': 0
            }
        }
        
        # Start scraping in a separate thread to avoid blocking
        def run_scraping():
            try:
                result = orchestrator.scrape_all_sources(
                    business_name, business_url, google_maps_url, trustpilot_url
                )
                # Update the job with results
                orchestrator.scraping_jobs[job_id].update(result)
            except Exception as e:
                print(f"[ERROR] Scraping job failed: {e}")
                # Update job status to failed
                if job_id in orchestrator.scraping_jobs:
                    orchestrator.scraping_jobs[job_id]['status'] = 'failed'
                    orchestrator.scraping_jobs[job_id]['error'] = str(e)
        
        # Start the scraping thread
        scraping_thread = threading.Thread(target=run_scraping)
        scraping_thread.daemon = True
        scraping_thread.start()
        return jsonify({
            'job_id': job_id,
            'status': 'started',
            'message': f'Scraping started for {business_name}',
            'business_name': business_name
        })
        
    except Exception as e:
        return jsonify({
            'error': f'Failed to start scraping: {str(e)}'
        }), 500

@app.route('/status/<job_id>', methods=['GET'])
def get_job_status(job_id):
    """Get the status of a scraping job"""
    if job_id not in orchestrator.scraping_jobs:
        return jsonify({
            'error': 'Job not found'
        }), 404
    
    job = orchestrator.scraping_jobs[job_id]
    return jsonify({
        'job_id': job_id,
        'status': job['status'],
        'progress': job.get('progress', 0),
        'statistics': job.get('statistics', {}),
        'start_time': job.get('start_time', '').isoformat() if job.get('start_time') else None,
        'end_time': job.get('end_time', '').isoformat() if job.get('end_time') else None,
        'error': job.get('error', None)
    })

@app.route('/results/<job_id>', methods=['GET'])
def get_job_results(job_id):
    """Get the complete results of a completed scraping job"""
    if job_id not in orchestrator.scraping_jobs:
        return jsonify({
            'error': 'Job not found'
        }), 404
    
    job = orchestrator.scraping_jobs[job_id]
    
    if job['status'] != 'completed':
        return jsonify({
            'error': f'Job is not completed. Current status: {job["status"]}'
        }), 400
    
    return jsonify({
        'job_id': job_id,
        'status': job['status'],
        'business_name': job.get('business_name', ''),
        'total_reviews': job.get('total_reviews', 0),
        'statistics': job.get('statistics', {}),
        'results': job.get('results', {}),
        'all_reviews': job.get('all_reviews', []),
        'start_time': job.get('start_time', '').isoformat() if job.get('start_time') else None,
        'end_time': job.get('end_time', '').isoformat() if job.get('end_time') else None
    })

@app.route('/jobs', methods=['GET'])
def list_jobs():
    """List all scraping jobs"""
    jobs = []
    for job_id, job in orchestrator.scraping_jobs.items():
        jobs.append({
            'job_id': job_id,
            'status': job['status'],
            'progress': job.get('progress', 0),
            'business_name': job.get('business_name', ''),
            'total_reviews': job.get('total_reviews', 0),
            'start_time': job.get('start_time', '').isoformat() if job.get('start_time') else None,
            'end_time': job.get('end_time', '').isoformat() if job.get('end_time') else None
        })
    
    return jsonify({
        'jobs': jobs,
        'total_jobs': len(jobs)
    })

@app.route('/cleanup', methods=['POST'])
def cleanup_old_jobs():
    """Clean up old completed jobs to free memory"""
    try:
        data = request.get_json() or {}
        max_age_hours = data.get('max_age_hours', 24)  # Default: 24 hours
        
        current_time = datetime.utcnow()
        jobs_to_remove = []
        
        for job_id, job in orchestrator.scraping_jobs.items():
            if job['status'] in ['completed', 'failed']:
                end_time = job.get('end_time', job.get('start_time'))
                if end_time:
                    age_hours = (current_time - end_time).total_seconds() / 3600
                    if age_hours > max_age_hours:
                        jobs_to_remove.append(job_id)
        
        # Remove old jobs
        for job_id in jobs_to_remove:
            del orchestrator.scraping_jobs[job_id]
        
        return jsonify({
            'message': f'Cleaned up {len(jobs_to_remove)} old jobs',
            'remaining_jobs': len(orchestrator.scraping_jobs)
        })
        
    except Exception as e:
        return jsonify({
            'error': f'Failed to cleanup jobs: {str(e)}'
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    print(f"[INFO] Starting Flask app on port {port}")
    print(f"[INFO] Debug mode: {debug}")
    
    app.run(host='0.0.0.0', port=port, debug=debug) 