#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Simple runner script for the Google Maps Business Review Scraper
"""

import subprocess
import sys
import os

def main():
    print("Google Maps Business Review Scraper")
    print("=" * 40)
    print()
    
    print("Choose an option:")
    print("1. Run scraper once (default)")
    print("2. Run scraper with scheduling (every 3 hours)")
    print("3. Run scraper with debug mode")
    print("4. Export existing reviews to CSV")
    print("5. Show help")
    
    choice = input("\nEnter your choice (1-5): ").strip()
    
    if choice == "1":
        # Run once
        cmd = [sys.executable, "scraper.py"]
        print("Running scraper once...")
        
    elif choice == "2":
        # Run with scheduling
        cmd = [sys.executable, "scraper.py", "--schedule"]
        print("Starting scheduled scraper (every 3 hours)...")
        print("Press Ctrl+C to stop")
        
    elif choice == "3":
        # Run with debug
        cmd = [sys.executable, "scraper.py", "--debug"]
        print("Running scraper in debug mode...")
        
    elif choice == "4":
        # Export to CSV
        output_file = input("Enter output CSV filename (default: business_reviews.csv): ").strip()
        if not output_file:
            output_file = "business_reviews.csv"
        cmd = [sys.executable, "scraper.py", "--export-csv", output_file]
        print(f"Exporting reviews to {output_file}...")
        
    elif choice == "5":
        # Show help
        cmd = [sys.executable, "scraper.py", "--help"]
        
    else:
        print("Invalid choice. Exiting.")
        return
    
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\nScraper stopped by user.")
    except subprocess.CalledProcessError as e:
        print(f"Error running scraper: {e}")
    except FileNotFoundError:
        print("Error: scraper.py not found. Make sure you're in the correct directory.")

if __name__ == "__main__":
    main() 