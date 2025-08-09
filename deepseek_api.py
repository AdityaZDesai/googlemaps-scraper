"""
DeepSeek API integration module to replace Gemini API calls
"""

import os
import requests
import json
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class DeepSeekAPI:
    """
    DeepSeek API client for making API calls
    """
    
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.base_url = "https://api.deepseek.com/v1/chat/completions"
        
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY not found in environment variables")
    
    def generate_content(self, prompt: str, temperature: float = 0.3, max_tokens: int = 4096) -> str:
        """
        Generate content using DeepSeek API
        
        Args:
            prompt (str): The prompt to send to DeepSeek
            temperature (float): Temperature for generation (0.0 to 1.0)
            max_tokens (int): Maximum tokens to generate
            
        Returns:
            str: Generated content from DeepSeek
        """
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }
        
        try:
            print(f"DEBUG: Sending request to DeepSeek API...")
            response = requests.post(self.base_url, headers=headers, json=payload, timeout=60)
            
            if response.status_code != 200:
                print(f"DEBUG: DeepSeek API returned status code: {response.status_code}")
                print(f"DEBUG: Response: {response.text}")
                return f"Error: DeepSeek API returned status code {response.status_code}"
            
            result = response.json()
            
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"]
                print(f"DEBUG: DeepSeek API response received successfully")
                return content
            else:
                print(f"DEBUG: Unexpected response format: {result}")
                return "Error: Unexpected response format from DeepSeek API"
                
        except requests.exceptions.Timeout:
            print(f"DEBUG: DeepSeek API request timed out")
            return "Error: Request timed out"
        except requests.exceptions.RequestException as e:
            print(f"DEBUG: DeepSeek API request failed: {e}")
            return f"Error: Request failed - {str(e)}"
        except json.JSONDecodeError as e:
            print(f"DEBUG: Failed to parse DeepSeek API response: {e}")
            return "Error: Failed to parse API response"
        except Exception as e:
            print(f"DEBUG: Unexpected error with DeepSeek API: {e}")
            return f"Error: Unexpected error - {str(e)}"

# Global instance
_deepseek_client = None

def get_deepseek_client() -> DeepSeekAPI:
    """
    Get or create a global DeepSeek API client instance
    
    Returns:
        DeepSeekAPI: The DeepSeek API client
    """
    global _deepseek_client
    if _deepseek_client is None:
        _deepseek_client = DeepSeekAPI()
    return _deepseek_client

def call_deepseek_api(prompt: str, temperature: float = 0.3, max_tokens: int = 4096) -> str:
    """
    Simple function to call DeepSeek API - compatible with existing call_gemini_api usage
    
    Args:
        prompt (str): The prompt to send to DeepSeek
        temperature (float): Temperature for generation (0.0 to 1.0) 
        max_tokens (int): Maximum tokens to generate
        
    Returns:
        str: Generated content from DeepSeek
    """
    client = get_deepseek_client()
    return client.generate_content(prompt, temperature, max_tokens)

# Legacy function for backward compatibility
def call_gemini_api(prompt: str) -> str:
    """
    Legacy function that now calls DeepSeek API instead of Gemini
    This maintains compatibility with existing code
    
    Args:
        prompt (str): The prompt to send to the API
        
    Returns:
        str: Generated content
    """
    print("DEBUG: Redirecting Gemini API call to DeepSeek API...")
    return call_deepseek_api(prompt)

if __name__ == "__main__":
    # Test the API
    test_prompt = "Hello, please respond with 'DeepSeek API is working correctly!'"
    result = call_deepseek_api(test_prompt)
    print(f"Test result: {result}")
