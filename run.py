#!/usr/bin/env python3
"""
Simple launcher script for the Transit-Accessible Activity Recommendation Bot.
This provides a more user-friendly way to start the bot.
"""

import os
import sys
import subprocess
import time

def check_env_file():
    """Check if .env file exists and has required keys."""
    if not os.path.exists(".env"):
        print("❌ Error: .env file not found!")
        print("   Please create a .env file with your API keys.")
        print("   You can use .env.example as a template.")
        return False
    
    with open(".env", "r") as f:
        content = f.read()
    
    required_keys = [
        "DISCORD_TOKEN",
        "MISTRAL_API_KEY",
        "OPENROUTE_API_KEY",
        "OPENWEATHER_API_KEY"
    ]
    
    missing_keys = []
    for key in required_keys:
        if key not in content:
            missing_keys.append(key)
    
    if missing_keys:
        print("❌ Error: Missing required keys in .env file:")
        for key in missing_keys:
            print(f"   - {key}")
        return False
    
    return True

def check_dependencies():
    """Check if all required packages are installed."""
    try:
        import discord
        import dotenv
        import mistralai
        import requests
        import geopy
        return True
    except ImportError as e:
        print(f"❌ Error: Missing dependency - {str(e)}")
        print("   Please run: pip install -r requirements.txt")
        return False

def main():
    """Main function to run the bot."""
    print("🤖 Transit-Accessible Activity Recommendation Bot Launcher")
    print("--------------------------------------------------------")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Error: Python 3.8 or higher is required.")
        return
    
    # Check dependencies
    print("📋 Checking dependencies...")
    if not check_dependencies():
        return
    print("✅ All dependencies found!")
    
    # Check .env file
    print("📋 Checking environment file...")
    if not check_env_file():
        return
    print("✅ Environment file looks good!")
    
    # Run the bot
    print("🚀 Starting the bot...")
    try:
        subprocess.run([sys.executable, "bot.py"])
    except KeyboardInterrupt:
        print("\n👋 Bot shutdown requested. Goodbye!")
    except Exception as e:
        print(f"❌ Error running the bot: {str(e)}")

if __name__ == "__main__":
    main()