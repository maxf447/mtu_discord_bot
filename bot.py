"""Main bot code"""

import os
import json
from typing import Literal
import aiohttp
import discord

import status
import rcon_server
import chat_bridge
import whitelist

# Load the bot config file
path = os.path.join(os.path.dirname(__file__), "config.json")
with open(path, "r", encoding = "utf-8") as f:
    config = json.load(f)

# Initialize the Discord bot
client = discord.Client(intents = discord.Intents.all(),
    allowed_mentions = discord.AllowedMentions.none())

# Start RCON communication with the server
rcon = rcon_server.RCONServer(config["rcon_password"], config["rcon_port"])

# Initialize the server status message system
server_status = status.Status(rcon)

# Start chat bridge service
bridge_webhook = discord.SyncWebhook.from_url(config["chat_bridge_webhook"])
bridge = chat_bridge.ChatBridge(config["log_file_path"],
    bridge_webhook, rcon, config["message_filter"])

# Start whitelist service
whitelist = whitelist.Whitelist(config["whitelist_file_path"], config["whitelist_db_path"],
    config["max_whitelist"], rcon)

# Create slash commands
tree = discord.app_commands.CommandTree(client)
user_group = discord.app_commands.Group(
    name = "whitelist", description = "Whitelist commands")
admin_group = discord.app_commands.Group(
    name = "wladmin", description = "Admin whitelist commands")

@user_group.command(name = "add", description = "Add an account to your whitelist")
async def user_add(intr: discord.Interaction, edition: Literal["Java", "Bedrock"], username: str):
    """Add a user to the whitelist"""
    print(intr)
    print(edition)
    print(username)

@user_group.command(name = "remove", description = "Remove an account from your whitelist")
async def user_remove(intr: discord.Interaction,
    edition: Literal["Java", "Bedrock"], username: str):
    """Remove a user from the whitelist"""
    # Player is whitelisted and owned by Discord user
    user_id = whitelist.get_discord_user(edition, username)
    if user_id == intr.user.id:
        whitelist.remove_from_whitelist(edition, username)
        await intr.response.send_message(
            f"{username} ({edition}) has been removed from <@{user_id}>'s whitelist!")

    # Player is owned by a different Discord user
    elif user_id is not None:
        await intr.response.send_message(
            f"{username} ({edition}) was not whitelisted by you!")

    # Player is not whitelisted
    else:
        await intr.response.send_message(f"{username} ({edition}) is not whitelisted!",
            ephemeral = True)

@user_group.command(name = "list", description = "List your whitelist")
async def user_list(intr: discord.Interaction):
    """List a user's whitelist"""
    players = whitelist.get_whitelist(intr.user)
    max_whitelist = whitelist.get_max_whitelist(intr.user)
    msg = f"You have {len(players)}/{max_whitelist} accounts whitelisted"
    for player in players:
        msg += f"\n- {whitelist.format(player)}"
    await intr.response.send_message(msg)

@admin_group.command(name = "add", description = "Add an account to a user's whitelist")
async def admin_add(intr: discord.Interaction, user: discord.User,
    edition: Literal["Java", "Bedrock"], username: str):
    """(Admin) Add a player to a user's whitelist"""
    print(intr)
    print(user)
    print(edition)
    print(username)

@admin_group.command(name = "remove", description = "Remove an account from the whitelist")
async def admin_remove(intr: discord.Interaction,
    edition: Literal["Java", "Bedrock"], username: str):
    """(Admin) Remove a player from the whitelist"""
    # Player is whitelisted
    user_id = whitelist.get_discord_user(edition, username)
    if user_id is not None:
        whitelist.remove_from_whitelist(edition, username)
        await intr.response.send_message(
            f"{username} ({edition}) has been removed from <@{user_id}>'s whitelist!")

    # Player is not whitelisted
    else:
        await intr.response.send_message(f"{username} ({edition}) is not whitelisted!",
            ephemeral = True)

@admin_group.command(name = "list", description = "List a user's whitelist")
async def admin_list(intr: discord.Interaction, user: discord.User):
    """(Admin) List a user's whitelist"""
    players = whitelist.get_whitelist(user)
    max_whitelist = whitelist.get_max_whitelist(user)
    msg = f"<@{user.id}> has {len(players)}/{max_whitelist} accounts whitelisted"
    for player in players:
        msg += f"\n- {whitelist.format(player)}"
    await intr.response.send_message(msg)

@admin_group.command(name = "user", description = "Get the owner of a whitelisted account")
async def admin_user(intr: discord.Interaction,
    edition: Literal["Java", "Bedrock"], username: str):
    """(Admin) Get the Discord user of a whitelisted player"""
    user_id = whitelist.get_discord_user(edition, username)
    # Player is whitelisted
    if user_id is not None:
        await intr.response.send_message(f"{username} ({edition}) is owned by <@{user_id}>")
    else:
        await intr.response.send_message(f"{username} ({edition}) is not whitelisted!",
            ephemeral = True)

@tree.command(name = "status", description = "Get current server status")
async def status_msg(intr: discord.Interaction):
    """Request a server status message"""
    # Generate status embed and change footer from "Last Updated" since message is not updated
    embed = server_status.get_status()
    embed.set_footer(text = "Server Status")
    await intr.response.send_message(embed = embed)

# Add slash commands to the tree
tree.add_command(user_group)
tree.add_command(admin_group)

# Assign chat bridge to on_message event
@client.event
async def on_message(msg):
    """Pass messages to chat bridge"""
    # Message is from chat bridge
    if msg.channel.id == config["chat_bridge_channel"]:
        await bridge.discord_msg(msg)

@client.event
async def on_ready():
    """Initialize things once bot is loaded"""

    # Register slash commands
    print("Syncing slash commands... ", end = "")
    await tree.sync()
    print("Done!")

    # Get appropriate status channel and webhook
    status_channel = client.get_channel(config["status_channel"])
    status_webhook = discord.Webhook.from_url(
        config["status_webhook"], session = aiohttp.ClientSession())

    # Start server status loop
    server_status.start_loop(status_channel, status_webhook)

# Start Discord client
client.run(config["bot_token"])
