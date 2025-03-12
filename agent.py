import os
import json
import requests
from mistralai import Mistral
import discord
from geopy.geocoders import Nominatim
from datetime import datetime

MISTRAL_MODEL = "mistral-large-latest"
SYSTEM_PROMPT = """You are TerraBot, a helpful assistant that recommends activities accessible by public transit.
When recommending activities:
1. Consider the user's location
2. Provide 3-5 activity suggestions
3. Include information about public transit options to reach each activity
4. Consider current weather and season
5. Format your response in a clear, organized way with emoji

If asked who you are or what your name is, respond that your name is TerraBot, a Discord bot that helps users find activities accessible by public transit.

When greeted, ask the user what type of activities they're looking for and where they're looking for such activities.

If asked how to use you, remind the user that they can try the "!helpme" option along with other suggestions.

Provide information on the weather and explain why that affects your recommendations.

Only respond with recommendations based on the information provided. Keep responses concise and practical."""


class ConversationManager:
    def __init__(self):
        # Store conversations by user_id -> list of message tuples (role, content)
        self.conversations = {}
        self.max_history = 10  # Maximum number of messages to keep per user

    def add_message(self, user_id, role, content):
        """Add a message to the user's conversation history."""
        user_id = str(user_id)

        if user_id not in self.conversations:
            self.conversations[user_id] = []

        self.conversations[user_id].append({"role": role, "content": content})

        # Trim history if it exceeds max length
        if len(self.conversations[user_id]) > self.max_history:
            self.conversations[user_id] = self.conversations[user_id][
                -self.max_history :
            ]

    def get_history(self, user_id):
        """Get the conversation history for a user."""
        user_id = str(user_id)
        return self.conversations.get(user_id, [])

    def clear_history(self, user_id):
        """Clear the conversation history for a user."""
        user_id = str(user_id)
        if user_id in self.conversations:
            self.conversations[user_id] = []


