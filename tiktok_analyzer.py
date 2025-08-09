import os
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any
from dotenv import load_dotenv
from apify_client import ApifyClient
from search_terms import call_gemini_api, generate_search_term
from searchapi import search_search1api

load_dotenv()


def get_business_description_from_url(url: str, company_name: str) -> str:
    """
    Extract business description from a single URL using the existing generate_search_term function.
    
    Args:
        url (str): The URL to scrape
        company_name (str): Name of the company for context
        
    Returns:
        str: Business description extracted from the URL
    """
    try:
        print(f"[INFO] Extracting business description from: {url}")
        
        # Use the existing generate_search_term function
        description = generate_search_term(company_name, url)
        
        if description in ["INVALID_URL", "Request failed with status code: 500", 
                          "No results found in the response.", "Failed to parse JSON response."]:
            print(f"[ERROR] Failed to extract description: {description}")
            return f"{company_name} - Business information unavailable"
        
        print(f"[INFO] Extracted business description: {description}")
        return description
        
    except Exception as e:
        print(f"[ERROR] Failed to extract business description: {e}")
        return f"{company_name} - Business description extraction failed"

def analyze_tiktok_content_for_business(company_name: str, business_description: str) -> List[Dict[str, Any]]:
    """
    Comprehensive function that takes a company name and business description,
    searches TikTok for relevant content, transcribes videos, and analyzes relevance.
    
    Args:
        company_name (str): Name of the company
        business_description (str): Description of the business
        
    Returns:
        List[Dict]: List of relevant TikTok results in the specified format
    """
    
    print(f"[INFO] Starting TikTok analysis for: {company_name}")
    
    # Step 1: Generate TikTok search keywords
    keywords = generate_tiktok_keywords(company_name, business_description)
    print(f"[INFO] Generated search keywords: {keywords}")
    
    # Step 2: Search TikTok for each keyword
    all_tiktok_results = []
    seen_links = set()
    
    # Search for original hashtag format
    original_query = f"#{company_name.replace(' ', '')}"
    print(f"[INFO] Searching for original query: {original_query}")
    original_results = search_tiktok(original_query, max_results=20)
    for result in original_results:
        link = result.get("link", "")
        if link and link not in seen_links:
            seen_links.add(link)
            all_tiktok_results.append(result)
    
    # Search for each generated keyword
    for keyword in keywords:
        print(f"[INFO] Searching TikTok for keyword: {keyword}")
        keyword_results = search_tiktok(keyword, max_results=20)
        for result in keyword_results:
            link = result.get("link", "")
            if link and link not in seen_links:
                seen_links.add(link)
                all_tiktok_results.append(result)
    
    print(f"[INFO] Found {len(all_tiktok_results)} unique TikTok videos")
    
    # Step 3: Extract transcripts for all videos
    video_urls = [result.get("link") for result in all_tiktok_results if result.get("link")]
    print(f"[INFO] Extracting transcripts for {len(video_urls)} videos")
    
    transcripts_data = extract_tiktok_transcripts(video_urls)
    
    # Step 4: Analyze relevance and rating for each video
    relevant_results = []
    
    for i, tiktok_result in enumerate(all_tiktok_results):
        video_url = tiktok_result.get("link", "")
        if not video_url:
            continue
            
        # Find corresponding transcript
        transcript_info = None
        for url, description, transcript in transcripts_data:
            if url == video_url:
                transcript_info = {"description": description, "transcript": transcript}
                break
        
        if not transcript_info:
            print(f"[WARNING] No transcript found for {video_url}")
            continue
        
        # Analyze relevance and rating
        analysis_result = analyze_video_relevance(
            company_name, 
            business_description, 
            tiktok_result.get("snippet", ""),
            transcript_info["description"],
            transcript_info["transcript"]
        )
        
        if analysis_result["is_relevant"]:
            # Create result in the specified format
            result_entry = create_result_entry(
                tiktok_result,
                transcript_info,
                analysis_result,
                company_name
            )
            relevant_results.append(result_entry)
    
    print(f"[INFO] Found {len(relevant_results)} relevant TikTok results")
    return relevant_results


