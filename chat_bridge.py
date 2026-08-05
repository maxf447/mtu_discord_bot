"""Chat bridge between Minecraft chat and Discord channel"""

import os
import threading
import re
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class ChatBridge:
    """Class for creating chat bridge"""

    def __init__(self, log_file_path, bridge_webhook, rcon):
        """Initialize log file listener"""
        self._log_file_path = log_file_path
        self._bridge_webhook = bridge_webhook
        self._rcon = rcon

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
            # Skip empty lines
            if line == "":
                continue

            self._bridge_webhook.send(line)

    def discord_msg(self, msg):
        """Discord message in chat bridge channel"""
        # No bot or empty messages
        if msg.author.bot or len(msg.clean_content) == 0:
            return

        self._rcon.tellraw({"text": msg.clean_content})

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
