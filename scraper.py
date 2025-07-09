# -*- coding: utf-8 -*-
from googlemaps import GoogleMapsScraper
from datetime import datetime, timedelta
import argparse
import csv
from termcolor import colored
import time
import schedule
import logging
from pymongo import MongoClient
import sys
import os

# MongoDB Configuration
DB_URL = 'mongodb://localhost:27017/'
DB_NAME = 'test'
BUSINESSES_COLLECTION = 'businesses'
REVIEWS_COLLECTION = 'reviews'

# Review sorting options
ind = {'most_relevant': 0, 'newest': 1, 'highest_rating': 2, 'lowest_rating': 3}

# CSV Headers
HEADER = ['id_review', 'caption', 'relative_date', 'retrieval_date', 'rating', 'username', 'n_review_user', 'n_photo_user', 'url_user']
HEADER_W_SOURCE = ['id_review', 'caption', 'relative_date', 'retrieval_date', 'rating', 'username', 'n_review_user', 'n_photo_user', 'url_user', 'url_source']

class BusinessReviewScraper:
    
    def __init__(self, debug=False, max_reviews_per_business=100, sort_by='newest'):
        self.debug = debug
        self.max_reviews_per_business = max_reviews_per_business
        self.sort_by = sort_by
        self.client = MongoClient(DB_URL)
        self.db = self.client[DB_NAME]
        self.businesses_collection = self.db[BUSINESSES_COLLECTION]
        self.reviews_collection = self.db[REVIEWS_COLLECTION]
        self.logger = self.__get_logger()
        
    def __get_logger(self):
        """Create logger for the scraper"""
        logger = logging.getLogger('business_review_scraper')
        logger.setLevel(logging.DEBUG)
        
        # Create file handler
        fh = logging.FileHandler('business_scraper.log')
        fh.setLevel(logging.DEBUG)
        
        # Create console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        # Add handlers to logger
        logger.addHandler(fh)
        logger.addHandler(ch)
        
        return logger
    
    def scrape_all_businesses(self):
        """Main method to scrape reviews for all businesses"""
        self.logger.info("Starting review scraping for all businesses...")
        
        # Get all businesses from MongoDB
        businesses = list(self.businesses_collection.find({}))
        self.logger.info(f"Found {len(businesses)} businesses to process")
        
        if not businesses:
            self.logger.warning("No businesses found in the database")
            return
        
        with GoogleMapsScraper(debug=self.debug) as scraper:
            for business in businesses:
                try:
                    self.scrape_business_reviews(scraper, business)
                except Exception as e:
                    self.logger.error(f"Error scraping business {business.get('business_name', 'Unknown')}: {str(e)}")
                    continue
        
        self.logger.info("Completed review scraping for all businesses")
    
    def scrape_business_reviews(self, scraper, business):
        """Scrape reviews for a single business"""
        business_name = business.get('business_name', 'Unknown')
        business_id = business.get('_id')
        google_url = business.get('google_business_url', '')
        
        if not google_url:
            self.logger.warning(f"No Google business URL found for business: {business_name}")
            return
        
        self.logger.info(f"Scraping reviews for business: {business_name}")
        self.logger.info(f"Google URL: {google_url}")
        
        # Sort reviews by specified criteria
        error = scraper.sort_by(google_url, ind[self.sort_by])
        
        if error != 0:
            self.logger.error(f"Failed to sort reviews for {business_name}")
            return
        
        n_reviews = 0
        offset = 0
        
        while n_reviews < self.max_reviews_per_business:
            # Get reviews batch
            reviews = scraper.get_reviews(offset)
            
            if len(reviews) == 0:
                self.logger.info(f"No more reviews found for {business_name}")
                break
            
            # Process each review
            for review in reviews:
                if n_reviews >= self.max_reviews_per_business:
                    break
                
                # Add business metadata to review
                review['business_id'] = business_id
                review['business_name'] = business_name
                review['business_slug'] = business.get('slug', '')
                review['google_business_url'] = google_url
                review['scraped_at'] = datetime.utcnow()
                
                # Check if review already exists
                existing_review = self.reviews_collection.find_one({
                    'id_review': review['id_review'],
                    'business_id': business_id
                })
                
                if not existing_review:
                    # Insert new review
                    self.reviews_collection.insert_one(review)
                    n_reviews += 1
                    self.logger.info(f"Added review {n_reviews} for {business_name}")
                else:
                    self.logger.debug(f"Review {review['id_review']} already exists for {business_name}")
            
            offset += len(reviews)
            
            # Small delay to be respectful to Google
            time.sleep(1)
        
        self.logger.info(f"Completed scraping {n_reviews} reviews for {business_name}")
    
    def export_to_csv(self, output_file='business_reviews.csv'):
        """Export all reviews to CSV file"""
        self.logger.info(f"Exporting reviews to {output_file}")
        
        # Get all reviews from database
        reviews = list(self.reviews_collection.find({}))
        
        if not reviews:
            self.logger.warning("No reviews found to export")
            return
        
        # Prepare CSV data
        csv_data = []
        for review in reviews:
            # Convert MongoDB ObjectId to string
            review['business_id'] = str(review['business_id'])
            review['scraped_at'] = review['scraped_at'].isoformat() if review.get('scraped_at') else ''
            
            # Create row with all fields
            row = [
                review.get('id_review', ''),
                review.get('caption', ''),
                review.get('relative_date', ''),
                review.get('retrieval_date', ''),
                review.get('rating', ''),
                review.get('username', ''),
                review.get('n_review_user', ''),
                review.get('n_photo_user', ''),
                review.get('url_user', ''),
                review.get('google_business_url', ''),
                review.get('business_name', ''),
                review.get('business_slug', ''),
                review.get('scraped_at', '')
            ]
            csv_data.append(row)
        
        # Write to CSV
        with open(output_file, mode='w', encoding='utf-8', newline='\n') as file:
            writer = csv.writer(file, quoting=csv.QUOTE_MINIMAL)
            
            # Write header
            header = HEADER_W_SOURCE + ['business_name', 'business_slug', 'scraped_at']
            writer.writerow(header)
            
            # Write data
            writer.writerows(csv_data)
        
        self.logger.info(f"Exported {len(csv_data)} reviews to {output_file}")