def generate_tiktok_keywords(company_name: str, business_description: str) -> List[str]:
    """
    Generate TikTok search keywords based on company name and business description.
    """
    try:
        # Get online search results
        search_query = f"{company_name} {business_description} tiktok"
        results_fed_tiktok = search_search1api(search_query, 30)
        
        if not results_fed_tiktok:
            raise ValueError("No results returned from Search1API")

        # Create formatted list of search result snippets
        top_snippets = results_fed_tiktok[:29]
        combined_text = "\n".join(f"- {result}" for result in top_snippets)

        # Formulate DeepSeek prompt
        prompt = (
            f"You are an expert in social media discovery.\n\n"
            f"Based on the following information about the company '{company_name}' "
            f"with business description: '{business_description}', "
            f"and these Google search results, give me a list of **5 short keywords or phrases only** "
            f"that can be used to search TikTok for related videos. "
            f"Do not write any full sentences or descriptions—just output the keywords in list format.\n\n"
            f"Search results:\n{combined_text}\n\n"
            f"Focus on TikTok trends, product names, and brand-related hashtags or slang. "
            f"Ensure that all the phrases start with {company_name}"
        )

        # Call DeepSeek (via call_gemini_api which now uses DeepSeek)
        response = call_gemini_api(prompt)

        # Parse and clean response
        lines = response.strip().splitlines()
        keywords = []

        for line in lines:
            clean = line.strip().lstrip("-*1234567890. ").strip()
            if clean:
                if ',' in clean:
                    keywords.extend([kw.strip() for kw in clean.split(',')])
                else:
                    keywords.append(clean)

        return keywords[:5]

    except Exception as e:
        print(f"[ERROR] generate_tiktok_keywords failed: {e}")
        return [f"#{company_name.replace(' ', '')}"]


def search_tiktok(query: str, max_results: int = 20) -> List[Dict[str, Any]]:
    """
    Search TikTok for the given query using Apify's apidojo/tiktok-scraper.
    """
    try:
        apify_token = os.getenv("APIFY_API")
        if not apify_token:
            print("[ERROR] APIFY_API not found in environment variables.")
            return []

        client = ApifyClient(apify_token)

        run_input = {
            "keywords": [query],
            "maxItems": max_results
        }

        print(f"[INFO] Starting TikTok search for query: {query}")
        run = client.actor("apidojo/tiktok-scraper").call(run_input=run_input)

        dataset = client.dataset(run["defaultDatasetId"])
        items = list(dataset.iterate_items())

        formatted_results = []
        for item in items:
            formatted_results.append({
                "link": item.get("postPage", ""),
                "snippet": item.get("title", "")[:200],
                "source": "tiktok",
                "username": item.get("author", {}).get("uniqueId", ""),
                "relative_date": item.get("createTime", ""),
                "view_count": item.get("stats", {}).get("playCount", 0),
                "like_count": item.get("stats", {}).get("diggCount", 0)
            })

        print(f"[INFO] Found {len(formatted_results)} TikTok results for query: {query}")
        return formatted_results

    except Exception as e:
        print(f"[ERROR] TikTok search error for query '{query}': {e}")
        return []


def extract_tiktok_transcripts(urls: List[str]) -> List[tuple]:
    """
    Extract transcripts from TikTok videos using Apify actor.
    """
    try:
        token = os.getenv("APIFY_API")
        if not token:
            raise RuntimeError("APIFY_API not set in environment")

        client = ApifyClient(token)
        actor_id = "emQXBCL3xePZYgJyn"  # transcript-extractor actor

        run_input = {"videos": urls}

        print(f"[INFO] Starting transcript extraction for {len(urls)} videos...")
        run = client.actor(actor_id).call(run_input=run_input)

        dataset = client.dataset(run["defaultDatasetId"])

        results = []
        for item in dataset.iterate_items():
            url = item.get("url")
            description = item.get("description") or item.get("text") or ""
            if item.get("transcript", ""):
                transcript = item.get("transcript", "").strip()
            else:
                transcript = "No Transcript"
            results.append((url, description, transcript))

        print(f"[INFO] Extracted {len(results)} transcripts.")
        return results

    except Exception as e:
        print(f"[ERROR] Transcript extraction failed: {e}")
        return []


