"""Allows detection and dealing with of common spam messages"""

import time
import datetime

class SpamHandler:
    """Spam handling class"""

    def __init__(self, client):
        """Set up message history tracker"""
        self.history = []
        self.client = client

    async def handle(self, msg):
        """Handle a message and act appropriately if spam"""

        # Create hash of (content, author, attachments) and add to history
        hashed_msg = hash((msg.content, msg.author.id, tuple(a.size for a in msg.attachments)))
        self.history.append((time.time(), msg.id, msg.channel.id, hashed_msg))

        # Remove hashes older than a minute from history
        while self.history[0][0] < time.time() - 60:
            del self.history[0]

        # Check how many channels had identical (content, author, attachments) hashes
        channels = set()
        for m in self.history:
            if m[3] == hashed_msg:
                channels.add(m[2])

        # Identical messages were sent in at least 3 channels, trigger spam removal
        if len(channels) >= 3:

            # Time out user for 15 minutes
            await msg.author.timeout(datetime.timedelta(minutes = 15),
                reason = "Automated spam detection")

            # Purge all messages with matching hash
            for m in self.history.copy():
                if m[3] == hashed_msg:
                    obj = self.client.get_partial_messageable(m[2]).get_partial_message(m[1])
                    self.history.remove(m)
                    await obj.delete()
