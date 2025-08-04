# Flask Scraping App

A comprehensive Flask application that orchestrates multiple scrapers to collect business reviews and mentions from various online sources while preventing duplicates.

## Features

- **Multi-Source Scraping**: Collects data from Google Reviews, Trustpilot, Reddit, YouTube, TikTok, and Internet search
- **Duplicate Prevention**: Uses URL normalization and review ID tracking to prevent duplicate entries
- **Asynchronous Processing**: Runs scraping jobs in background threads
- **Progress Tracking**: Real-time progress monitoring for each scraping job
- **RESTful API**: Clean REST endpoints for easy integration
- **Job Management**: Track, monitor, and manage multiple scraping jobs

## Supported Sources

1. **Google Reviews** - Scrapes reviews from Google Maps business listings (requires `google_maps_url`)
2. **Trustpilot Reviews** - Collects customer reviews from Trustpilot (requires `trustpilot_url`)
3. **Reddit** - Searches for relevant discussions and mentions (requires `business_url`)
4. **YouTube** - Finds videos mentioning the business (requires `business_url`)
5. **TikTok** - Analyzes TikTok content for business mentions (requires `business_url`)
6. **Internet Search** - General web search for business mentions and reviews (requires `business_url`)

**URL Requirements:**
- **Google Reviews**: Requires `google_maps_url`
- **Trustpilot Reviews**: Requires `trustpilot_url`
- **Reddit**: Requires `business_url` (for business description)
- **YouTube**: Requires `business_url` (for business description)
- **TikTok**: Requires `business_url` (for business description)
- **Internet Search**: Requires `business_url` (for business description)

## Installation

1. **Clone the repository** (if not already done):
   ```bash
   git clone <repository-url>
   cd googlemaps-scraper
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   Create a `.env` file in the project root with the following variables:
   ```env
   GOOGLE_API_KEY=your_google_api_key_here
   MONGO_URL=your_mongodb_connection_string
   SEARCH1API_KEY=your_search1api_key_here
   APIFY_API_KEY=your_apify_api_key_here
   ```

## Usage

### Starting the Flask App

```bash
python app.py
```

The app will start on `http://localhost:5000` by default. You can change the port by setting the `PORT` environment variable.

### API Endpoints

#### 1. Health Check
```http
GET /health
```
Returns the health status of the application.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00.000Z",
  "active_jobs": 2
}
```

#### 2. Start Scraping
```http
POST /scrape
Content-Type: application/json

{
  "business_name": "Primal Queen",
  "business_url": "https://primalqueen.com/",
  "google_maps_url": "https://www.google.com/maps/place/Primal+Queen/@40.7128,-74.0060,17z/",
  "trustpilot_url": "https://www.trustpilot.com/review/primalqueen.com"
}
```

**Note**: Only `business_name` is required. Missing URLs will cause the corresponding platforms to be skipped:

- **Missing `google_maps_url`**: Skips Google Reviews
- **Missing `trustpilot_url`**: Skips Trustpilot Reviews  
- **Missing `business_url`**: Skips Reddit, YouTube, TikTok, and Internet Search (all require business_url for business description)

**Example with minimal data**:
```http
POST /scrape
Content-Type: application/json

{
  "business_name": "Example Business"
}
```
This will only scrape Google Reviews and Trustpilot Reviews (if their respective URLs are provided).

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "started",
  "message": "Scraping started for Primal Queen",
  "business_name": "Primal Queen"
}
```

#### 3. Get Job Status
```http
GET /status/{job_id}
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running",
  "progress": 50,
  "statistics": {
    "google": 15,
    "trustpilot": 8,
    "reddit": 12,
    "youtube": 5,
    "tiktok": 0,
    "internet": 0,
    "total_unique": 40
  },
  "start_time": "2024-01-01T12:00:00.000Z",
  "end_time": null,
  "error": null
}
```

#### 4. Get Job Results
```http
GET /results/{job_id}
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "business_name": "Primal Queen",
  "total_reviews": 85,
  "statistics": {
    "google": 25,
    "trustpilot": 12,
    "reddit": 18,
    "youtube": 8,
    "tiktok": 15,
    "internet": 7,
    "total_unique": 85
  },
  "results": {
    "google": [...],
    "trustpilot": [...],
    "reddit": [...],
    "youtube": [...],
    "tiktok": [...],
    "internet": [...]
  },
  "all_reviews": [...],
  "start_time": "2024-01-01T12:00:00.000Z",
  "end_time": "2024-01-01T12:15:30.000Z"
}
```