def analyze_video_relevance(company_name: str, business_description: str, 
                          snippet: str, description: str, transcript: str) -> Dict[str, Any]:
    """
    Analyze video relevance and rating using DeepSeek.
    """
    try:
        prompt = f"""
        You are an expert content analyst. Analyze the following TikTok video content for relevance to a business.

        Company Name: {company_name}
        Business Description: {business_description}

        Video Content:
        - Snippet: {snippet}
        - Description: {description}
        - Transcript: {transcript}

        Please analyze this content and provide:
        1. Is this video relevant to the business? (yes/no)
        2. Rate the relevance from 1-5 (1=not relevant, 5=highly relevant)
        3. Determine sentiment (positive/negative/neutral)
        4. Brief explanation of why it's relevant or not

        Respond in this exact format:
        RELEVANT: yes/no
        RATING: 1-5
        SENTIMENT: positive/negative/neutral
        EXPLANATION: brief explanation
        """

        response = call_gemini_api(prompt)
        
        # Parse response
        lines = response.strip().split('\n')
        analysis = {
            "is_relevant": False,
            "rating": 1,
            "sentiment": "neutral",
            "explanation": ""
        }
        
        for line in lines:
            if line.startswith("RELEVANT:"):
                analysis["is_relevant"] = "yes" in line.lower()
            elif line.startswith("RATING:"):
                try:
                    rating = int(line.split(":")[1].strip())
                    analysis["rating"] = max(1, min(5, rating))
                except:
                    pass
            elif line.startswith("SENTIMENT:"):
                sentiment = line.split(":")[1].strip().lower()
                if sentiment in ["positive", "negative", "neutral"]:
                    analysis["sentiment"] = sentiment
            elif line.startswith("EXPLANATION:"):
                analysis["explanation"] = line.split(":")[1].strip()

        return analysis

    except Exception as e:
        print(f"[ERROR] Video analysis failed: {e}")
        return {
            "is_relevant": False,
            "rating": 1,
            "sentiment": "neutral",
            "explanation": "Analysis failed"
        }


def create_result_entry(tiktok_result: Dict[str, Any], transcript_info: Dict[str, str], 
                       analysis_result: Dict[str, Any], company_name: str) -> Dict[str, Any]:
    """
    Create a result entry in the specified format.
    """
    current_time = datetime.now(timezone.utc)
    
    return {
        "_id": str(uuid.uuid4()),
        "id_review": str(uuid.uuid4()),
        "caption": tiktok_result.get("snippet", ""),
        "relative_date": tiktok_result.get("relative_date", ""),
        "retrieval_date": current_time.isoformat(),
        "rating": analysis_result["rating"],
        "username": tiktok_result.get("username", ""),
        "n_review_user": 0,
        "n_photo_user": 0,
        "url_user": "",
        "business_id": str(uuid.uuid4()),
        "business_name": company_name,
        "business_slug": company_name.lower().replace(" ", "-"),
        "business_url": "",
        "scraped_at": current_time.isoformat(),
        "review_url": tiktok_result.get("link", ""),
        "source": "TikTok",
        "sentiment": analysis_result["sentiment"],
        "quotation_amount": 0,
        "status": "active",
        "transcript": transcript_info.get("transcript", ""),
        "description": transcript_info.get("description", ""),
        "explanation": analysis_result.get("explanation", ""),
        "view_count": tiktok_result.get("view_count", 0),
        "like_count": tiktok_result.get("like_count", 0)
    }


# Example usage
if __name__ == "__main__":
    # Example usage
    company_name = "Republic Bricks"
    business_description = get_business_description_from_url("https://republicbricks.com/en-au", company_name)
    
    results = analyze_tiktok_content_for_business(company_name, business_description)
    
    print(f"\nFound {len(results)} relevant TikTok results:")
    for result in results:
        print(f"- {result['username']}: {result['caption'][:100]}... (Rating: {result['rating']}, Sentiment: {result['sentiment']})") 