class ActivityRecommendationAgent:
    def __init__(self):
        self.mistral_api_key = os.getenv("MISTRAL_API_KEY")
        self.openroute_api_key = os.getenv("OPENROUTE_API_KEY")
        self.openweather_api_key = os.getenv("OPENWEATHER_API_KEY")

        self.mistral_client = Mistral(api_key=self.mistral_api_key)
        self.geolocator = Nominatim(user_agent="discord-activity-bot")
        self.conversation_manager = ConversationManager()

        # Categories mapping for filtering places
        self.category_mapping = {
            # Food and drink related
            "food": ["restaurant", "cafe", "bar", "pub", "fast_food", "food_court"],
            "restaurant": ["restaurant"],
            "cafe": ["cafe"],
            "dining": ["restaurant", "cafe", "bar", "pub"],
            "eat": ["restaurant", "cafe", "fast_food"],
            # Tourism related
            "tourist": [
                "attraction",
                "museum",
                "gallery",
                "viewpoint",
                "artwork",
                "theme_park",
            ],
            "attraction": ["attraction", "theme_park", "artwork"],
            "museum": ["museum"],
            "gallery": ["gallery", "museum", "artwork"],
            "culture": ["museum", "gallery", "theatre", "arts_centre"],
            "sightseeing": ["attraction", "viewpoint", "monument"],
            # Accommodation
            "hotel": ["hotel", "hostel", "guest_house"],
            "accommodation": ["hotel", "hostel", "guest_house", "apartment"],
            "stay": ["hotel", "hostel", "guest_house", "apartment"],
            # Nature and recreation
            "park": ["park"],
            "nature": ["park", "nature_reserve", "national_park"],
            "outdoor": ["park", "viewpoint", "nature_reserve"],
            # Shopping
            "shop": ["mall", "department_store", "supermarket"],
            "mall": ["mall"],
            "shopping": ["mall", "department_store", "marketplace"],
            # Entertainment
            "entertainment": ["cinema", "theatre", "nightclub", "casino"],
            "cinema": ["cinema"],
            "theatre": ["theatre"],
            "movie": ["cinema"],
            "show": ["theatre", "arts_centre"],
        }

    async def get_coordinates(self, location_name):
        """Convert a location name to coordinates using OpenStreetMap/Nominatim."""
        try:
            location = self.geolocator.geocode(location_name)
            if location:
                return {
                    "lat": location.latitude,
                    "lng": location.longitude,
                    "formatted_address": location.address,
                }
            return None
        except Exception as e:
            print(f"Error geocoding location: {e}")
            return None

    async def get_weather(self, lat, lng):
        """Get current weather for the coordinates."""
        try:
            url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lng}&units=metric&appid={self.openweather_api_key}"
            response = requests.get(url)
            data = response.json()

            if response.status_code == 200:
                return {
                    "description": data["weather"][0]["description"],
                    "temperature": data["main"]["temp"],
                    "feels_like": data["main"]["feels_like"],
                    "humidity": data["main"]["humidity"],
                }
            return None
        except Exception as e:
            print(f"Error getting weather: {e}")
            return None

    async def get_nearby_places(self, lat, lng, radius=5000, place_type=None):
        """
        Get nearby places from OpenStreetMap using Overpass API.
        Optional place_type parameter to filter by specific types of places.
        """
        try:
            overpass_url = "https://overpass-api.de/api/interpreter"

            # Build query - either with filters or with all types
            if place_type:
                # Get the OSM tags that correspond to the requested place type
                query_parts = []

                # Check if we need to filter by tourism
                tourism_types = []
                if "attraction" in place_type:
                    tourism_types.append("attraction")
                if "museum" in place_type:
                    tourism_types.append("museum")
                if "gallery" in place_type or "artwork" in place_type:
                    tourism_types.append("gallery")
                if "hotel" in place_type or "hostel" in place_type:
                    tourism_types.extend(["hotel", "hostel", "guest_house"])

                # Add tourism queries
                if tourism_types:
                    for t_type in tourism_types:
                        query_parts.append(
                            f'node["tourism"="{t_type}"](around:{radius},{lat},{lng});'
                        )
                        query_parts.append(
                            f'way["tourism"="{t_type}"](around:{radius},{lat},{lng});'
                        )
                        query_parts.append(
                            f'relation["tourism"="{t_type}"](around:{radius},{lat},{lng});'
                        )

                # Check if we need to filter by amenity
                amenity_types = []
                if (
                    "restaurant" in place_type
                    or "food" in place_type
                    or "eat" in place_type
                    or "dining" in place_type
                ):
                    amenity_types.append("restaurant")
                if "cafe" in place_type or "food" in place_type:
                    amenity_types.append("cafe")
                if "bar" in place_type or "pub" in place_type or "dining" in place_type:
                    amenity_types.extend(["bar", "pub"])
                if "fast_food" in place_type or "food" in place_type:
                    amenity_types.append("fast_food")
                if (
                    "cinema" in place_type
                    or "movie" in place_type
                    or "entertainment" in place_type
                ):
                    amenity_types.append("cinema")
                if (
                    "theatre" in place_type
                    or "show" in place_type
                    or "entertainment" in place_type
                ):
                    amenity_types.append("theatre")
                if "arts_centre" in place_type or "culture" in place_type:
                    amenity_types.append("arts_centre")

                # Add amenity queries
                if amenity_types:
                    for a_type in amenity_types:
                        query_parts.append(
                            f'node["amenity"="{a_type}"](around:{radius},{lat},{lng});'
                        )
                        query_parts.append(
                            f'way["amenity"="{a_type}"](around:{radius},{lat},{lng});'
                        )

                # Check if we need to filter by leisure
                leisure_types = []
                if (
                    "park" in place_type
                    or "nature" in place_type
                    or "outdoor" in place_type
                ):
                    leisure_types.append("park")

                # Add leisure queries
                if leisure_types:
                    for l_type in leisure_types:
                        query_parts.append(
                            f'node["leisure"="{l_type}"](around:{radius},{lat},{lng});'
                        )
                        query_parts.append(
                            f'way["leisure"="{l_type}"](around:{radius},{lat},{lng});'
                        )
                        query_parts.append(
                            f'relation["leisure"="{l_type}"](around:{radius},{lat},{lng});'
                        )

                # Check if we need to filter by shop
                shop_types = []
                if (
                    "mall" in place_type
                    or "shopping" in place_type
                    or "shop" in place_type
                ):
                    shop_types.append("mall")
                if "department_store" in place_type or "shopping" in place_type:
                    shop_types.append("department_store")

                # Add shop queries
                if shop_types:
                    for s_type in shop_types:
                        query_parts.append(
                            f'node["shop"="{s_type}"](around:{radius},{lat},{lng});'
                        )
                        query_parts.append(
                            f'way["shop"="{s_type}"](around:{radius},{lat},{lng});'
                        )

                # If no specific types are matched, use the default query
                if not query_parts:
                    query = f"""
                    [out:json];
                    (
                      node["tourism"](around:{radius},{lat},{lng});
                      node["leisure"="park"](around:{radius},{lat},{lng});
                      node["amenity"="restaurant"](around:{radius},{lat},{lng});
                      node["amenity"="cafe"](around:{radius},{lat},{lng});
                      node["amenity"="theatre"](around:{radius},{lat},{lng});
                      node["amenity"="cinema"](around:{radius},{lat},{lng});
                      node["amenity"="arts_centre"](around:{radius},{lat},{lng});
                      node["shop"="mall"](around:{radius},{lat},{lng});
                      way["tourism"](around:{radius},{lat},{lng});
                      way["leisure"="park"](around:{radius},{lat},{lng});
                      relation["tourism"](around:{radius},{lat},{lng});
                      relation["leisure"="park"](around:{radius},{lat},{lng});
                    );
                    out center;
                    """
                else:
                    query = f"""
                    [out:json];
                    (
                      {' '.join(query_parts)}
                    );
                    out center;
                    """
            else:
                # Default query with all types
                query = f"""
                [out:json];
                (
                  node["tourism"](around:{radius},{lat},{lng});
                  node["leisure"="park"](around:{radius},{lat},{lng});
                  node["amenity"="restaurant"](around:{radius},{lat},{lng});
                  node["amenity"="cafe"](around:{radius},{lat},{lng});
                  node["amenity"="theatre"](around:{radius},{lat},{lng});
                  node["amenity"="cinema"](around:{radius},{lat},{lng});
                  node["amenity"="arts_centre"](around:{radius},{lat},{lng});
                  node["shop"="mall"](around:{radius},{lat},{lng});
                  way["tourism"](around:{radius},{lat},{lng});
                  way["leisure"="park"](around:{radius},{lat},{lng});
                  relation["tourism"](around:{radius},{lat},{lng});
                  relation["leisure"="park"](around:{radius},{lat},{lng});
                );
                out center;
                """

            response = requests.get(overpass_url, params={"data": query})

            if response.status_code == 200:
                data = response.json()
                places = []

                for element in data.get("elements", [])[
                    :15
                ]:  # Increase limit to get more candidates
                    if element["type"] == "node":
                        place_lat = element["lat"]
                        place_lng = element["lon"]
                    else:  # way or relation
                        if "center" in element:
                            place_lat = element["center"]["lat"]
                            place_lng = element["center"]["lon"]
                        else:
                            continue

                    tags = element.get("tags", {})
                    name = tags.get("name", "Unnamed location")

                    if name == "Unnamed location":
                        continue

                    place_type = []
                    if "tourism" in tags:
                        place_type.append(tags["tourism"])
                    if "leisure" in tags:
                        place_type.append(tags["leisure"])
                    if "amenity" in tags:
                        place_type.append(tags["amenity"])
                    if "shop" in tags:
                        place_type.append(tags["shop"])

                    places.append(
                        {
                            "name": name,
                            "lat": place_lat,
                            "lng": place_lng,
                            "types": place_type,
                            "address": tags.get("addr:street", "")
                            + " "
                            + tags.get("addr:housenumber", ""),
                        }
                    )

                return places
            return []
        except Exception as e:
            print(f"Error getting nearby places: {e}")
            return []

    async def get_transit_info(self, origin_lat, origin_lng, dest_lat, dest_lng):
        """Get transit directions using OpenRouteService."""
        try:
            # OpenRouteService public transportation API
            url = "https://api.openrouteservice.org/v2/directions/public-transport"
            headers = {
                "Accept": "application/json, application/geo+json, application/gpx+xml",
                "Authorization": self.openroute_api_key,
                "Content-Type": "application/json",
            }
            body = {
                "coordinates": [[origin_lng, origin_lat], [dest_lng, dest_lat]],
                "departure": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            }

            response = requests.post(url, json=body, headers=headers)

            if response.status_code != 200:
                overpass_url = "https://overpass-api.de/api/interpreter"
                query = f"""
                [out:json];
                (
                  node["public_transport"="stop_position"](around:1000,{dest_lat},{dest_lng});
                  node["highway"="bus_stop"](around:1000,{dest_lat},{dest_lng});
                  node["railway"="station"](around:1000,{dest_lat},{dest_lng});
                  node["railway"="tram_stop"](around:1000,{dest_lat},{dest_lng});
                );
                out;
                """

                transit_response = requests.get(overpass_url, params={"data": query})
                if transit_response.status_code == 200:
                    transit_data = transit_response.json()
                    transit_stops = transit_data.get("elements", [])

                    if transit_stops:
                        closest_stop = min(
                            transit_stops,
                            key=lambda x: self.haversine_distance(
                                dest_lat, dest_lng, x["lat"], x["lon"]
                            ),
                        )

                        stop_name = closest_stop.get("tags", {}).get(
                            "name", "Unknown stop"
                        )
                        stop_type = []
                        if "public_transport" in closest_stop.get("tags", {}):
                            stop_type.append(closest_stop["tags"]["public_transport"])
                        if "highway" in closest_stop.get("tags", {}):
                            stop_type.append(closest_stop["tags"]["highway"])
                        if "railway" in closest_stop.get("tags", {}):
                            stop_type.append(closest_stop["tags"]["railway"])

                        return {
                            "available": True,
                            "transit_type": ", ".join(stop_type),
                            "stop_name": stop_name,
                            "distance_to_stop": f"{int(self.haversine_distance(dest_lat, dest_lng, closest_stop['lat'], closest_stop['lon']) * 1000)}m",
                            "note": "Transit information is approximated based on nearby stops.",
                        }

                return {"available": False}

            # Process OpenRouteService response
            data = response.json()
            if "features" in data and len(data["features"]) > 0:
                route = data["features"][0]
                properties = route.get("properties", {})
                segments = properties.get("segments", [{}])[0]
                steps = segments.get("steps", [])

                transit_steps = [
                    step for step in steps if step.get("type") == "public_transport"
                ]

                if transit_steps:
                    return {
                        "available": True,
                        "duration": properties.get("summary", {}).get("duration", 0)
                        / 60,
                        "transit_options": len(transit_steps),
                        "transit_types": [
                            step.get("mode", "transit") for step in transit_steps
                        ],
                    }

            return {"available": False}
        except Exception as e:
            print(f"Error getting transit info: {e}")
            return {"available": False}

    def haversine_distance(self, lat1, lon1, lat2, lon2):
        """Calculate the great circle distance between two points in kilometers."""
        from math import radians, cos, sin, asin, sqrt

        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * asin(sqrt(a))
        r = 6371

        return c * r

    def extract_place_type(self, content):
        """Extract place type from message content"""
        content_lower = content.lower()

        # Check for bot identification question
        if (
            "who are you" in content_lower
            or "what is your name" in content_lower
            or "what's your name" in content_lower
        ):
            return None, True

        # Search for place type keywords
        for category, tags in self.category_mapping.items():
            if category in content_lower:
                return category, False

        # Look for more specific phrases
        if "places to eat" in content_lower or "where to eat" in content_lower:
            return "food", False
        if "tourist spots" in content_lower or "tourist destinations" in content_lower:
            return "tourist", False
        if "where to stay" in content_lower or "places to stay" in content_lower:
            return "accommodation", False

        return None, False  # No specific place type found

    async def run(self, message: discord.Message):
        """Process the message and return activity recommendations."""
        content = message.content
        user_id = message.author.id

        # Store this message in the conversation history
        self.conversation_manager.add_message(user_id, "user", content)

        # Check if it's a bot identification question
        place_type, is_name_question = self.extract_place_type(content)

        if is_name_question:
            response = "My name is TerraBot! I'm a Discord bot that helps you find activities accessible by public transit. How can I assist you today?"
            self.conversation_manager.add_message(user_id, "assistant", response)
            return response

        location_keywords = ["in ", "near ", "around "]
        location = None

        for keyword in location_keywords:
            if keyword in content.lower():
                parts = content.lower().split(keyword, 1)
                if len(parts) > 1:
                    raw_location = parts[1].strip()

                    location = raw_location

                    cutoff_phrases = [
                        " that",
                        " which",
                        " using",
                        " with",
                        " by",
                        " via",
                        " on",
                        " through",
                        " where",
                        " when",
                        " for",
                        " and",
                    ]

                    for phrase in cutoff_phrases:
                        if phrase in location:
                            location = location.split(phrase, 1)[0].strip()

                    break

        if not location:
            # Get the conversation history
            conversation_history = self.conversation_manager.get_history(user_id)

            # Prepare messages for Mistral including history
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]

            # Add relevant conversation history (skipping the latest user message which we'll add separately)
            for msg in conversation_history[:-1]:
                messages.append(msg)

            # Add the latest user message
            messages.append({"role": "user", "content": content})

            response = await self.mistral_client.chat.complete_async(
                model=MISTRAL_MODEL,
                messages=messages,
            )

            mistral_response = response.choices[0].message.content
            self.conversation_manager.add_message(
                user_id, "assistant", mistral_response
            )
            return mistral_response

        # Get coordinates for the location
        coords = await self.get_coordinates(location)
        if not coords:
            return f"Sorry, I couldn't find the location '{location}'. Please try a different location."

        weather = await self.get_weather(coords["lat"], coords["lng"])

        # Get nearby places of interest, filtered by place type if specified
        places = await self.get_nearby_places(
            coords["lat"], coords["lng"], place_type=place_type
        )

        # Filter places that are accessible by public transit
        transit_accessible_places = []
        for place in places[:5]:
            place_lat = place["lat"]
            place_lng = place["lng"]

            transit_info = await self.get_transit_info(
                coords["lat"], coords["lng"], place_lat, place_lng
            )

            if transit_info["available"]:
                transit_accessible_places.append(
                    {
                        "name": place["name"],
                        "address": place.get(
                            "address", "Check maps for exact location"
                        ),
                        "types": place.get("types", []),
                        "transit_info": transit_info,
                    }
                )

        current_season = self.get_current_season()
        current_time = datetime.now().strftime("%A, %I:%M %p")

        context = {
            "location": coords["formatted_address"],
            "weather": weather if weather else "Unknown",
            "season": current_season,
            "current_time": current_time,
            "transit_accessible_places": transit_accessible_places,
        }

        # Format a prompt for Mistral
        place_type_text = f" focusing on {place_type} options" if place_type else ""

        user_prompt = f"""
        I need recommendations for activities near {location}{place_type_text} that are accessible by public transit.
        
        Location details:
        - Full address: {context['location']}
        - Current time: {context['current_time']}
        - Season: {context['season']}
        
        Weather information:
        {json.dumps(context['weather'], indent=2) if weather else "Weather information unavailable"}
        
        Places accessible by public transit:
        {json.dumps(context['transit_accessible_places'], indent=2) if transit_accessible_places else "No places with public transit access found"}
        
        Consider the conversation history when making recommendations. The user might have mentioned preferences or constraints in previous messages.
        
        Please provide 3-5 specific recommendations based on this data. If no transit-accessible places were found, suggest popular activities in the area that might have public transit access not listed in the data.
        """

        # Get all conversation history for context
        conversation_history = self.conversation_manager.get_history(user_id)

        # Prepare messages for Mistral including history
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Add relevant conversation history (up to 5 previous messages)
        for msg in conversation_history[-5:-1]:  # Skip the current message
            messages.append(msg)

        # Add the current context as the latest user message
        messages.append({"role": "user", "content": user_prompt})

        try:
            response = await self.mistral_client.chat.complete_async(
                model=MISTRAL_MODEL,
                messages=messages,
            )

            recommendations = response.choices[0].message.content

            # Format the title according to whether we have a specific place type
            if place_type:
                title = f"**{place_type.title()} options near {location} accessible by public transit:**"
            else:
                title = f"**Activities near {location} accessible by public transit:**"

            final_response = f"{title}\n\n{recommendations}"

            if not transit_accessible_places:
                final_response += "\n\n*Note: Transit data may be limited. These are general recommendations based on popular places in the area.*"

            # Store the bot's response in conversation history
            self.conversation_manager.add_message(user_id, "assistant", final_response)

            return final_response
        except Exception as e:
            print(f"Error getting recommendations from Mistral: {e}")
            error_message = f"I had trouble generating recommendations for {location}. Please try again later."
            self.conversation_manager.add_message(user_id, "assistant", error_message)
            return error_message

    def get_current_season(self):
        """Get the current season based on month."""
        month = datetime.now().month
        if month in [12, 1, 2]:
            return "Winter"
        elif month in [3, 4, 5]:
            return "Spring"
        elif month in [6, 7, 8]:
            return "Summer"
        else:
            return "Fall"
