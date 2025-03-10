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
handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s"))
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

@bot.event
async def on_ready():
    """Called when the bot successfully connects to Discord."""
    logger.info(f"{bot.user} has connected to Discord!")
    
    # Set the bot's status/activity
    activity = discord.Activity(
        type=discord.ActivityType.listening, 
        name="for transit recommendations"
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

    # Process only messages that look like they're asking for recommendations
    recommendation_keywords = [
        "recommend", "suggest", "what to do", "activities", 
        "things to do", "visit", "explore", "where should i go"
    ]
    
    if any(keyword in message.content.lower() for keyword in recommendation_keywords):
        # Send typing indicator while processing
        async with message.channel.typing():
            logger.info(f"Processing recommendation request from {message.author}: {message.content}")
            
            # Show initial response
            initial_response = await message.reply("🔍 Looking for activities accessible by public transit... This might take a moment!")
            
            # Process the message with the agent
            response = await agent.run(message)
            
            # Edit the initial message with the actual response
            await initial_response.edit(content=response)
    
# Commands
@bot.command(name="activities", help="Get recommendations for activities accessible by public transit.")
async def activities(ctx, *, location=None):
    """Command to get activity recommendations."""
    if location is None:
        await ctx.send("Please specify a location. For example: `!activities New York City`")
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

@bot.command(name="help_transit", help="Shows how to use the transit recommendation bot")
async def help_transit(ctx):
    """Custom help command for the transit bot."""
    embed = discord.Embed(
        title="🚆 Transit Activity Recommendation Bot",
        description="Get recommendations for things to do that are accessible by public transit!",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="How to use:",
        value=(
            "**1. Ask naturally:**\n"
            "- \"What can I do in Seattle?\"\n"
            "- \"Recommend activities near Chicago\"\n"
            "- \"What should I explore in Boston?\"\n\n"
            "**2. Use the command:**\n"
            "`!activities [location]`\n"
            "Example: `!activities New York City`"
        ),
        inline=False
    )
    
    embed.add_field(
        name="Tips:",
        value=(
            "• Be specific with your location\n"
            "• The recommendations are based on public transit availability\n"
            "• Results include current weather and seasonal considerations"
        ),
        inline=False
    )
    
    embed.set_footer(text="Powered by Mistral AI and OpenStreetMap")
    
    await ctx.send(embed=embed)

# Start the bot
if __name__ == "__main__":
    bot.run(token)