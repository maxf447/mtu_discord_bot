"""Fetches and updates status messages for the server"""

import asyncio
import datetime
import subprocess
import discord

class Status:
    """Class to fetch and update status messages"""

    def __init__(self, rcon):
        # Doesn't start the status update loop until start_loop is called
        self._rcon = rcon
        self._channel = None
        self._webhook = None
        self._msg = None
        self._content = None
        self._started = False

    async def _update_loop(self):
        """Runs the loop to update the status message"""
        while True:
            # Generate status message and update if necessary
            content = self.get_status()
            if content != self._content:
                self._content = content
                try:
                    await self._webhook.edit_message(self._msg,
                        content = None, embed = self._content)

                # Get status message if there was an error editing the current one
                except discord.HTTPException:
                    await self._get_msg()
            await asyncio.sleep(10)

    async def _get_msg(self):
        """Get status message if it exists, or create a new one"""
        # Search for status message
        self._msg = None
        async for msg in self._channel.history():
            if msg.webhook_id == self._webhook.id:
                self._msg = msg.id
                await self._webhook.edit_message(self._msg, content = None, embed = self._content)

        # No status message found, create a new one
        if self._msg is None:
            msg = await self._webhook.send(None, embed = self._content, username = "Server Status",
                wait = True)
            self._msg = msg.id

    def _get_memory(self):
        """Get total and in use memory"""
        try:
            output = subprocess.getoutput("free").split("\n")[1].split(" ")
            nums = [n for n in output if n != ""]
            return int(nums[1]), int(nums[2])
        except (IndexError, ValueError):
            return None

    def _get_disk(self):
        """Get total and in use disk space"""
        try:
            output = subprocess.getoutput("df /home").split("\n")[1].split(" ")
            nums = [n for n in output if n != ""]
            return int(nums[1]), int(nums[2])
        except (IndexError, ValueError):
            return None

    def _get_power(self):
        """Get current power draw from the server's 900W UPS"""
        try:
            output = subprocess.getoutput("/usr/sbin/apcaccess status | grep LOADPCT")
            return float(output.split(" ")[3]) * 900 / 100
        except (IndexError, ValueError):
            return None

    def get_status(self):
        """Generate an embed with the server status information"""
        player_list = self._rcon.get_players()
        mspt = self._rcon.get_mspt()
        memory = self._get_memory()
        disk = self._get_disk()
        power = self._get_power()

        # Generate status message
        # Player list
        if player_list is None:
            title = "Minecraft server unavailable"
            description = ""
            color = 0xFF0000
        else:
            title = f"{len(player_list)} player{'' if len(player_list) == 1 else 's'} online"
            description = f"```\n{'\n'.join(player_list)}```" if len(player_list) > 0 else ""
            color = 0x00FF00
            # Tick time
            if mspt is None:
                description += "\nTick Time: [unknown]"
            else:
                tps = min(20, 1000 / mspt)
                description += f"\nTick Time: {mspt:.1f} ms / 50.0 ms ({tps:.1f} TPS)"

        # Memory usage
        if memory is None:
            description += "\nMemory: [unknown]"
        else:
            description += f"\nMemory: {memory[1] / 2**20:.2f} GiB / {memory[0] / 2**20:.2f} GiB"

        # Disk usage
        if disk is None:
            description += "\nDisk: [unknown]"
        else:
            description += f"\nDisk: {disk[1] / 2**20:.1f} GiB / {disk[0] / 2**20:.1f} GiB"

        # Power usage
        if power is None:
            description += "\nPower: [unknown]"
        else:
            description += f"\nPower: {power:.0f}W"

        # Create and return embed
        embed = discord.Embed(title = title, description = description,
            timestamp = datetime.datetime.now(), color = color)
        embed.set_footer(text = "Last Updated")
        return embed

    def start_loop(self, status_channel, status_webhook):
        """Start running the async loop that updates the status"""
        # Don't start status loop multiple times
        if self._started:
            return
        self._started = True

        self._channel = status_channel
        self._webhook = status_webhook
        asyncio.create_task(self._update_loop())
