import os
import json
import discord
import logging
from discord.ext import commands
from dotenv import load_dotenv
from agent import ActivityRecommendationAgent

PREFIX = "!"

# Setup logging
logger = logging.getLogger("discord")
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
handler.setFormatter(
    logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s")
)
logger.addHandler(handler)

# Load the environment variables
load_dotenv()

# Create the bot with all intents
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

# Import the Activity Recommendation Agent
agent = ActivityRecommendationAgent()

# Get the token from the environment variables
token = os.getenv("DISCORD_TOKEN")


@bot.event
async def on_ready():
    """Called when the bot successfully connects to Discord."""
    logger.info(f"{bot.user} has connected to Discord!")

    # Set the bot's status/activity
    activity = discord.Activity(
        type=discord.ActivityType.listening, name="for transit recommendations"
    )
    await bot.change_presence(activity=activity)


# Define the path for storing bookmarks
BOOKMARKS_DIR = "bookmarks"
os.makedirs(BOOKMARKS_DIR, exist_ok=True)


def get_bookmark_file(user_id):
    """Get the bookmark file path for a specific user."""
    return os.path.join(BOOKMARKS_DIR, f"{user_id}_bookmarks.json")


def load_bookmarks(user_id):
    """Load a user's bookmarks from file."""
    bookmark_file = get_bookmark_file(user_id)
    if os.path.exists(bookmark_file):
        with open(bookmark_file, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}


def save_bookmarks(user_id, bookmarks):
    """Save a user's bookmarks to file."""
    bookmark_file = get_bookmark_file(user_id)
    with open(bookmark_file, "w") as f:
        json.dump(bookmarks, f, indent=2)


@bot.command(
    name="add", help="Add a location to your bookmarks. Usage: !add <place name>"
)
async def add_bookmark(ctx, *, location=None):
    """Command to add a location to the user's bookmarks."""
    if location is None:
        await ctx.send(
            "Please specify a location to bookmark. Example: `!add Central Park`"
        )
        return

    user_id = str(ctx.author.id)
    bookmarks = load_bookmarks(user_id)

    # Check if location is already bookmarked
    for bookmark_name, bookmark_location in bookmarks.items():
        if bookmark_location.lower() == location.lower():
            await ctx.send(
                f"📌 You already have `{location}` bookmarked as `{bookmark_name}`!"
            )
            return

    # Generate a default name based on numbers
    if ":" in location:
        name, place = location.split(":", 1)
        name = name.strip()
        place = place.strip()
    else:
        # Find next available number
        used_names = set(bookmarks.keys())

        # Start from 1 and find the first unused number
        counter = 1
        while str(counter) in used_names:
            counter += 1

        name = str(counter)
        place = location

    # Add to bookmarks
    bookmarks[name] = place
    save_bookmarks(user_id, bookmarks)

    # Create an embed with the bookmark information
    embed = discord.Embed(
        title="📍 Location Bookmarked",
        description=f"Successfully added `{place}` to your bookmarks!",
        color=discord.Color.green(),
    )
    embed.add_field(name="Bookmark Name", value=name, inline=True)
    embed.add_field(name="Location", value=place, inline=True)
    embed.set_footer(
        text=f"You now have {len(bookmarks)} bookmarks. Use !list to see them all."
    )

    await ctx.send(embed=embed)


@bot.command(
    name="delete",
    help="Remove a location from your bookmarks. Usage: !delete <bookmark name>",
)
async def delete_bookmark(ctx, bookmark_name=None):
    """Command to delete a location from the user's bookmarks."""
    if bookmark_name is None:
        await ctx.send("Please specify a bookmark to delete. Example: `!delete A`")
        return

    user_id = str(ctx.author.id)
    bookmarks = load_bookmarks(user_id)

    if bookmark_name in bookmarks:
        location = bookmarks[bookmark_name]
        del bookmarks[bookmark_name]
        save_bookmarks(user_id, bookmarks)

        embed = discord.Embed(
            title="🗑️ Bookmark Deleted",
            description=f"Successfully removed `{location}` from your bookmarks.",
            color=discord.Color.red(),
        )
        embed.set_footer(
            text=f"You now have {len(bookmarks)} bookmarks. Use !list to see them all."
        )

        await ctx.send(embed=embed)
    else:
        await ctx.send(
            f"❌ Bookmark `{bookmark_name}` not found. Use `!list` to see your bookmarks."
        )


