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
from dotenv import load_dotenv
import sched
import threading

load_dotenv()

MONGO_URL = os.getenv('MONGO_URL')
DB_NAME = 'test'
BUSINESSES_COLLECTION = 'businesses'
REVIEWS_COLLECTION = 'reviews'

if not MONGO_URL:
    print('Error: MONGO_URL not set in .env file.')
    sys.exit(1)

# Review sorting options
ind = {'most_relevant': 0, 'newest': 1, 'highest_rating': 2, 'lowest_rating': 3}

# CSV Headers
HEADER = ['id_review', 'caption', 'relative_date', 'retrieval_date', 'rating', 'username', 'n_review_user', 'n_photo_user', 'url_user']
HEADER_W_SOURCE = ['id_review', 'caption', 'relative_date', 'retrieval_date', 'rating', 'username', 'n_review_user', 'n_photo_user', 'url_user', 'url_source']

class BusinessReviewScraper:
    
    def __init__(self, debug=False, max_reviews_per_business=1000, sort_by='newest'):
        self.debug = debug
        self.max_reviews_per_business = max_reviews_per_business
        self.sort_by = sort_by
        self.client = MongoClient(MONGO_URL)
        self.db = self.client[DB_NAME]
        self.businesses_collection = self.db[BUSINESSES_COLLECTION]
        self.reviews_collection = self.db[REVIEWS_COLLECTION]
        # Remove logger
        # self.logger = self.__get_logger()
    
    # Remove __get_logger
    # def __get_logger(self): ...
    
    def scrape_all_businesses(self):
        print("Starting review scraping for all businesses...")

        new_businesses = list(self.businesses_collection.find({'last_scraped_at': {'$exists': False}}))
        if new_businesses:
            print(f"Found {len(new_businesses)} new businesses to scrape first")
        else:
            print("No new businesses to prioritize")

        with GoogleMapsScraper(debug=self.debug) as scraper:
            for business in new_businesses:
                try:
                    self.scrape_business_reviews(scraper, business)
                    self.businesses_collection.update_one({'_id': business['_id']}, {'$set': {'last_scraped_at': datetime.utcnow()}})
                except Exception as e:
                    print(f"Error scraping new business {business.get('business_name', 'Unknown')}: {str(e)}")
                    continue

        businesses = list(self.businesses_collection.find({}))
        print(f"Found {len(businesses)} businesses to process in regular schedule")

        if not businesses:
            print("No businesses found in the database")
            return

        with GoogleMapsScraper(debug=self.debug) as scraper:
            for business in businesses:
                try:
                    self.scrape_business_reviews(scraper, business)
                    self.businesses_collection.update_one({'_id': business['_id']}, {'$set': {'last_scraped_at': datetime.utcnow()}})
                except Exception as e:
                    print(f"Error scraping business {business.get('business_name', 'Unknown')}: {str(e)}")
                    continue

        print("Completed review scraping for all businesses")
    
    def scrape_business_reviews(self, scraper, business):
        business_name = business.get('business_name') or business.get('businessName', 'Unknown')
        business_id = business.get('_id')
        # Try both possible locations for the Google URL
        google_url = business.get('googleBusinessUrl', '')
        if not google_url:
            google_url = (
                business.get('settings', {})
                .get('reviewPlatforms', {})
                .get('google', {})
                .get('link', '')
            )
        if not google_url:
            print(f"No Google business URL found for business: {business_name}")
            return
        print(f"Scraping reviews for business: {business_name}")
        print(f"Google URL: {google_url}")
        error = scraper.sort_by(google_url, ind[self.sort_by])
        if error != 0:
            print(f"Failed to sort reviews for {business_name}")
            return
        n_reviews = 0
        offset = 0
        while n_reviews < self.max_reviews_per_business:
            reviews = scraper.get_reviews(offset)
            if len(reviews) == 0:
                print(f"No more reviews found for {business_name}")
                break
            for review in reviews:
                if n_reviews >= self.max_reviews_per_business:
                    break
                review_dict = {
                    'id_review': review.get('id_review', review.get('id', '')),
                    'caption': review.get('caption', review.get('text', '')),
                    'relative_date': review.get('relative_date', ''),
                    'retrieval_date': datetime.utcnow(),
                    'rating': review.get('rating', ''),
                    'username': review.get('username', ''),
                    'n_review_user': review.get('n_review_user', 0),
                    'n_photo_user': review.get('n_photo_user', 0),
                    'url_user': review.get('url_user', ''),
                    'business_id': str(business_id) if business_id else '',
                    'business_name': business_name if business_name else '',
                    'business_slug': business.get('slug', ''),
                    'business_url': google_url,  # Google business page
                    'scraped_at': datetime.utcnow(),
                    'review_url': f"{google_url}/review/{review.get('id_review', review.get('id', ''))}",
                    'source': 'Google'
                }
                existing_review = self.reviews_collection.find_one({
                    'id_review': review_dict['id_review'],
                    'business_id': review_dict['business_id']
                })
                if not existing_review:
                    self.reviews_collection.insert_one(review_dict)
                    n_reviews += 1
                    print(f"Added review {n_reviews} for {business_name}")
                else:
                    print(f"Review {review_dict['id_review']} already exists for {business_name}")
            offset += len(reviews)
            time.sleep(1)
        print(f"Completed scraping {n_reviews} reviews for {business_name}")



