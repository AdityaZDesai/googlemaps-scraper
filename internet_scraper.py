import os
from dotenv import load_dotenv
import json
from datetime import datetime
import uuid
from typing import List, Dict, Any
import google.generativeai as genai
from searchapi import search_search1api
from tiktok_analyzer import get_business_description_from_url

# Load environment variables from .env file
load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

def generate_search_terms(business_name: str, business_description: str) -> List[str]:
    """
    Generate a range of search terms to find the best and most comprehensive results for a business.
    
    Args:
        business_name (str): Name of the business
        business_description (str): Description of the business
    
    Returns:
        List[str]: List of search terms to use for scraping
    """
    prompt = f"""
    Generate a comprehensive list of search terms to find the best and most relevant information about this business on the internet.
    
    Business Name: {business_name}
    Business Description: {business_description}
    
    Generate 5 search terms that would help find:
    1. Reviews and customer feedback
    2. News articles and press coverage
    3. Social media mentions
    4. Blog posts and articles
    5. Forum discussions
    6. Business listings and directories
    7. Any other relevant online presence
    
    Focus on terms that would yield high-quality, relevant results.
    Include variations with and without quotes, location-specific terms if relevant, and industry-specific keywords.
    
    Return ONLY a JSON array of search terms, like this:
    ["search term 1", "search term 2", "search term 3"]
    """
    
    try:
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Parse JSON response
        if response_text.startswith('```json'):
            response_text = response_text[7:-3]  # Remove ```json and ```
        elif response_text.startswith('```'):
            response_text = response_text[3:-3]  # Remove ``` and ```
        
        search_terms = json.loads(response_text)
        return search_terms if isinstance(search_terms, list) else []
        
    except Exception as e:
        print(f"[ERROR] Failed to generate search terms: {e}")
        # Fallback search terms
        return [
            f'"{business_name}"',
            f'"{business_name}" reviews',
            f'"{business_name}" customer feedback',
            f'"{business_name}" complaints',
            f'"{business_name}" experience',
            business_name
        ]

def filter_results(results: List[Dict], business_name: str) -> List[Dict]:
    """
    Filter search results to exclude TikTok, Trustpilot, Reddit, YouTube sites and irrelevant results.
    
    Args:
        results (List[Dict]): Raw search results from Search1API
        business_name (str): Name of the business to filter for relevance
    
    Returns:
        List[Dict]: Filtered results
    """
    filtered_results = []
    
    for result in results:
        url = result.get('url', '').lower()
        title = result.get('title', '').lower()
        snippet = result.get('snippet', '').lower()
        
        # Skip TikTok, Trustpilot, Reddit, and YouTube sites
        if any(site in url for site in ['tiktok.com', 'trustpilot.com', 'trustpilot.co.uk', 'reddit.com', 'youtube.com', 'youtu.be']):
            continue
        
        # Skip social media platforms that don't provide useful content
        if any(site in url for site in ['facebook.com', 'instagram.com', 'twitter.com', 'x.com']):
            continue
        
        # Basic relevance check - must mention the business name
        business_name_lower = business_name.lower()
        if business_name_lower not in title and business_name_lower not in snippet:
            continue
        
        filtered_results.append(result)
    
    return filtered_results

def analyze_result_relevance(result: Dict, business_name: str, business_description: str) -> Dict[str, Any]:
    """
    Analyze a search result for relevance and sentiment using Gemini API.
    
    Args:
        result (Dict): Search result data
        business_name (str): Name of the business
        business_description (str): Description of the business
    
    Returns:
        Dict[str, Any]: Analysis result with relevance, sentiment, and rating
    """
    title = result.get('title', '')
    snippet = result.get('snippet', '')
    url = result.get('url', '')
    
    prompt = f"""
    Analyze this internet search result for business relevance and sentiment:
    
    Business Name: {business_name}
    Business Description: {business_description}
    
    Search Result:
    Title: {title}
    Snippet: {snippet}
    URL: {url}
    
    Please classify this result according to these criteria:
    
    1. RELEVANCE: Is this result relevant to the business described above? (yes/no)
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
    - Only mark as relevant if the result directly relates to the business and the description of the business.
    - The way to check that the result is negative or not, is to see if it's complaining about the business or the product and if potential customers see it, will they be turned off from the business.
    - For positive sentiment: rating 4-5 stars (4=positive, 5=very positive)
    - For negative sentiment: rating 1-2 stars (1=very negative, 2=negative)
    - For neutral sentiment: rating 3 stars
    - If not relevant, sentiment and rating should be null
    """
    
    try:
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
        
        return {
            'relevant': True,
            'sentiment': sentiment,
            'rating': rating,
            'reasoning': analysis.get('reasoning', '')
        }
        
    except Exception as e:
        print(f"[ERROR] Failed to analyze result: {e}")
        return None