@bot.command(name="list", help="List all your bookmarked locations.")
async def list_bookmarks(ctx):
    """Command to list all of a user's bookmarks."""
    user_id = str(ctx.author.id)
    bookmarks = load_bookmarks(user_id)

    if not bookmarks:
        await ctx.send(
            "📭 You don't have any bookmarked locations yet. Use `!add <location>` to add one!"
        )
        return

    embed = discord.Embed(
        title="📚 Your Bookmarked Locations",
        description=f"You have {len(bookmarks)} saved locations:",
        color=discord.Color.blue(),
    )

    # Add each bookmark to the embed
    for name, location in bookmarks.items():
        embed.add_field(name=f"Bookmark {name}", value=location, inline=False)

    embed.set_footer(text="Use !add to add more or !delete to remove any.")

    await ctx.send(embed=embed)


async def process_bookmark_request(message):
    """Process natural language requests for bookmark management."""
    content = message.content.lower()
    user_id = str(message.author.id)

    # Pattern matching for bookmark-related requests
    if "save" in content or "bookmark" in content or "remember" in content:
        # Extract location (simple approach)
        location_phrases = ["this place", "location", "spot", "area", "place"]
        for phrase in location_phrases:
            if phrase in content:
                # Try to extract location from context
                # This is a simplified approach - in a real bot, you'd use NLP
                words = content.split()
                idx = words.index(phrase.split()[0])
                if idx > 0 and words[idx - 1] == "this":
                    # User is referring to a location mentioned earlier
                    # You'd need to track conversation context
                    await message.reply(
                        "I'd love to save this location, but I need to know what place you're referring to. Could you specify which location you'd like to bookmark?"
                    )
                    return True

        # Extract location after keywords
        for keyword in ["save", "bookmark", "remember"]:
            if keyword in content:
                parts = content.split(keyword, 1)
                if len(parts) > 1:
                    location = parts[1].strip()
                    # Clean up the location string
                    for ending in ["please", "for me", "for later", "."]:
                        if location.endswith(ending):
                            location = location.rsplit(ending, 1)[0].strip()

                    if location:
                        # Create a context that mimics command context
                        mock_ctx = discord.Object(id=0)
                        mock_ctx.send = message.channel.send
                        mock_ctx.author = message.author

                        # Call the add bookmark command
                        await add_bookmark(mock_ctx, location=location)
                        return True

    # Pattern matching for listing bookmarks
    if any(
        phrase in content
        for phrase in [
            "show my bookmarks",
            "list my bookmarks",
            "what are my bookmarks",
            "show saved",
            "list saved",
        ]
    ):
        # Create a context that mimics command context
        mock_ctx = discord.Object(id=0)
        mock_ctx.send = message.channel.send
        mock_ctx.author = message.author

        # Call the list bookmarks command
        await list_bookmarks(mock_ctx)
        return True

    # Pattern matching for deleting bookmarks
    if any(
        phrase in content
        for phrase in ["remove bookmark", "delete bookmark", "forget location"]
    ):
        bookmarks = load_bookmarks(user_id)
        if not bookmarks:
            await message.reply(
                "You don't have any bookmarks to delete. Use `!add <location>` to create some first!"
            )
            return True

        # Check if any bookmark name is mentioned
        for name in bookmarks.keys():
            if name.lower() in content.lower():
                # Create a context that mimics command context
                mock_ctx = discord.Object(id=0)
                mock_ctx.send = message.channel.send
                mock_ctx.author = message.author

                # Call the delete bookmark command
                await delete_bookmark(mock_ctx, bookmark_name=name)
                return True

        # If no specific bookmark is mentioned
        await message.reply(
            "Which bookmark would you like to delete? Here are your current bookmarks:"
        )

        # Create a context that mimics command context
        mock_ctx = discord.Object(id=0)
        mock_ctx.send = message.channel.send
        mock_ctx.author = message.author

        # Call the list bookmarks command
        await list_bookmarks(mock_ctx)
        return True

    return False