# Scheduler setup for Google reviews
main_scheduler_google = sched.scheduler(time.time, time.sleep)
hourly_scheduler_google = sched.scheduler(time.time, time.sleep)
hourly_scrape_business_ids_google = set()
last_enabled_status_google = {}

def periodic_scrape_google():
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    business_collection = db[BUSINESSES_COLLECTION]
    all_businesses = list(business_collection.find({}))
    for business in all_businesses:
        try:
            google_settings = business.get("settings", {}).get("reviewPlatforms", {}).get("google", {})
            enabled = google_settings.get("enabled", False)
            link = google_settings.get("link", None)
            business_id = str(business.get('_id'))
            was_enabled = last_enabled_status_google.get(business_id, False)
            last_enabled_status_google[business_id] = enabled
            if enabled and link:
                if business_id not in hourly_scrape_business_ids_google:
                    print(f"[IMMEDIATE] Scraping Google reviews for business: {business.get('business_name', business.get('_id'))} ({link})")
                    scrape_google_reviews_for_business(business_id)
                    hourly_scrape_business_ids_google.add(business_id)
                    # Schedule hourly scraping for this business
                    hourly_scheduler_google.enter(3600, 1, hourly_scrape_google, (business_id, link, business.get('business_name')))
            else:
                if business_id in hourly_scrape_business_ids_google:
                    hourly_scrape_business_ids_google.remove(business_id)
        except Exception as e:
            print(f"Error processing business {business.get('business_name', business.get('_id'))}: {e}")
    # Schedule next periodic scrape in 5 minutes
    main_scheduler_google.enter(300, 1, periodic_scrape_google)

def hourly_scrape_google(business_id, link, business_name):
    try:
        print(f"[HOURLY] Scraping Google reviews for business: {business_name} ({link})")
        scrape_google_reviews_for_business(business_id)
    except Exception as e:
        print(f"Error in hourly scrape for business {business_name}: {e}")
    # Reschedule next hourly scrape if still enabled
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    business_collection = db[BUSINESSES_COLLECTION]
    business = business_collection.find_one({'_id': business_id})
    if business:
        google_settings = business.get("settings", {}).get("reviewPlatforms", {}).get("google", {})
        enabled = google_settings.get("enabled", False)
        if enabled:
            hourly_scheduler_google.enter(3600, 1, hourly_scrape_google, (business_id, link, business_name))
        else:
            if business_id in hourly_scrape_business_ids_google:
                hourly_scrape_business_ids_google.remove(business_id)

def scrape_google_reviews_for_business(business_id):
    """Scrape Google reviews for a single business by business_id (string or ObjectId)."""
    from bson import ObjectId
    # Accept both string and ObjectId
    try:
        obj_id = ObjectId(business_id)
    except Exception:
        obj_id = business_id
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    businesses_collection = db[BUSINESSES_COLLECTION]
    business = businesses_collection.find_one({'_id': obj_id})
    if not business:
        print(f"Business with id {business_id} not found.")
        return
    scraper = BusinessReviewScraper(debug=False, max_reviews_per_business=1000, sort_by='newest')
    with GoogleMapsScraper(debug=False) as gmaps_scraper:
        scraper.scrape_business_reviews(gmaps_scraper, business)

def start_google_schedulers():
    main_scheduler_google.enter(0, 1, periodic_scrape_google)
    threading.Thread(target=main_scheduler_google.run, daemon=True).start()
    threading.Thread(target=hourly_scheduler_google.run, daemon=True).start()
    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        print("Shutting down Google review schedulers.")

if __name__ == "__main__":
    start_google_schedulers()
