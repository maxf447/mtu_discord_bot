"""Allows detection and dealing with of common spam messages"""

import time
import datetime

# Array of sets of spam phrases; must match a full set to take action
SPAM_PHRASES = [
    ["macbook air", "dm if you are interested"],    # Giving away laptop scam
    ["giving away", "email me"],                    # Giving away PS5 scam
    ["giving away", "ps5"]                          # Giving away PS5 scam
]

class SpamHandler:
    """Spam handling class"""

    def __init__(self, client):
        """Set up message history tracker"""
        self.history = []
        self.client = client

    async def handle(self, msg):
        """Handle a message and act appropriately if spam"""

        # Matches spam phrases, delete message and time out user for 24 hours
        for phrase_set in SPAM_PHRASES:
            # Check if all phrases in set are matched
            matched_all = True
            for phrase in phrase_set:
                if phrase not in msg.content.lower():
                    matched_all = False

            # All phrases matched, take action
            if matched_all:
                try:
                    await msg.author.timeout(datetime.timedelta(days = 1),
                        reason = "Automated spam detection")
                except:
                    pass
                try:
                    await msg.delete()
                except:
                    pass
                return

        # Create hash of (content, author, attachments) and add to history
        hashed_msg = hash((msg.content, msg.author.id, tuple(a.size for a in msg.attachments)))
        self.history.append((time.time(), msg.id, msg.channel.id, hashed_msg))

        # Remove hashes older than 3 minutes from history
        while self.history[0][0] < time.time() - 180:
            del self.history[0]

        # Check how many channels had identical (content, author, attachments) hashes
        channels = set()
        for m in self.history:
            if m[3] == hashed_msg:
                channels.add(m[2])

        # Identical messages were sent in at least 3 channels, trigger spam removal
        if len(channels) >= 3:

            # Time out user for 15 minutes
            try:
                await msg.author.timeout(datetime.timedelta(minutes = 15),
                    reason = "Automated spam detection")
            except:
                pass

            # Purge all messages with matching hash
            for m in self.history.copy():
                if m[3] == hashed_msg:
                    obj = self.client.get_partial_messageable(m[2]).get_partial_message(m[1])
                    self.history.remove(m)
                    try:
                        await obj.delete()
                    except:
                        pass
