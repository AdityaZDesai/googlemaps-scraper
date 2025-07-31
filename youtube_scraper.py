import os
from dotenv import load_dotenv
import json
from datetime import datetime
from search_terms import generate_search_term

# Load environment variables from .env file
load_dotenv()

try:
    from apify_client import ApifyClient
    import google.generativeai as genai
except ImportError as e:
    print(f"Error: Missing required packages. Please install with: pip install apify-client google-generativeai")
    exit(1)

# Configure Gemini API
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

def clean_youtube_url(url):
    """
    Clean YouTube URLs by ensuring proper format.
    
    Args:
        url (str): Original YouTube URL
    
    Returns:
        str: Cleaned YouTube URL
    """
    if not url:
        return url
    
    # Remove any tracking parameters
    if '&' in url:
        base_url = url.split('&')[0]
        return base_url
    
    return url

def analyze_video(video_data, business_description):
    """
    Analyze a YouTube video and classify it according to the database structure using Gemini API.
    
    Args:
        video_data (dict): YouTube video data
        business_description (str): Description of the business to match relevance
    
    Returns:
        dict: Classified video data matching the database structure, or None if not relevant
    """
    
    title = video_data.get('title', '')
    description = video_data.get('description', '')
    channel_name = video_data.get('channel', 'Unknown')
    video_id = video_data.get('id', '')
    url = clean_youtube_url(video_data.get('url', ''))
    view_count = video_data.get('viewCount', 0)
    like_count = video_data.get('likes', 0)
    comment_count = video_data.get('commentCount', 0)
    upload_date = video_data.get('uploadDate', '')
    duration = video_data.get('duration', '')
    keywords = video_data.get('keywords', [])
    date = video_data.get('uploadDate', '')
    
    # Combine title and description for analysis
    full_text = f"{title} {description}".strip()
    
    # Format keywords for display
    keywords_text = ", ".join(keywords) if keywords else "None"
    
    # Prompt for Gemini API
    prompt = f"""
    Analyze this YouTube video for business relevance and sentiment:
    
    Business Description: {business_description}
    
    Video Title: {title}
    Video Description: {description}
    Channel Name: {channel_name}
    Keywords: {keywords_text}
    Upload Date: {date}
    
    Please classify this video according to these criteria:
    
    1. RELEVANCE: Is this video relevant to the business described above? (yes/no)
    2. SENTIMENT: If relevant, is the sentiment positive or negative?
    3. RATING: If relevant, provide a star rating from 1-5 (1=very negative, 5=very positive)
    
    Respond ONLY in this exact JSON format:
    {{
        "relevant": true/false,
        "sentiment": "positive"/"negative"/null,
        "rating": 1-5/null,
        "reasoning": "brief explanation"
    }}
    
    Rules:
    - Only mark as relevant if the video directly relates to the business and the description of the business.
    - Consider the keywords when determining relevance - they often indicate the video's main topics.
    - The way to check that the video is negative or not, is to see if the video is complaining about the business or the product and if potential customers see it, will they be turned off from the business.
    - For positive sentiment: rating 4-5 stars (4=positive, 5=very positive)
    - For negative sentiment: rating 1-2 stars (1=very negative, 2=negative)
    - For neutral sentiment: rating 3 stars
    - If not relevant, sentiment and rating should be null
    """
    
    try:
        # Get response from Gemini API
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Parse JSON response - handle markdown code blocks
        try:
            # Remove markdown code blocks if present
            cleaned_response = response_text.strip()
            if cleaned_response.startswith('```json'):
                cleaned_response = cleaned_response[7:]  # Remove ```json
            if cleaned_response.startswith('```'):
                cleaned_response = cleaned_response[3:]  # Remove ```
            if cleaned_response.endswith('```'):
                cleaned_response = cleaned_response[:-3]  # Remove trailing ```
            
            cleaned_response = cleaned_response.strip()
            analysis = json.loads(cleaned_response)
        except json.JSONDecodeError as e:
            print(f"ERROR: Failed to parse Gemini response as JSON: {response_text}")
            print(f"Cleaned response: {cleaned_response}")
            print(f"JSON error: {str(e)}")
            return None
        
        # Check if video is relevant
        if not analysis.get('relevant', False):
            return None
        
        # Return classified video data
        return {
            'platform': 'youtube',
            'sentiment': analysis.get('sentiment'),
            'rating': analysis.get('rating'),
            'username': channel_name,
            'caption': title,
            'url_user': url,
            'url_post': url,
            'engagement': {
                'views': view_count,
                'likes': like_count,
                'comments': comment_count
            },
            'metadata': {
                'video_id': video_id,
                'duration': duration,
                'upload_date': upload_date,
                'date': date,
                'keywords': keywords,
                'reasoning': analysis.get('reasoning', '')
            },
            'scraped_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"ERROR: Failed to analyze video: {str(e)}")
        return None

def scrape_youtube(company_name, company_url, results_limit=50):
    """
    Scrape and classify YouTube videos for a business.
    
    Args:
        company_name (str): Name of the business
        company_url (str): URL of the business website
        results_limit (int): Number of results to return (default: 50)
    
    Returns:
        list: List of relevant classified YouTube videos
    """
    try:
        print(f"DEBUG: Starting YouTube scraping for {company_name}")
        
        # Generate business description
        print("DEBUG: Generating business description...")
        business_description = generate_search_term(company_name, company_url)
        
        if business_description in ["INVALID_URL", "Request failed with status code: 500", 
                                 "No results found in the response.", "Failed to parse JSON response."]:
            print(f"DEBUG: Failed to generate business description: {business_description}")
            return []
        
        print(f"DEBUG: Business description generated: {business_description[:100]}...")
        
        # Initialize the ApifyClient
        api_token = os.getenv("APIFY_API")
        if not api_token:
            print("ERROR: APIFY_API not found in .env file.")
            return []
        
        client = ApifyClient(api_token)
        
        # Prepare the Actor input
        run_input = {
            "startUrls": [
                f"https://www.youtube.com/results?search_query={company_name.replace(' ', '+')}",
            ],
            "youtubeHandles": [],
            "keywords": [company_name],
            "gl": "us",
            "hl": "en",
            "uploadDate": "all",
            "duration": "all",
            "features": "all",
            "sort": "r",  # relevance
            "maxItems": results_limit,
            "customMapFunction": "(object) => { return {...object} }",
        }
        
        print("DEBUG: Running Apify YouTube scraper...")
        run = client.actor("1p1aa7gcSydPkAE0d").call(run_input=run_input)
        
        # Fetch results
        print("DEBUG: Fetching YouTube videos...")
        raw_videos = []
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            raw_videos.append(item)
        
        print(f"DEBUG: Found {len(raw_videos)} raw YouTube videos")
        
        # Classify videos
        print("DEBUG: Classifying videos for relevance...")
        relevant_videos = []
        for video in raw_videos:
            classified = analyze_video(video, business_description)
            if classified:
                relevant_videos.append(classified)
        
        print(f"DEBUG: Found {len(relevant_videos)} relevant videos")
        
        return relevant_videos
        
    except Exception as e:
        print(f"ERROR: Failed to scrape YouTube: {str(e)}")
        return []

def scrape_youtube_with_custom_input(custom_input):
    """
    Scrape YouTube with custom input parameters.
    
    Args:
        custom_input (dict): Custom input parameters for the YouTube scraper
    
    Returns:
        list: List of YouTube videos
    """
    try:
        print("DEBUG: Starting YouTube scraping with custom input")
        
        # Initialize the ApifyClient
        api_token = os.getenv("APIFY_API")
        if not api_token:
            print("ERROR: APIFY_API not found in .env file.")
            return []
        
        client = ApifyClient(api_token)
        
        print("DEBUG: Running Apify YouTube scraper with custom input...")
        run = client.actor("1p1aa7gcSydPkAE0d").call(run_input=custom_input)
        
        # Fetch results
        print("DEBUG: Fetching YouTube videos...")
        videos = []
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            videos.append(item)
        
        print(f"DEBUG: Found {len(videos)} YouTube videos")
        
        return videos
        
    except Exception as e:
        print(f"ERROR: Failed to scrape YouTube with custom input: {str(e)}")
        return []

if __name__ == "__main__":
    # Example usage of the YouTube scraper
    company_name = "Primal Queen"
    company_url = "https://primalqueen.com/"
    
    print("=" * 80)
    print("YOUTUBE SCRAPER")
    print("=" * 80)
    
    # Get relevant YouTube videos
    relevant_videos = scrape_youtube(company_name, company_url, results_limit=20)
    
    print(f"\nFound {len(relevant_videos)} relevant videos:")
    print("=" * 80)
    
    for i, video in enumerate(relevant_videos, 1):
        print(f"\n--- Video {i} ---")
        print(f"Sentiment: {video['sentiment']}")
        print(f"Rating: {video['rating']} stars")
        print(f"Channel: {video['username']}")
        print(f"Title: {video['caption'][:200]}...")
        print(f"URL: {video['url_user']}")
        print(f"Views: {video['engagement']['views']}")
        print(f"Likes: {video['engagement']['likes']}")
        print(f"Comments: {video['engagement']['comments']}")
        print("-" * 40)
    

