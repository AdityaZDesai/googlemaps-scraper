from dotenv import load_dotenv
import os
import sys
import requests
import google.generativeai as genai

print("DEBUG: Loading environment variables...")
load_dotenv() 
print("DEBUG: Environment variables loaded")

# Configure the API and create model instance
print("DEBUG: Configuring Gemini API...")
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')
print("DEBUG: Gemini API configured successfully")

def call_gemini_api(prompt: str) -> str:
    """
    Sends `prompt` to Gemini Flash via the Gen AI SDK 
    and returns the generated text.
    """
    print(f"DEBUG: call_gemini_api called with prompt length: {len(prompt)}")
    
    if not os.getenv("GOOGLE_API_KEY"):
        print("DEBUG: ERROR - GOOGLE_API_KEY not found in environment")
        raise RuntimeError("Please set GOOGLE_API_KEY in your environment")

    try:
        print("DEBUG: Sending request to Gemini API...")
        # Generate a single best completion
        response = model.generate_content(prompt)
        print("DEBUG: Gemini API response received successfully")
        return response.text
    except Exception as e:
        print(f"DEBUG: Error calling Gemini API: {e}")
        return "Error generating content"






load_dotenv()
print("DEBUG: Loading SEARCH1_API_KEY from environment...")
SEARCH1_API_KEY = os.getenv("SEARCH1_API_KEY")
print(f"DEBUG: SEARCH1_API_KEY loaded: {'Yes' if SEARCH1_API_KEY else 'No'}")

def scrape_site(url):
    """
    Generates a list of search terms based on the provided company name.
    Parameters:
    - company_name (str): Name of the company
    Returns:
    - list: List of generated search terms
    """
    print(f"DEBUG: scrape_site called with URL: {url}")
    
    if not SEARCH1_API_KEY:
        print("DEBUG: ERROR - SEARCH1_API_KEY not found in environment")
        raise RuntimeError("SEARCH1_API_KEY is not set in your environment")

    print("DEBUG: Making request to Search1 API...")
    response = requests.post(
        'https://api.search1api.com/crawl',
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {SEARCH1_API_KEY}'
        },
        json={
        "url": f"{url}"
    }
    )
    print(f"DEBUG: Search1 API response status code: {response.status_code}")

    if response.status_code == 500:
        print("DEBUG: Search1 API returned 500 error - INVALID_URL")
        return "INVALID_URL"
    # Check if the response is successful
    if response.status_code == 200:
        try:
            print("DEBUG: Parsing JSON response from Search1 API...")
            # Parse the JSON response
            data = response.json()
            print(f"DEBUG: JSON response keys: {list(data.keys())}")
            # Assuming the structure of the response
            if 'results' in data and len(data['results']) > 0:
                print("DEBUG: Found results in response, extracting content...")
                scraped_content = f"{data['results']['title']}{data['results']['content']}"
                print(f"DEBUG: Scraped content length: {len(scraped_content)}")
                return scraped_content
            else:
                print("DEBUG: No results found in the response.")
                return "No results found in the response."
        except ValueError as e:
            print(f"DEBUG: Failed to parse JSON response: {e}")
            return "Failed to parse JSON response."
    else:
        print(f"DEBUG: Request failed with status code: {response.status_code}")
        return f"Request failed with status code: {response.status_code}"


def generate_search_term(company_name, url):
    print(f"DEBUG: generate_search_term called with company: {company_name}, URL: {url}")
    
    print("DEBUG: Starting site scraping...")
    scraped_data = scrape_site(url)
    print(f"DEBUG: Scraped data result: {scraped_data[:100] if len(scraped_data) > 100 else scraped_data}")
    
    if scraped_data == "INVALID_URL":
        print("DEBUG: Returning INVALID_URL")
        return "INVALID_URL"
    if scraped_data == "Request failed with status code: 500":
        print("DEBUG: Returning Request failed with status code: 500")
        return "Request failed with status code: 500"
    if scraped_data == "No results found in the response.":
        print("DEBUG: Returning No results found in the response.")
        return "No results found in the response."
    if scraped_data == "Failed to parse JSON response.":
        print("DEBUG: Returning Failed to parse JSON response.")
        return "Failed to parse JSON response."

    print("DEBUG: Creating prompt for Gemini API...")
    prompt= f"""
    Your are helpful assistant that generates me a the company description for a given company name and their scraped website data.
    Along with this you will also generate me a small two sentence description of the company based on the website data I have provided. 
    Here is the company name: {company_name}
    Here is the website data: {scraped_data}
    Here is the format you should return:
    Description: <description>
    There should be no more than 2 sentences in the description.
    Here is an example of what you should return:
    Input: Facebook, [Scraped Facebook website about data]
    Output:
    Description: Facebook is a social media platform that allows users to connect with friends, family, and the world around them.
    """
    print(f"DEBUG: Prompt created, length: {len(prompt)}")
    
    print("DEBUG: Calling Gemini API...")
    response = call_gemini_api(prompt)
    print(f"DEBUG: Gemini API response: {response}")
    
    # Parse the Gemini response to extract the description
    print("DEBUG: Parsing Gemini response...")
    print(f"DEBUG: Raw response: {repr(response)}")
    
    # Handle different response formats
    if response.startswith("Description: "):
        # Single line format: "Description: <content>"
        description = response.replace("Description: ", "").strip()
        print(f"DEBUG: Extracted description from single line: {description}")
    elif '\n' in response:
        # Multi-line format: look for "Description: " on any line
        lines = response.split('\n')
        print(f"DEBUG: Response split into {len(lines)} lines")
        description = ""
        for line in lines:
            if line.strip().startswith("Description: "):
                description = line.replace("Description: ", "").strip()
                print(f"DEBUG: Found description on line: {description}")
                break
        if not description:
            print("DEBUG: WARNING - No 'Description: ' found in multi-line response")
            description = response.strip()
    else:
        # Fallback: treat entire response as description
        print("DEBUG: WARNING - Unexpected response format, using entire response")
        description = response.strip()
    
    print(f"DEBUG: Final result: {description}")
    return description

if __name__ == "__main__":
    print("DEBUG: Starting main execution...")
    result = generate_search_term("Primal Queen", "https://primalqueen.com/")
    print(f"DEBUG: Final result: {result}")