"""Fetches and updates status messages for the server"""

import asyncio
import datetime
import subprocess
import struct
import discord
import serial

class Status:
    """Class to fetch and update status messages"""

    def __init__(self, rcon):
        # Doesn't start the status update loop until start_loop is called
        self._rcon = rcon
        self._channel = None
        self._webhook = None
        self._msg = None
        self._started = False

        # CPU info
        self._cpu_idle = None
        self._cpu_total = None

    async def _update_loop(self):
        """Runs the loop to update the status message"""
        while True:
            try:
                # Generate status message and serial data
                embed, serial_data = self.get_status()

                # Attempt to send serial data
                try:
                    serial = serial.Serial("/dev/ttyACM0", timeout = 0.1)
                    serial.write(serial_data)
                    assert(serial.read() == 0x69)
                except:
                    pass

                # Attempt to edit status message
                try:
                    await self._webhook.edit_message(self._msg,
                        content = None, embed = embed)
                # Get status message if there was an error editing the current one
                except:
                    await self._get_msg()
            except:
                pass
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
                wait = True, allowed_mentions = discord.AllowedMentions.none())
            self._msg = msg.id

    def _get_cpu(self):
        """Get CPU usage since last call"""
        try:
            # Read total CPU time
            with open("/proc/stat", "r") as f:
                data = f.readline().removeprefix("cpu").strip()
                nums = [int(n) for n in data.split(" ")]
                idle = nums[3]
                total = sum(nums)

                # CPU time has not been previously set, return None
                if self._cpu_idle is None:
                    usage = None
                # CPU time has been previously set, calculate usage delta since last
                else:
                    usage = 1 - (idle - self._cpu_idle) / (total - self._cpu_total)

            # Set CPU times
            self._cpu_idle = idle
            self._cpu_total = total
            return usage

        except:
            return None

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

    def get_status(self):
        """Generate an embed with the server status information"""
        player_list = self._rcon.get_players()
        mspt = self._rcon.get_mspt()
        cpu = self._get_cpu()
        memory = self._get_memory()
        disk = self._get_disk()

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
            if mspt is None or mspt == 0:
                description += "\nTick Time: [unknown]"
            else:
                tps = min(20, 1000 / mspt)
                description += f"\nTick Time: {mspt:.1f} ms / 50.0 ms ({tps:.1f} TPS)"

        # CPU usage
        if cpu is None:
            description += "\nCPU Usage: [unknown]"
        else:
            description += f"\nCPU Usage: {cpu * 100:.1f}%"

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

        # Create embed
        embed = discord.Embed(title = title, description = description,
            timestamp = datetime.datetime.now(), color = color)
        embed.set_footer(text = "Last Updated")

        # Create serial data
        serial = struct.pack("<BIIII?IB",
            int(cpu * 100),
            int(memory[0] / 2 ** 10),
            int(memory[1] / 2 ** 10),
            int(disk[0] / 2 ** 10),
            int(disk[1] / 2 ** 10),
            player_list is not None,
            int(mspt * 1000),
            len(player_list)
        )
        for player in player_list:
            serial += bytes(player, encoding = "ascii") + b'\x00'

        return embed, serial

    def start_loop(self, status_channel, status_webhook):
        """Start running the async loop that updates the status"""
        # Don't start status loop multiple times
        if self._started:
            return
        self._started = True

        self._channel = status_channel
        self._webhook = status_webhook
        asyncio.create_task(self._update_loop())
