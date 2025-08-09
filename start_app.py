#!/usr/bin/env python3
"""
Startup script for the Flask scraping app
"""

import os
import sys
from dotenv import load_dotenv

def check_environment():
    """Check if all required environment variables are set"""
    load_dotenv()
    
    required_vars = [
        'DEEPSEEK_API',
        'SEARCH1API_KEY', 
        'APIFY_API'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set these variables in your .env file")
        return False
    
    print("✅ All required environment variables are set")
    return True

def check_dependencies():
    """Check if all required packages are installed"""
    try:
        import flask
        import flask_cors
        import requests
        # google.generativeai no longer needed - using DeepSeek API
        from apify_client import ApifyClient
        print("✅ All required packages are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing required package: {e}")
        print("Please run: pip install -r requirements.txt")
        return False

def main():
    """Main startup function"""
    print("🚀 Flask Scraping App Startup")
    print("=" * 40)
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    print("\n✅ Environment check passed!")
    print("\nStarting Flask app...")
    print("=" * 40)
    
    # Import and run the Flask app
    try:
        from app import app
        
        port = int(os.environ.get('PORT', 5000))
        debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
        
        print(f"🌐 App will be available at: http://localhost:{port}")
        print(f"🔧 Debug mode: {debug}")
        print("\nPress Ctrl+C to stop the server")
        print("=" * 40)
        
        app.run(host='0.0.0.0', port=port, debug=debug)
        
    except Exception as e:
        print(f"❌ Failed to start Flask app: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 