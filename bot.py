import os
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
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# Import the Activity Recommendation Agent
agent = ActivityRecommendationAgent()

# Get the token from the environment variables
token = os.getenv("DISCORD_TOKEN")


def extract_location(content: str) -> str:
    """
    Extract location from the message content.
    Returns the location string if found, None otherwise.
    """
    # Check for common location indicators
    location_keywords = ["in ", "near ", "around ", "at ", "close to "]

    for keyword in location_keywords:
        if keyword in content.lower():
            parts = content.lower().split(keyword, 1)
            if len(parts) > 1:
                raw_location = parts[1].strip()

                # Cut off location at certain phrases
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
                    " accessible",
                    " public",
                    " transit",
                    "?",
                    "!",
                    ".",
                ]

                for phrase in cutoff_phrases:
                    if phrase in raw_location:
                        raw_location = raw_location.split(phrase, 1)[0].strip()

                return raw_location if raw_location else None

    # Check if the message might be asking for activity recommendations without specifying location format
    if any(
        word in content.lower()
        for word in ["activities", "recommend", "suggest", "do", "visit", "explore"]
    ):
        # Try to find proper nouns that might be locations (basic approach)
        words = content.split()
        for i, word in enumerate(words):
            # Check for capitalized words that aren't at the start of a sentence
            if i > 0 and word[0].isupper() and len(word) > 1:
                # Basic check to avoid pronouns and other common capitalized words
                if word.lower() not in [
                    "i",
                    "me",
                    "my",
                    "mine",
                    "we",
                    "us",
                    "our",
                    "ours",
                    "you",
                    "your",
                    "yours",
                ]:
                    return word

    return None


@bot.event
async def on_ready():
    """Called when the bot successfully connects to Discord."""
    logger.info(f"{bot.user} has connected to Discord!")

    # Set the bot's status/activity
    activity = discord.Activity(
        type=discord.ActivityType.listening, name="for transit recommendations"
    )
    await bot.change_presence(activity=activity)


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

    # Process all messages (not just those with recommendation keywords)
    # Check if we can extract a location from the message
    location = extract_location(message.content)

    async with message.channel.typing():
        logger.info(f"Processing request from {message.author}: {message.content}")

        # if location:
        # Show initial response with the detected location
        # initial_response = await message.reply(
        # f"🔍 Looking for activities in {location} accessible by public transit... This might take a moment!"
        # )
        # response = await agent.run(message)

        # Send the response back to the channel
        # await initial_response.edit(content=response)
        # else:
        response = await agent.run(message)
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
            f"❌ Sorry, `{ctx.message.content}` is not a valid command. Type `{PREFIX}helpme` to see available commands."
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


@bot.command(name="helpme", help="Shows how to use the transit recommendation bot")
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
            "**2. Use the command:**\n"
            "`!activities [location]`\n"
            "Example: `!activities New York City`"
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
            f"`{PREFIX}helpme` - Display this help message\n"
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