@bot.event
async def on_message(message: discord.Message):
    """Process incoming messages."""
    # Don't delete this line! It's necessary for the bot to process commands.
    await bot.process_commands(message)

    # Ignore messages from self or other bots to prevent infinite loops.
    if message.author.bot:
        return

    # Ignore messages with command prefix
    if message.content.startswith(PREFIX):
        return

    # Check for bookmark-related requests
    bookmark_processed = await process_bookmark_request(message)
    if bookmark_processed:
        return

    async with message.channel.typing():
        logger.info(f"Processing request from {message.author}: {message.content}")
        response = await agent.run(message)
        if not response or response.strip() == "":
            response = "I'm not sure what you're asking for. Try mentioning a specific location for activity recommendations."
        await message.reply(response)


# Add command error handler for handling invalid commands
@bot.event
async def on_command_error(ctx, error):
    """Handle command errors."""
    if isinstance(error, commands.CommandNotFound):
        # Log the error but don't show it in the console
        logger.info(f"Invalid command used by {ctx.author}: {ctx.message.content}")

        # Send a friendly message to the user
        await ctx.send(
            f"❌ Sorry, `{ctx.message.content}` is not a valid command. Type `{PREFIX}` to see available commands."
        )
    else:
        # For other types of errors, log them
        logger.error(f"Command error: {error}")
        await ctx.send(
            "An error occurred while processing your command. Please try again later."
        )


# Commands
@bot.command(
    name="activities",
    help="Get recommendations for activities accessible by public transit.",
)
async def activities(ctx, *, location=None):
    """Command to get activity recommendations."""
    if location is None:
        await ctx.send(
            "Please specify a location. For example: `!activities New York City`"
        )
        return

    # Show typing indicator while processing
    async with ctx.typing():
        logger.info(f"Processing activities command from {ctx.author}: {location}")

        # Create a mock message with the content
        mock_message = discord.Object(id=0)
        mock_message.content = f"recommend activities in {location}"
        mock_message.author = ctx.author

        # Process with the agent
        response = await agent.run(mock_message)

        # Send the response
        await ctx.send(response)


@bot.command(name="help", help="Shows how to use the transit recommendation bot")
async def help_transit(ctx):
    """Custom help command for the transit bot."""
    embed = discord.Embed(
        title="🚆 Transit Activity Recommendation Bot",
        description="Get recommendations for things to do that are accessible by public transit!",
        color=discord.Color.blue(),
    )

    embed.add_field(
        name="How to use:",
        value=(
            "**1. Ask naturally:**\n"
            '- "What can I do in Seattle?"\n'
            '- "Recommend activities near Chicago"\n'
            '- "What should I explore in Boston?"\n\n'
            '- "Bookmark Central Park"\n'
            '- "Show my bookmarks"\n'
            '- "Delete bookmark 1"\n\n'
            "**2. Use the command:**\n"
            "- `!activities [location]`\n"
            "Example: `!activities New York City`\n"
            "- `!add [location]`\n"
            "Example: `!add New York City`\n"
            "- `!delete [bookmark number]`\n"
            "Example: `!delete 1`"
        ),
        inline=False,
    )

    embed.add_field(
        name="Tips:",
        value=(
            "• Be specific with your location\n"
            "• The recommendations are based on public transit availability\n"
            "• Results include current weather and seasonal considerations"
        ),
        inline=False,
    )

    embed.add_field(
        name="Available Commands:",
        value=(
            f"`{PREFIX}activities [location]` - Get activity recommendations\n"
            f"`{PREFIX}add [location]` - Add a location to bookmarks\n"
            f"`{PREFIX}delete [bookmark number]` - Remove a bookmark\n"
            f"`{PREFIX}list` - View all your bookmarks\n"
            f"`{PREFIX}help` - Display this help message\n"
            f"`{PREFIX}clear` - Clear your conversation history"
        ),
        inline=False,
    )

    embed.set_footer(text="Powered by Mistral AI and OpenStreetMap")

    await ctx.send(embed=embed)


@bot.command(name="clear", help="Clear your conversation history with the bot")
async def clear_history(ctx):
    """Command to clear conversation history."""
    agent.conversation_manager.clear_history(ctx.author.id)
    await ctx.send(
        "🧹 I've cleared our conversation history. What would you like to talk about now?"
    )


# Start the bot
if __name__ == "__main__":
    bot.run(token)
