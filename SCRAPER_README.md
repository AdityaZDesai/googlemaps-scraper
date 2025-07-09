# Google Maps Business Review Scraper

This scraper connects to a MongoDB database, iterates through businesses, and scrapes their Google Maps reviews every 3 hours.

## Features

- **MongoDB Integration**: Connects to MongoDB database "test" and collection "businesses"
- **Scheduled Scraping**: Runs every 3 hours automatically
- **Duplicate Prevention**: Checks for existing reviews before adding new ones
- **Comprehensive Logging**: Detailed logs for monitoring and debugging
- **CSV Export**: Export all scraped reviews to CSV format
- **Error Handling**: Robust error handling for individual businesses

## Database Schema

### Businesses Collection
```json
{
  "_id": "ObjectId",
  "business_name": "String",
  "slug": "String", 
  "google_business_url": "String",
  "createdAt": "Date",
  "updatedAt": "Date",
  "__v": "Number"
}
```

### Reviews Collection (Auto-created)
```json
{
  "_id": "ObjectId",
  "id_review": "String",
  "caption": "String",
  "relative_date": "String",
  "retrieval_date": "String",
  "rating": "Number",
  "username": "String",
  "n_review_user": "Number",
  "n_photo_user": "Number",
  "url_user": "String",
  "business_id": "ObjectId",
  "business_name": "String",
  "business_slug": "String",
  "google_business_url": "String",
  "scraped_at": "Date"
}
```

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Make sure MongoDB is running on `localhost:27017`

3. Ensure your businesses collection has the required fields:
   - `business_name`: Name of the business
   - `google_business_url`: Google Maps URL for the business

## Usage

### Option 1: Interactive Runner (Recommended)
```bash
python run_scraper.py
```

This will show you a menu with options:
1. Run scraper once
2. Run scraper with scheduling (every 3 hours)
3. Run scraper with debug mode
4. Export existing reviews to CSV
5. Show help

### Option 2: Direct Command Line

#### Run once:
```bash
python scraper.py
```

#### Run with scheduling (every 3 hours):
```bash
python scraper.py --schedule
```

#### Run with debug mode:
```bash
python scraper.py --debug
```

#### Export to CSV:
```bash
python scraper.py --export-csv output.csv
```

#### Customize number of reviews per business:
```bash
python scraper.py --N 50
```

#### Change review sorting:
```bash
python scraper.py --sort_by newest
# Options: most_relevant, newest, highest_rating, lowest_rating
```

## Command Line Arguments

- `--N`: Number of reviews to scrape per business (default: 100)
- `--sort_by`: Review sorting method (default: newest)
- `--debug`: Run with browser GUI for debugging
- `--export-csv`: Export reviews to CSV file
- `--schedule`: Run every 3 hours automatically

## Logging

The scraper creates detailed logs in `business_scraper.log` with the following information:
- Business processing status
- Number of reviews scraped per business
- Errors and warnings
- Scheduling information

## Scheduling

When using the `--schedule` option, the scraper will:
1. Run immediately when started
2. Continue running every 3 hours
3. Log all activities
4. Stop gracefully when you press Ctrl+C

## Error Handling

The scraper includes robust error handling:
- Individual business failures don't stop the entire process
- Network errors are logged and retried
- Missing Google URLs are logged as warnings
- Duplicate reviews are automatically skipped

## Output Files

- `business_scraper.log`: Detailed logging information
- `business_reviews.csv`: Exported reviews (when using --export-csv)

## MongoDB Connection

The scraper connects to:
- **URL**: `mongodb://localhost:27017/`
- **Database**: `test`
- **Businesses Collection**: `businesses`
- **Reviews Collection**: `reviews` (auto-created)

## Example Business Document

```json
{
  "_id": "686c0842c12ba07a5cb0e15e",
  "business_name": "Some Business",
  "slug": "some-business",
  "google_business_url": "https://www.google.com/maps/place/...",
  "createdAt": "2025-07-07T17:47:46.240+00:00",
  "updatedAt": "2025-07-07T17:47:46.240+00:00",
  "__v": 0
}
```

## Troubleshooting

### Common Issues:

1. **MongoDB Connection Error**: Make sure MongoDB is running on localhost:27017
2. **No Businesses Found**: Check that your businesses collection has documents
3. **Missing Google URLs**: Ensure businesses have valid `google_business_url` fields
4. **Chrome Driver Issues**: The scraper uses Selenium with Chrome - make sure Chrome is installed

### Debug Mode:
Use `--debug` flag to see the browser in action and troubleshoot scraping issues.

## Performance Notes

- The scraper includes delays between requests to be respectful to Google
- Reviews are checked for duplicates before insertion
- The process can handle large numbers of businesses efficiently
- Memory usage is optimized for long-running scheduled operations 