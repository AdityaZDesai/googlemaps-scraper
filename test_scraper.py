import sys
from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv('MONGO_URL')
DB_NAME = 'test'
BUSINESSES_COLLECTION = 'businesses'
REVIEWS_COLLECTION = 'reviews'

if not MONGO_URL:
    print('Error: MONGO_URL not set in .env file.')
    sys.exit(1)

TEST_BUSINESS = {
    'business_name': 'Test Business',
    'google_business_url': 'https://maps.google.com/?cid=1234567890',
    'slug': 'test-business',
}

TEST_REVIEW = {
    'id_review': 'test_review_1',
    'caption': 'Test review',
    'relative_date': '1 day ago',
    'retrieval_date': '2024-01-01',
    'rating': 5,
    'username': 'testuser',
    'n_review_user': 1,
    'n_photo_user': 0,
    'url_user': 'https://maps.google.com/user/testuser',
    'scraped_at': datetime.utcnow(),
}

def check_mongodb_connection():
    print('Checking MongoDB connection...')
    try:
        client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=3000)
        client.server_info()  # Force connection
        print('MongoDB connection successful.')
        return client
    except Exception as e:
        print(f'Failed to connect to MongoDB: {e}')
        sys.exit(1)

def check_collections(db):
    print('Checking collections...')
    collections = db.list_collection_names()
    if BUSINESSES_COLLECTION in collections:
        print(f'Collection "{BUSINESSES_COLLECTION}" exists.')
    else:
        print(f'Collection "{BUSINESSES_COLLECTION}" does not exist. Creating...')
        db.create_collection(BUSINESSES_COLLECTION)
        print(f'Collection "{BUSINESSES_COLLECTION}" created.')
    if REVIEWS_COLLECTION in collections:
        print(f'Collection "{REVIEWS_COLLECTION}" exists.')
    else:
        print(f'Collection "{REVIEWS_COLLECTION}" does not exist. Creating...')
        db.create_collection(REVIEWS_COLLECTION)
        print(f'Collection "{REVIEWS_COLLECTION}" created.')

def test_insert_and_retrieve(db):
    print('Testing insert and retrieve for business...')
    businesses = db[BUSINESSES_COLLECTION]
    reviews = db[REVIEWS_COLLECTION]
    # Insert test business
    business_id = businesses.insert_one(TEST_BUSINESS).inserted_id
    print(f'Inserted test business with _id: {business_id}')
    # Retrieve
    found = businesses.find_one({'_id': business_id})
    if found:
        print('Successfully retrieved test business.')
    else:
        print('Failed to retrieve test business.')
    # Insert test review
    test_review = TEST_REVIEW.copy()
    test_review['business_id'] = business_id
    review_id = reviews.insert_one(test_review).inserted_id
    print(f'Inserted test review with _id: {review_id}')
    # Retrieve
    found_review = reviews.find_one({'_id': review_id})
    if found_review:
        print('Successfully retrieved test review.')
    else:
        print('Failed to retrieve test review.')
    # Clean up
    businesses.delete_one({'_id': business_id})
    reviews.delete_one({'_id': review_id})
    print('Cleaned up test data.')

def main():
    client = check_mongodb_connection()
    db = client[DB_NAME]
    check_collections(db)
    test_insert_and_retrieve(db)
    print('All MongoDB tests passed.')

if __name__ == '__main__':
    main() 