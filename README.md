
# Transit-Accessible Activity Recommendation Agent

A Discord bot that recommends activities near a given location that are accessible by public transit. The bot leverages Mistral AI for natural language processing, OpenStreetMap APIs for location and transit data, and OpenWeatherMap for current weather conditions.

---

## Features

✅ **Smart Activity Recommendations** – Get suggestions for activities based on your location  
🚆 **Public Transit Accessibility** – Ensures recommendations are reachable via transit  
🌦 **Weather-Aware** – Adjusts recommendations based on current weather and season  
🤖 **Natural Language Understanding** – Ask for suggestions in plain English  
⌨ **Command-Based Interaction** – Use `!activities` for structured queries  
💰 **100% Free & Open-Source** – No need for Google Maps or paid APIs  

---

## Demo Video


## Setup Instructions

### Prerequisites

Ensure you have the following before installation:

- **Python 3.8+**
- **Discord Bot Token** (from [Discord Developer Portal](https://discord.com/developers/applications))
- **Mistral AI API Key** (from [Mistral AI Platform](https://mistral.ai/))
- **OpenRouteService API Key** (free from [OpenRouteService](https://openrouteservice.org/))
- **OpenWeatherMap API Key** (free tier from [OpenWeatherMap](https://openweathermap.org/))

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-repo-name.git
   cd your-repo-name
   
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt

3. **Setup API Keys:**
- Create a .env file with your API keys (use .env.example as a template)

4. **Run the bot:**
   ```bash
   python bot.py


### Discord Bot Setup

#### 1. Create Discord Bot  
- Go to the [Discord Developer Portal](https://discord.com/developers/applications)  
- Create a new bot and **enable "Message Content Intent"** in the **Bot** section  

#### 2. Add Bot to Your Server  
- Use the **OAuth2 URL generator** and select the following scopes:  
  - `bot`  
  - `applications.commands`  

#### 3. Required Permissions  
Give the bot permissions:  
- **Read Messages/View Channels**  
- **Send Messages**  
- **Use External Emojis**  
- **Add Reactions**  

---

## Usage  

### Natural Language Queries   
Just ask the bot for activity recommendations in a natural conversational way:

> "What can I do in Seattle?"

> "Recommend activities near Chicago"

> "What should I explore in Boston?"

### Commands  
- `!activities [location]` – Get activity recommendations for a specific location  
  - Example: `!activities New York City`  
- `!help_transit` – show detailed help information  

---

## Technology Stack  

| Component | Purpose |  
|-----------|---------|  
| **Discord.py** | Bot framework for Discord integration |  
| **Mistral AI** | Large language model for generating recommendations |  
| **OpenStreetMap (OSM)** | Location data & transit accessibility |  
| **OpenRouteService** | Public transit routing information |  
| **OpenWeatherMap API** | Real time weather data |  
| **GeoPy** | Geocoding & reverse geocoding library|  
| **Nominatim API** | Geocoding (location to coordinates)|  
| **Overpass API** | Finding points of interest|  


---

## Advantages of the Open-Source Approach 

- **Completely Free** – No billing setup or credit card required  
- **No API Quotas** – The OpenStreetMap ecosystem doesn't require API keys for basic usage
- **Global Coverage** – Often better coverage in regions outside the US 
- **Community-Maintained Data** – Frequently updated by local contributors 

---

## Limitations  

- Transit routing information may be limited in some regions
- API response times may be slower than commercial alternatives
- Weather data might not be available for all locations

---

## License  

This project is open-source and available under the **MIT License**.  
