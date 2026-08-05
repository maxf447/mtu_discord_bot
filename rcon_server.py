"""Communicate with the Minecraft server through RCON"""

import re
import mcrcon

# Communicates with the Minecraft server via RCON
class RCONServer:
    """Small wrapper for RCON communication with the Minecraft server"""

    def __init__(self, rcon_password, rcon_port):
        # Create the RCON connection
        self.rcon = mcrcon.MCRcon("localhost", rcon_password, port = rcon_port, timeout = 1)

    def get_players(self):
        """Get all players on the server"""
        result = self._run_command("list")
        if result is None:
            return None
        players = result.partition(": ")[2].split(", ")
        if "" in players:
            players = []
        return players

    def get_mspt(self):
        """Get the current server MSPT"""
        result = self._run_command("tick query")
        if result is None:
            return None
        return float(re.search(r"(?<=tick: )\d+\.\d(?=ms)", result).group(0))

    # Run command, attempting to reconnect if necessary
    def _run_command(self, command):
        # Attempt to run command
        try:
            return self.rcon.command(command)
        # On error, attempt to reconnect and rerun command
        except (BrokenPipeError, ConnectionRefusedError, mcrcon.MCRconException):
            try:
                self.rcon.connect()
                return self.rcon.command(command)
            # On a second error, give up and return None
            except (BrokenPipeError, ConnectionRefusedError, mcrcon.MCRconException):
                return None
