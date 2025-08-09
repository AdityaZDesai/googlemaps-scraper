# DeepSeek API Migration Guide

## Overview
This project has been migrated from Google Gemini API to DeepSeek API to resolve quota issues and improve reliability.

## What Changed

### Files Modified
- `deepseek_api.py` - New DeepSeek API integration module
- `search_terms.py` - Updated to use DeepSeek API
- `reddit_scraper.py` - Updated to use DeepSeek API  
- `internet_scraper.py` - Updated to use DeepSeek API
- `youtube_scraper.py` - Updated to use DeepSeek API
- `tiktok_analyzer.py` - Updated comments (uses DeepSeek via search_terms)
- `start_app.py` - Updated environment variable checks
- `requirements.txt` - Removed google-generativeai dependency

### Environment Variables
- **Old:** `GOOGLE_API_KEY`
- **New:** `DEEPSEEK_API_KEY`

## Setup Instructions

### 1. Get DeepSeek API Key
1. Go to [DeepSeek Platform](https://platform.deepseek.com/)
2. Sign up or log in to your account
3. Navigate to API Keys section
4. Create a new API key
5. Copy the API key (starts with `sk-`)

### 2. Update Environment Variables
Create or update your `.env` file:

```bash
# DeepSeek API (replaces GOOGLE_API_KEY)
DEEPSEEK_API_KEY=sk-your-deepseek-api-key-here

# Other existing keys (unchanged)
SEARCH1_API_KEY=your-search1-api-key
APIFY_API=your-apify-api-key
```

### 3. Install Dependencies
The project no longer requires `google-generativeai`:

```bash
pip install -r requirements.txt
```

### 4. Test the Integration
Run the startup script to verify everything is working:

```bash
python start_app.py
```

## API Differences

### DeepSeek vs Gemini
- **Model:** `deepseek-chat` (replaces `gemini-1.5-flash-8b`)
- **API Endpoint:** `https://api.deepseek.com/v1/chat/completions`
- **Rate Limits:** More generous than Gemini's free tier
- **Response Format:** OpenAI-compatible format

### Backward Compatibility
The migration maintains backward compatibility:
- `call_gemini_api()` function still exists but now calls DeepSeek
- All existing code continues to work without changes
- Same response format and behavior

## Testing

### Test DeepSeek API Directly
```bash
python deepseek_api.py
```

### Test Search Terms Generation
```bash
python search_terms.py
```

### Test Complete Scraping
```bash
python simple_test_and_save.py
```

## Troubleshooting

### Common Issues

1. **API Key Error**
   ```
   ERROR: DEEPSEEK_API_KEY not found in environment
   ```
   **Solution:** Add `DEEPSEEK_API_KEY` to your `.env` file

2. **Import Error**
   ```
   ModuleNotFoundError: No module named 'deepseek_api'
   ```
   **Solution:** Make sure `deepseek_api.py` is in the project root

3. **API Rate Limits**
   ```
   Error: DeepSeek API returned status code 429
   ```
   **Solution:** Wait and retry, or check your DeepSeek quota

### Debug Mode
Enable debug logging by setting environment variable:
```bash
export DEBUG=true
```

## Benefits of Migration

1. **Higher Rate Limits:** DeepSeek offers more generous API quotas
2. **Better Reliability:** Fewer quota exceeded errors
3. **Cost Effective:** Competitive pricing compared to other providers
4. **OpenAI Compatibility:** Standard API format for easier integration
5. **Maintained Functionality:** All existing features work the same way

## Support

If you encounter issues:
1. Check the troubleshooting section above
2. Verify your API key is correct
3. Check DeepSeek platform for any service announcements
4. Review the error logs for specific error messages

## Migration Complete ✅

The migration from Gemini to DeepSeek API is now complete. All functionality has been preserved while improving reliability and reducing quota limitations.
