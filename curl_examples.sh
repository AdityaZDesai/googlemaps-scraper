#!/bin/bash

# Flask Scraping App - cURL Examples
# Make sure the Flask app is running on http://localhost:5000

BASE_URL="http://localhost:5000"

echo "Flask Scraping App - cURL Examples"
echo "=================================="

# 1. Health Check
echo -e "\n1. Health Check:"
curl -X GET "${BASE_URL}/health" \
  -H "Content-Type: application/json" \
  | jq '.'

# 2. List Jobs (should be empty initially)
echo -e "\n\n2. List Jobs:"
curl -X GET "${BASE_URL}/jobs" \
  -H "Content-Type: application/json" \
  | jq '.'

# 3. Start Scraping Job (with all URLs)
echo -e "\n\n3. Start Scraping Job (with all URLs):"
JOB_RESPONSE=$(curl -s -X POST "${BASE_URL}/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "business_name": "Primal Queen",
    "business_url": "https://primalqueen.com/",
    "google_maps_url": "https://www.google.com/maps/place/Primal+Queen/@40.7128,-74.0060,17z/",
    "trustpilot_url": "https://www.trustpilot.com/review/primalqueen.com"
  }')

echo "$JOB_RESPONSE" | jq '.'

# 3b. Start Scraping Job (with minimal data - missing URLs)
echo -e "\n\n3b. Start Scraping Job (with minimal data - missing URLs):"
JOB_RESPONSE_MINIMAL=$(curl -s -X POST "${BASE_URL}/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "business_name": "Example Business"
  }')

echo "$JOB_RESPONSE_MINIMAL" | jq '.'

# Extract job ID from response
JOB_ID=$(echo "$JOB_RESPONSE" | jq -r '.job_id')

if [ "$JOB_ID" != "null" ] && [ "$JOB_ID" != "" ]; then
    echo -e "\nJob ID: $JOB_ID"
    
    # 4. Check Job Status
    echo -e "\n\n4. Check Job Status:"
    curl -X GET "${BASE_URL}/status/${JOB_ID}" \
      -H "Content-Type: application/json" \
      | jq '.'
    
    # 5. Wait and check status multiple times
    echo -e "\n\n5. Monitoring Job Progress (checking every 10 seconds):"
    for i in {1..6}; do
        echo -e "\nCheck $i:"
        curl -s -X GET "${BASE_URL}/status/${JOB_ID}" \
          -H "Content-Type: application/json" \
          | jq '{status: .status, progress: .progress, statistics: .statistics}'
        
        if [ $i -lt 6 ]; then
            echo "Waiting 10 seconds..."
            sleep 10
        fi
    done
    
    # 6. Get Final Results (if completed)
    echo -e "\n\n6. Get Final Results:"
    curl -X GET "${BASE_URL}/results/${JOB_ID}" \
      -H "Content-Type: application/json" \
      | jq '{job_id: .job_id, status: .status, total_reviews: .total_reviews, statistics: .statistics}'
    
    # 7. List Jobs Again
    echo -e "\n\n7. List Jobs (after scraping):"
    curl -X GET "${BASE_URL}/jobs" \
      -H "Content-Type: application/json" \
      | jq '.'
    
    # 8. Cleanup Old Jobs
    echo -e "\n\n8. Cleanup Old Jobs:"
    curl -X POST "${BASE_URL}/cleanup" \
      -H "Content-Type: application/json" \
      -d '{"max_age_hours": 1}' \
      | jq '.'
    
else
    echo -e "\nFailed to get job ID from response"
fi

echo -e "\n\nDone!" 