def create_result_entry(result: Dict, analysis: Dict, business_name: str, business_description: str) -> Dict[str, Any]:
    """
    Create a standardized result entry matching the required database structure.
    
    Args:
        result (Dict): Search result data
        analysis (Dict): Analysis result from analyze_result_relevance
        business_name (str): Name of the business
        business_description (str): Description of the business
    
    Returns:
        Dict[str, Any]: Standardized result entry
    """
    if not analysis or not analysis.get('relevant'):
        return None
    
    # Generate unique ID
    unique_id = str(uuid.uuid4())
    
    # Create review ID from URL or generate one
    review_id = result.get('url', '').replace('https://', '').replace('http://', '').replace('/', '_')[:50]
    if not review_id:
        review_id = f"internet_{unique_id[:20]}"
    
    # Extract username from URL or use default
    username = "Internet User"
    url = result.get('url', '')
    if 'blog' in url or 'article' in url:
        username = "Blog Author"
    elif 'news' in url or 'press' in url:
        username = "News Author"
    elif 'forum' in url or 'discussion' in url:
        username = "Forum User"
    
    # Create business slug
    business_slug = business_name.lower().replace(' ', '-').replace('&', 'and').replace("'", '').replace('"', '')
    
    now = datetime.utcnow()
    
    return {
        '_id': unique_id,
        'id_review': review_id,
        'caption': result.get('snippet', ''),
        'relative_date': 'Recently',  # Internet results don't have specific dates
        'retrieval_date': now,
        'rating': analysis.get('rating', 3),
        'username': username,
        'n_review_user': 0,
        'n_photo_user': 0,
        'url_user': url,
        'business_id': f"internet_{business_slug}",
        'business_name': business_name,
        'business_slug': business_slug,
        'business_url': url,
        'scraped_at': now,
        'review_url': url,
        'source': 'Internet',
        'sentiment': analysis.get('sentiment', 'positive'),
        'quotation_amount': 0,
        'status': 'active'
    }

def scrape_internet_for_business(business_name: str, business_description: str, max_results_per_term: int = 20) -> List[Dict[str, Any]]:
    """
    Main function to scrape the internet for business information.
    
    Args:
        business_name (str): Name of the business to search for
        business_description (str): Description of the business
        max_results_per_term (int): Maximum number of results to get per search term
    
    Returns:
        List[Dict[str, Any]]: List of standardized result entries
    """
    print(f"[INFO] Starting internet scrape for: {business_name}")
    
    # Generate search terms
    print("[INFO] Generating search terms...")
    search_terms = generate_search_terms(business_name, business_description)
    print(f"[INFO] Generated {len(search_terms)} search terms: {search_terms}")
    
    all_results = []
    
    # Search for each term
    for i, search_term in enumerate(search_terms):
        print(f"[INFO] Searching for term {i+1}/{len(search_terms)}: '{search_term}'")
        
        try:
            # Get search results
            results = search_search1api(search_term, max_results_per_term)
            
            if not results:
                print(f"[WARNING] No results found for term: {search_term}")
                continue
            
            print(f"[INFO] Found {len(results)} results for term: {search_term}")
            
            # Filter results
            filtered_results = filter_results(results, business_name)
            print(f"[INFO] After filtering: {len(filtered_results)} relevant results")
            
            # Analyze each result
            for result in filtered_results:
                analysis = analyze_result_relevance(result, business_name, business_description)
                
                if analysis and analysis.get('relevant'):
                    result_entry = create_result_entry(result, analysis, business_name, business_description)
                    if result_entry:
                        all_results.append(result_entry)
                        print(f"[INFO] Added relevant result: {result.get('title', 'No title')[:50]}...")
            
        except Exception as e:
            print(f"[ERROR] Failed to process search term '{search_term}': {e}")
            continue
    
    print(f"[INFO] Internet scrape completed. Found {len(all_results)} relevant results.")
    return all_results

if __name__ == "__main__":
    # Example usage
    business_name = "Primal Queen"
    business_description = get_business_description_from_url("https://primalqueen.com/", business_name)
    
    results = scrape_internet_for_business(business_name, business_description)
    
    print(f"\nFound {len(results)} relevant results:")
    for i, result in enumerate(results[:5]):  # Show first 5 results
        print(f"\n{i+1}. {result['business_name']}")
        print(f"   Caption: {result['caption'][:100]}...")
        print(f"   Sentiment: {result['sentiment']}")
        print(f"   Rating: {result['rating']}")
        print(f"   URL: {result['url_user']}") 