#### 5. List All Jobs
```http
GET /jobs
```

**Response:**
```json
{
  "jobs": [
    {
      "job_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "completed",
      "progress": 100,
      "business_name": "Primal Queen",
      "total_reviews": 85,
      "start_time": "2024-01-01T12:00:00.000Z",
      "end_time": "2024-01-01T12:15:30.000Z"
    }
  ],
  "total_jobs": 1
}
```

#### 6. Cleanup Old Jobs
```http
POST /cleanup
Content-Type: application/json

{
  "max_age_hours": 24
}
```

**Response:**
```json
{
  "message": "Cleaned up 3 old jobs",
  "remaining_jobs": 2
}
```

## Review Data Structure

All scrapers return reviews in a standardized format:

```json
{
  "_id": "unique_review_id",
  "id_review": "review_identifier",
  "caption": "Review text content",
  "relative_date": "2 days ago",
  "retrieval_date": "2024-01-01T12:00:00.000Z",
  "rating": 4,
  "username": "John Doe",
  "n_review_user": 5,
  "n_photo_user": 2,
  "url_user": "https://example.com/user/profile",
  "business_id": "business_identifier",
  "business_name": "Business Name",
  "business_slug": "business-name",
  "business_url": "https://business.com",
  "scraped_at": "2024-01-01T12:00:00.000Z",
  "review_url": "https://example.com/review/123",
  "source": "Google",
  "sentiment": "positive",
  "quotation_amount": 0,
  "status": "active"
}
```

## Duplicate Prevention

The app prevents duplicates using multiple strategies:

1. **URL Normalization**: URLs are normalized by removing protocols, www prefixes, trailing slashes, and tracking parameters
2. **Review ID Tracking**: Each review has a unique ID that's tracked across all sources
3. **Source-Specific Deduplication**: Reviews found in multiple sources are only included once

## Testing

Use the provided test script to verify the app is working correctly:

```bash
python test_flask_app.py
```

This will:
1. Test the health check endpoint
2. Start a scraping job
3. Monitor the job progress
4. Retrieve the final results
5. Test cleanup functionality

## Configuration

### Environment Variables

- `GOOGLE_API_KEY`: Required for Gemini AI analysis
- `MONGO_URL`: MongoDB connection string (optional, for data persistence)
- `SEARCH1API_KEY`: Required for internet search functionality
- `APIFY_API_KEY`: Required for Reddit, YouTube, and TikTok scraping
- `PORT`: Flask app port (default: 5000)
- `FLASK_DEBUG`: Enable debug mode (default: False)

### Scraping Limits

You can adjust scraping limits in the `app.py` file:

- Google Reviews: `max_reviews=100`
- Reddit: `results_limit=50`
- YouTube: `results_limit=50`
- Internet Search: `max_results_per_term=20`

## Error Handling

The app includes comprehensive error handling:

- **Individual scraper failures** don't stop the entire process
- **Network timeouts** are handled gracefully
- **API rate limits** are respected
- **Invalid URLs** are logged and skipped
- **Missing API keys** are detected and reported

## Performance Considerations

- **Memory Management**: Old completed jobs are automatically cleaned up
- **Concurrent Jobs**: Multiple scraping jobs can run simultaneously
- **Progress Tracking**: Real-time progress updates without blocking
- **Resource Cleanup**: Background threads are properly managed

## Troubleshooting

### Common Issues

1. **Missing API Keys**: Ensure all required API keys are set in the `.env` file
2. **Network Issues**: Check internet connectivity and API service status
3. **Rate Limiting**: Some APIs have rate limits; the app includes delays to respect these
4. **Memory Usage**: Use the cleanup endpoint to remove old jobs if memory usage is high

### Logs

The app provides detailed logging for debugging:

- `[INFO]` messages for normal operation
- `[ERROR]` messages for failures
- `[WARNING]` messages for potential issues

## Security Considerations

- **API Key Protection**: Never commit API keys to version control
- **Input Validation**: All inputs are validated before processing
- **CORS**: Cross-origin requests are enabled for frontend integration
- **Error Messages**: Sensitive information is not exposed in error responses

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the same license as the original repository. 