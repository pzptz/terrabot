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


@bot.event
async def on_interaction(interaction):
    """Handle button interactions."""
    if interaction.type == discord.InteractionType.component:
        # Extract info from custom_id
        custom_id = interaction.data.get("custom_id", "")

        if custom_id.startswith("bookmark_"):
            # Extract place name from custom_id
            place_name = custom_id[9:]  # Remove "bookmark_" prefix

            # Get place details from the agent's last recommendations
            place_info = agent.get_place_by_name(interaction.user.id, place_name)

            if place_info:
                user_id = str(interaction.user.id)
                bookmarks = load_bookmarks(user_id)

                # Find next available number for bookmark name
                used_names = set(bookmarks.keys())
                counter = 1
                while str(counter) in used_names:
                    counter += 1

                name = str(counter)

                # Format a nice description for the bookmark
                place_types = ", ".join(place_info.get("types", ["place"]))
                transit_info = place_info.get("transit_info", {})
                transit_details = ""

                if transit_info.get("transit_type"):
                    transit_details = f" - {transit_info.get('transit_type')} available"
                elif transit_info.get("transit_types"):
                    transit_details = (
                        f" - {', '.join(transit_info.get('transit_types'))} available"
                    )

                # Create bookmark with formatted description
                bookmark_description = f"{place_name} ({place_types}){transit_details}"
                bookmarks[name] = bookmark_description
                save_bookmarks(user_id, bookmarks)

                # Create an embed response
                embed = discord.Embed(
                    title="📍 Location Bookmarked",
                    description=f"Successfully added `{place_name}` to your bookmarks!",
                    color=discord.Color.green(),
                )
                embed.add_field(name="Bookmark Number", value=name, inline=True)
                embed.add_field(name="Location", value=place_name, inline=True)
                embed.set_footer(
                    text=f"You now have {len(bookmarks)} bookmarks. Use !list to see them all."
                )

                # Respond to the interaction
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                # Place not found in recommendations
                await interaction.response.send_message(
                    "Sorry, I couldn't find details for this place anymore. Try asking for recommendations again.",
                    ephemeral=True,
                )

        elif custom_id.startswith("delete_bookmark_"):
            # Extract bookmark ID from custom_id
            bookmark_id = custom_id[16:]  # Remove "delete_bookmark_" prefix

            user_id = str(interaction.user.id)
            bookmarks = load_bookmarks(user_id)

            if bookmark_id in bookmarks:
                # Get the bookmark location before deleting
                location = bookmarks[bookmark_id]

                # Delete the bookmark
                del bookmarks[bookmark_id]
                save_bookmarks(user_id, bookmarks)

                # Create an embed response
                embed = discord.Embed(
                    title="🗑️ Bookmark Deleted",
                    description=f"Successfully removed bookmark `{bookmark_id}`: `{location}`",
                    color=discord.Color.red(),
                )

                # Add information about remaining bookmarks
                if bookmarks:
                    embed.set_footer(
                        text=f"You now have {len(bookmarks)} bookmarks remaining."
                    )
                else:
                    embed.set_footer(
                        text="You have no bookmarks remaining. Use the Bookmark buttons on recommendations to add new ones!"
                    )

                # Respond to the interaction
                await interaction.response.send_message(embed=embed, ephemeral=True)

                # Update the bookmarks list message with new buttons if there are still bookmarks
                if interaction.message:
                    if bookmarks:
                        # Create new embed with updated bookmark list
                        new_embed = discord.Embed(
                            title="📚 Your Bookmarked Locations",
                            description=f"You have {len(bookmarks)} saved locations:",
                            color=discord.Color.blue(),
                        )

                        # Add each bookmark to the embed
                        for name, location in bookmarks.items():
                            new_embed.add_field(
                                name=f"Bookmark {name}", value=location, inline=False
                            )

                        new_embed.set_footer(
                            text="Click the Delete button to remove a bookmark or use !delete-all to clear all."
                        )

                        # Create a new view with delete buttons for the remaining bookmarks
                        new_view = discord.ui.View(timeout=300)
                        for remaining_id in bookmarks.keys():
                            new_view.add_item(DeleteBookmarkButton(remaining_id))

                        await interaction.message.edit(embed=new_embed, view=new_view)
                    else:
                        # No bookmarks remaining, update the message accordingly
                        empty_embed = discord.Embed(
                            title="📭 No Bookmarks",
                            description="You have deleted all your bookmarks.",
                            color=discord.Color.blue(),
                        )

                        await interaction.message.edit(embed=empty_embed, view=None)
            else:
                # Bookmark not found
                await interaction.response.send_message(
                    f"❌ Bookmark `{bookmark_id}` not found. It may have already been deleted.",
                    ephemeral=True,
                )


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
    help="Remove a location from your bookmarks. Usage: !delete <number>",
)
async def delete_bookmark(ctx, bookmark_name=None):
    """Command to delete a location from the user's bookmarks."""
    if bookmark_name is None:
        await ctx.send("Please specify a bookmark to delete. Example: `!delete 1`")
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


