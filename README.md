Transit-Accessible Activity Recommendation Bot
A Discord bot that recommends activities near a given location that are accessible by public transit. The bot leverages Mistral AI for natural language processing, OpenStreetMap APIs for location and transit data, and OpenWeatherMap for current weather conditions.
Features

🗺️ Recommends activities based on user's location
🚆 Ensures recommendations are accessible by public transit
🌦️ Considers current weather and season
🤖 Natural language interface (ask in plain English)
⌨️ Command-based interface (!activities)
💰 Uses FREE APIs (no Google Maps required!)

Setup Instructions
Prerequisites

Python 3.8+
Discord Bot Token (from Discord Developer Portal)
Mistral AI API Key (from Mistral AI Platform)
OpenRouteService API Key (free from OpenRouteService)
OpenWeatherMap API Key (free tier from OpenWeatherMap)

Installation

Clone this repository
Install dependencies:
Copypip install -r requirements.txt

Create a .env file with your API keys (use .env.example as a template)
Run the bot:
Copypython bot.py


Discord Setup

Create a bot on the Discord Developer Portal
Enable "Message Content Intent" in the Bot section
Add the bot to your server using the OAuth2 URL generator with the following scopes:

bot
applications.commands


Give the bot permissions:

Read Messages/View Channels
Send Messages
Use External Emojis
Add Reactions



Usage
Natural Language
Just ask the bot for recommendations in a natural way:

"What can I do in Seattle?"
"Recommend activities near Chicago"
"What should I explore in Boston?"

Commands

!activities [location] - Get activity recommendations for a specific location

Example: !activities New York City


!help_transit - Show detailed help information

Technology Stack

Discord.py: Bot framework for Discord integration
Mistral AI: Large language model for generating recommendations
OpenStreetMap:

Nominatim API: Geocoding (location to coordinates)
Overpass API: Finding points of interest


OpenRouteService: Public transit routing information
OpenWeatherMap API: Current weather data
GeoPy: Geocoding and reverse geocoding library

Advantages of the Open-Source Approach

Completely free: No billing setup or credit card required
No API quotas: The OpenStreetMap ecosystem doesn't require API keys for basic usage
Global coverage: Often better coverage in regions outside the US
Community-maintained data: Frequently updated by local contributors

Limitations

Transit routing information may be limited in some regions
API response times may be slower than commercial alternatives
Weather data might not be available for all locations