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

def clean_reddit_url(url):
    """
    Clean Reddit URLs by removing 'old.' prefix and ensuring proper format.
    
    Args:
        url (str): Original Reddit URL
    
    Returns:
        str: Cleaned Reddit URL
    """
    if not url:
        return url
    
    # Remove 'old.' prefix from Reddit URLs
    if 'old.reddit.com' in url:
        url = url.replace('old.reddit.com', 'reddit.com')
    
    return url

def summarise(post, business_description):
    """
    Analyze a Reddit post and classify it according to the database structure using Gemini API.
    
    Args:
        post (dict): Reddit post data containing title and content
        business_description (str): Description of the business to match relevance
    
    Returns:
        dict: Classified post data matching the database structure, or None if not relevant
    """
    
    title = post.get('title', '')
    content = post.get('selftext', '')
    author = post.get('author', 'Unknown')
    post_id = post.get('id', '')
    url = clean_reddit_url(post.get('url', ''))
    score = post.get('score', 0)
    num_comments = post.get('numComments', 0)
    created = post.get('created', '')
    
    # Combine title and content for analysis
    full_text = f"{title} {content}".strip()
    
    # Prompt for Gemini API
    prompt = f"""
    Analyze this Reddit post for business relevance and sentiment:
    
    Business Description: {business_description}
    
    Post Title: {title}
    Post Content: {content}
    
    Please classify this post according to these criteria:
    
    1. RELEVANCE: Is this post relevant to the business described above? (yes/no)
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
    - Only mark as relevant if the post directly relates to the business and the description of the business.
    - The way to check that the post is negative or not, is to see if the post is complaining about the business or the product and if potential customers see it, will they be turned off from the business.
    - For positive sentiment: rating 4-5 stars (4=positive, 5=very positive)
    - For negative sentiment: rating 1-2 stars (1=very negative, 2=negative)
    - For neutral sentiment: rating 3 stars
    - If not relevant, sentiment and rating should be null
    """
    
    try:
        # Get response from Gemini API
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Parse JSON response
        if response_text.startswith('```json'):
            response_text = response_text[7:-3]  # Remove ```json and ```
        elif response_text.startswith('```'):
            response_text = response_text[3:-3]  # Remove ``` and ```
        
        analysis = json.loads(response_text)
        
        # Validate response
        if not analysis.get('relevant', False):
            return None
        
        sentiment = analysis.get('sentiment')
        rating = analysis.get('rating')
        
        # Validate sentiment and rating
        if sentiment not in ['positive', 'negative']:
            sentiment = 'positive'  # Default to positive if unclear
        
        # Validate and adjust rating based on sentiment
        if sentiment == 'positive':
            if not rating or rating < 4:
                rating = 4  # Default positive rating
        elif sentiment == 'negative':
            if not rating or rating > 2:
                rating = 2  # Default negative rating
        else:
            rating = 3  # Default neutral rating
        
        # Create database structure
        classified_post = {
            "_id": f"reddit_{post_id}",
            "id_review": post_id,
            "caption": full_text[:500] + "..." if len(full_text) > 500 else full_text,
            "relative_date": "recent",  # You might want to parse the actual date
            "retrieval_date": datetime.now().isoformat() + "Z",
            "rating": rating,
            "username": author,
            "n_review_user": 0,  # Not applicable for Reddit
            "n_photo_user": 0,   # Not applicable for Reddit
            "url_user": url,
            "business_id": "reddit_business",  # You'll need to set this
            "business_name": "Reddit Business",  # You'll need to set this
            "business_slug": "reddit-business",  # You'll need to set this
            "business_url": url,
            "scraped_at": datetime.now().isoformat() + "Z",
            "review_url": url,
            "source": "Reddit",
            "sentiment": sentiment,
            "quotation_amount": 0,
            "status": "active"
        }
        
        return classified_post
        
    except Exception as e:
        print(f"Error analyzing post with Gemini API: {e}")
        return None

def scrape_reddit(company_name, company_url, results_limit=20):
    """
    Scrape and classify Reddit posts for a business.
    
    Args:
        company_name (str): Name of the business
        company_url (str): URL of the business website
        results_limit (int): Number of results to return (default: 20)
    
    Returns:
        list: List of relevant classified Reddit posts
    """
    try:
        print(f"DEBUG: Starting Reddit scraping for {company_name}")
        
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
        
        # Prepare search terms from company name
        search_terms = [company_name.lower()]
        
        # Prepare the Actor input
        run_input = {
            "searchList": search_terms,
            "resultsLimit": results_limit,
            "sortBy": "relevance",
            "over18": True,
            "proxy": {
                "useApifyProxy": True,
                "apifyProxyGroups": ["RESIDENTIAL"],
            },
        }
        
        print("DEBUG: Running Apify Reddit scraper...")
        run = client.actor("tW0tdmu7XAIoNezk2").call(run_input=run_input)
        
        # Fetch results
        print("DEBUG: Fetching Reddit posts...")
        raw_posts = []
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            raw_posts.append(item)
        
        print(f"DEBUG: Found {len(raw_posts)} raw Reddit posts")
        
        # Classify posts
        print("DEBUG: Classifying posts for relevance...")
        relevant_posts = []
        for post in raw_posts:
            classified = summarise(post, business_description)
            if classified:
                relevant_posts.append(classified)
        
        print(f"DEBUG: Found {len(relevant_posts)} relevant posts")
        
        return relevant_posts
        
    except Exception as e:
        print(f"ERROR: Failed to scrape Reddit: {str(e)}")
        return []

if __name__ == "__main__":
    # Example usage of the simplified scrape_reddit function
    company_name = "Primal Queen"
    company_url = "https://primalqueen.com/"
    
    print("=" * 80)
    print("REDDIT SCRAPER - SIMPLIFIED")
    print("=" * 80)
    
    # Get relevant Reddit posts
    relevant_posts = scrape_reddit(company_name, company_url, results_limit=20)
    
    print(f"\nFound {len(relevant_posts)} relevant posts:")
    print("=" * 80)
    
    for i, post in enumerate(relevant_posts, 1):
        print(f"\n--- Post {i} ---")
        print(f"Sentiment: {post['sentiment']}")
        print(f"Rating: {post['rating']} stars")
        print(f"Username: {post['username']}")
        print(f"Caption: {post['caption'][:200]}...")
        print(f"URL: {post['url_user']}")
        print("-" * 40)