def run_scraper():
    """Function to run the scraper (used by scheduler)"""
    scraper = BusinessReviewScraper(debug=False, max_reviews_per_business=100, sort_by='newest')
    scraper.scrape_all_businesses()

def main():
    parser = argparse.ArgumentParser(description='Google Maps Business Reviews Scraper with MongoDB')
    parser.add_argument('--N', type=int, default=100, help='Number of reviews to scrape per business')
    parser.add_argument('--sort_by', type=str, default='newest', 
                       help='most_relevant, newest, highest_rating or lowest_rating')
    parser.add_argument('--debug', dest='debug', action='store_true', 
                       help='Run scraper using browser graphical interface')
    parser.add_argument('--export-csv', type=str, default=None, 
                       help='Export reviews to CSV file')
    parser.add_argument('--schedule', dest='schedule', action='store_true', 
                       help='Run scraper every 3 hours')
    parser.set_defaults(debug=False, schedule=False)

    args = parser.parse_args()

    if args.schedule:
        # Schedule the scraper to run every 3 hours
        schedule.every(3).hours.do(run_scraper)
        
        print("Starting scheduled scraper (every 3 hours)...")
        print("Press Ctrl+C to stop")
        
        # Run once immediately
        run_scraper()
        
        # Keep running the scheduler
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except KeyboardInterrupt:
                print("\nStopping scheduled scraper...")
                break
    else:
        # Run once
        scraper = BusinessReviewScraper(
            debug=args.debug, 
            max_reviews_per_business=args.N, 
            sort_by=args.sort_by
        )
        
        scraper.scrape_all_businesses()
        
        if args.export_csv:
            scraper.export_to_csv(args.export_csv)

if __name__ == '__main__':
    main()