class DeleteBookmarkButton(discord.ui.Button):
    def __init__(self, bookmark_id):
        """Initialize a delete button for a specific bookmark."""
        super().__init__(
            style=discord.ButtonStyle.danger,
            label=f"🗑️ {bookmark_id}",
            custom_id=f"delete_bookmark_{bookmark_id}",
        )
        self.bookmark_id = bookmark_id

    async def callback(self, interaction: discord.Interaction):
        """Called when the button is clicked."""
        # This will be handled by the on_interaction event handler
        pass


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

    embed.set_footer(
        text="Click the Delete button to remove a bookmark or use !delete-all to clear all."
    )

    # Create a view with delete buttons for each bookmark
    view = discord.ui.View(timeout=300)  # 5 minute timeout
    for bookmark_id in bookmarks.keys():
        view.add_item(DeleteBookmarkButton(bookmark_id))

    await ctx.send(embed=embed, view=view)


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

    async with message.channel.typing():
        logger.info(f"Processing request from {message.author}: {message.content}")
        response, view = await agent.run(message)
        if not response or response.strip() == "":
            response = "I'm not sure what you're asking for. Try mentioning a specific location for activity recommendations."
            await message.reply(response)
        else:
            # Send the response with view if available
            if view:
                await message.reply(response, view=view)
            else:
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
            f"❌ Sorry, `{ctx.message.content}` is not a valid command. Type `{PREFIX}help` to see available commands."
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
        class MockMessage:
            def __init__(self, author, content):
                self.author = author
                self.content = content

        mock_message = MockMessage(ctx.author, f"recommend activities in {location}")

        # Process with the agent
        response, view = await agent.run(mock_message)

        # Send the response with view if available
        if view:
            await ctx.send(response, view=view)
        else:
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
            "**2. Use the command:**\n"
            '- "`!activities <location>`"\n'
            "Example: `!activities New York City`\n"
            '- "`!delete <number>`"\n'
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
            f"`{PREFIX}activities <location>` - Get activity recommendations\n"
            f"`{PREFIX}list` - View all your bookmarks\n"
            f"`{PREFIX}add <location>` - Add a location to bookmarks\n"
            f"`{PREFIX}delete <number>` - Remove a bookmark\n"
            f"`{PREFIX}delete-all` - Delete all your bookmarks\n"
            f"`{PREFIX}help` - Display this help message\n"
            f"`{PREFIX}clear` - Clear your conversation history\n"
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


@bot.command(name="delete-all", help="Delete all your bookmarked locations.")
async def clear_bookmarks(ctx):
    """Simple command to clear all of a user's bookmarks without button confirmation."""
    user_id = str(ctx.author.id)
    bookmarks = load_bookmarks(user_id)

    if not bookmarks:
        await ctx.send("📭 You don't have any bookmarked locations to clear.")
        return

    # Count how many bookmarks will be deleted
    bookmark_count = len(bookmarks)

    # Clear the bookmarks and save
    bookmarks.clear()
    save_bookmarks(user_id, bookmarks)

    embed = discord.Embed(
        title="🗑️ Bookmarks Cleared",
        description=f"Successfully deleted all {bookmark_count} of your bookmarks.",
        color=discord.Color.red(),
    )

    await ctx.send(embed=embed)


# Start the bot
if __name__ == "__main__":
    bot.run(token)
