"""Handle whitelisting players on the server"""

import json
import os

class Whitelist:
    """Whitelist handler class"""

    def __init__(self, whitelist_file_path, whitelist_db_path, max_whitelist, rcon):
        """Open the whitelist file and database"""
        self._whitelist_file_path = whitelist_file_path
        self._whitelist_db_path = whitelist_db_path
        self._max_whitelist = max_whitelist
        self._rcon = rcon

        # Read whitelist db
        if os.path.exists(self._whitelist_db_path):
            with open(self._whitelist_db_path, "r", encoding = "utf-8") as f:
                self._whitelist_db = json.load(f)
        else:
            self._whitelist_db = {}

        # Read server whitelist file
        with open(self._whitelist_file_path, "r", encoding = "utf-8") as f:
            self._whitelist_file = json.load(f)

    def add_to_whitelist(self, user, edition, username):
        """Add a player to the whitelist"""

    def remove_from_whitelist(self, edition, username):
        """Remove a player from the whitelist"""
        # Find the player in question and remove them
        for player in self._whitelist_file:
            if player["name"] == (username if edition == "Java" else "." + username):
                self._whitelist_file.remove(player)
                self._update_whitelist()
                return

    def get_whitelist(self, user):
        """Get the whitelist of a Discord user"""
        # Find players whitelisted by user
        usernames = []
        for player in self._whitelist_file:
            if player["discord_user"] == user.id:
                usernames.append(player["name"])
        return usernames

    def get_discord_user(self, edition, username):
        """Get the Discord user ID a whitelisted player belongs to"""
        for player in self._whitelist_file:
            if player["name"] == (username if edition == "Java" else "." + username):
                return player["discord_user"]
        return None

    def get_max_whitelist(self, user):
        """Get the max number of players a user is allowed to whitelist"""
        if user.id in self._whitelist_db:
            return self._whitelist_db[user.id]["max_whitelist"]
        return self._max_whitelist

    def set_max_whitelist(self, user, n):
        """Set the max number of players a user is allowed to whitelist"""
        if user.id in self._whitelist_db:
            self._whitelist_db[user.id]["max_whitelist"] = n
        else:
            self._whitelist_db[user.id] = {
                "max_whitelist": n
            }
        self._update_db()

    def format(self, username):
        """Format a username which may start with a . to <username> (Java|Bedrock)"""
        if username.startswith("."):
            return username.removeprefix(".") + " (Bedrock)"
        return username + " (Java)"

    def _update_db(self):
        """Sync the database to disk"""
        with open(self._whitelist_db_path, "w", encoding = "utf-8") as f:
            json.dump(self._whitelist_db, f, indent = 2)

    def _update_whitelist(self):
        """Sync the server whitelist to disk and reload on the server"""
        with open(self._whitelist_file_path, "w", encoding = "utf-8") as f:
            json.dump(self._whitelist_file, f, indent = 2)
        self._rcon.reload_whitelist()
