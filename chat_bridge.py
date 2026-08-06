"""Chat bridge between Minecraft chat and Discord channel"""

import os
import threading
import re
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from discord import MessageType

class ChatBridge:
    """Class for creating chat bridge"""

    def __init__(self, log_file_path, bridge_webhook, rcon, msg_filter):
        """Initialize log file listener"""
        self._log_file_path = log_file_path
        self._bridge_webhook = bridge_webhook
        self._rcon = rcon
        self._msg_filter = msg_filter

        # Open log file
        self._log_file = open(self._log_file_path, "r", encoding = "utf-8")
        self._log_file.seek(0, 2)
        self._log_file_inode = os.stat(self._log_file_path).st_ino

        # Bind handler to updates in the log file directory
        self._observer = Observer()
        self._observer.schedule(Handler(self.file_update),
            os.path.dirname(self._log_file_path))
        thread = threading.Thread(target = self._observer.start)
        thread.start()

    def file_update(self, event):
        """File update event"""
        # File is not log file
        if event.src_path != self._log_file_path:
            return

        # Reopen file if it has changed (inode number is different)
        new_inode = os.stat(self._log_file_path).st_ino
        if new_inode != self._log_file_inode:
            self._log_file.close()
            self._log_file = open(self._log_file_path, "r", encoding = "utf-8")
            self._log_file_inode = new_inode

        # Read new lines in file
        lines = self._log_file.read().split("\n")
        for line in lines:
            self._parse_line(line)

    def _parse_line(self, line):
        """Parse a logfile line and send a webhook message if necessary"""
        # Skip non-info lines
        if len(line) < 33 or line[11:31] != "[Server thread/INFO]":
            return

        msg = line[33:]

        # Message is a chat message from a player
        if msg[0] == "<" and re.search("<(.*?)>", msg) is not None:
            # Extract username and message content
            username = re.search("<(.*?)>", msg).group(1)
            content = msg.removeprefix(f"<{username}> ")
            avatar_url = f"https://mc-heads.net/avatar/{username}"
            # Send message
            self._bridge_webhook.send(content, username = username, avatar_url = avatar_url)

        # Message is a message from the server
        elif msg.startswith("[Server] "):
            content = msg.removeprefix("[Server] ")
            self._bridge_webhook.send(content, username = "Server")

        # Message is a /me
        elif msg.startswith("* "):
            username = msg.split(" ")[1]
            content = msg.removeprefix(f"* {username} ")
            # Escape usernames with Markdown formatting
            username_clean = username.replace("_", "\\_")
            self._bridge_webhook.send(f"\\* {username_clean} {content}", username = "System")

        # Message is a join / leave / advancement / challenge / death message
        elif len(msg.split(" ")) > 1 and msg.split(" ")[1] in self._msg_filter:
            # Escape possible Markdown formatting in usernames
            msg_clean = msg.replace("_", "\\_")
            self._bridge_webhook.send(msg_clean, username = "System")

        # Special case for this one insane death message
        elif msg == "death.fell.accident.water":
            self._bridge_webhook.send(msg, username = "System")

    async def discord_msg(self, msg):
        """Discord message in chat bridge channel"""
        # No bot or empty messages
        if msg.author.bot or len(msg.clean_content) == 0:
            return

        # Generate tellraw for message
        msg_tellraw = [
            {"text": "[", "color": "white"},
            {"text": msg.author.display_name, "color": "blue"},
            {"text": "] " + msg.clean_content},
        ]

        # Message is a reply, fetch reply and add to tellraw
        if msg.reference is not None:
            replied_msg = await msg.channel.fetch_message(msg.reference.message_id)
            replied_name = replied_msg.author.display_name
            replied_content = replied_msg.clean_content

            # Undo Markdown formatting escape if message was a server message
            replied_content_clean = replied_content.replace("\\_", "_")

            # Message was automated
            if replied_msg.webhook_id is not None and replied_msg.type == MessageType.default:
                print(replied_msg)
                # Message was a /me
                if replied_content.startswith("\\* "):
                    msg_tellraw = [
                        {"text": f"┌ * {replied_content_clean.removeprefix("\\* ")}\n",
                        "color": "gray"}
                    ] + msg_tellraw

                # Message was a system message
                elif replied_msg.author.display_name == "System" \
                    and replied_msg.author.avatar is None:
                    msg_tellraw = [
                        {"text": f"┌ {replied_content_clean}\n", "color": "gray"}
                    ] + msg_tellraw

                # Message was sent by /say from server console
                elif replied_msg.author.display_name == "Server" \
                    and replied_msg.author.avatar is None:
                    msg_tellraw = [
                        {"text": f"┌ [Server] {replied_content}\n", "color": "gray"}
                    ] + msg_tellraw

                # Message was a chat bridged Minecraft user
                else:
                    msg_tellraw = [
                        {"text": f"┌ <{replied_name}> {replied_content}\n", "color": "gray"}
                    ] + msg_tellraw

            # Message was a Discord user
            else:
                msg_tellraw = [
                    {"text": f"┌ [{replied_name}] {replied_content_clean}\n", "color": "gray"}
                ] + msg_tellraw


        self._rcon.tellraw(msg_tellraw)

# Small event handler for file system update
class Handler(FileSystemEventHandler):
    """File system update event handler"""
    def __init__(self, file_callback):
        """Record log file path"""
        self._file_callback = file_callback

    def on_modified(self, event):
        """Check if modified file is log file path"""
        if not event.is_directory:
            self._file_callback(event)
