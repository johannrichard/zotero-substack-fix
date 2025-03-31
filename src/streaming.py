import json
import asyncio
import websockets
import backoff
from typing import Set
from pyzotero import zotero

class ZoteroStreamHandler:
    def __init__(self, zot: zotero.Zotero, api_key: str):
        self.zot = zot
        self.api_key = api_key
        self.ws = None
        self.connected = False
        self.topics: Set[str] = set()
        self.retry_delay = 10  # Initial retry delay in seconds

    @backoff.on_exception(
        backoff.expo,
        (websockets.ConnectionClosed, ConnectionError),
        max_tries=10
    )
    async def connect(self):
        """Establish WebSocket connection with exponential retry"""
        if self.ws:
            await self.ws.close()
        
        self.ws = await websockets.connect('wss://stream.zotero.org')
        response = await self.ws.recv()
        connection_info = json.loads(response)
        
        if connection_info["event"] == "connected":
            self.connected = True
            print("✓ Connected to Zotero streaming API")
            self.retry_delay = connection_info.get("retry", 10000) / 1000
            return True
        return False

    async def subscribe(self):
        """Subscribe to library updates"""
        if not self.connected:
            return

        # Determine topics based on library type
        library_type = "groups" if self.zot.library_type == "group" else "users"
        library_id = self.zot.library_id
        topic = f"/{library_type}/{library_id}"

        subscription_message = {
            "action": "createSubscriptions",
            "subscriptions": [
                {
                    "apiKey": self.api_key,
                    "topics": [topic]
                }
            ]
        }

        await self.ws.send(json.dumps(subscription_message))
        response = await self.ws.recv()
        subscription_info = json.loads(response)

        if subscription_info["event"] == "subscriptionsCreated":
            print(f"✓ Subscribed to updates for {topic}")
            self.topics.add(topic)
            return True
        return False

    async def process_updates(self):
        """Process incoming updates"""
        while True:
            try:
                message = await self.ws.recv()
                event = json.loads(message)

                if event["event"] == "topicUpdated":
                    topic = event["topic"]
                    version = event["version"]
                    print(f"\nReceived update for {topic} (version {version})")

                    # Get latest items
                    items = self.zot.items(
                        limit=5,  # Adjust as needed
                        sort="dateModified",
                        direction="desc"
                    )

                    # Process items
                    for item in items:
                        if "url" in item["data"]:
                            from main import process_item  # Import here to avoid circular imports
                            if updated_data := process_item(item):
                                try:
                                    self.zot.update_item(updated_data)
                                    print(f"✓ Updated item: {item['data'].get('title', '')[:50]}...")
                                except Exception as e:
                                    print(f"Error updating item: {str(e)}")

            except websockets.ConnectionClosed:
                print("Connection closed. Reconnecting...")
                await self.connect()
                await self.subscribe()

    async def run(self):
        """Main run loop"""
        while True:
            try:
                if not self.connected:
                    await self.connect()
                    await self.subscribe()
                await self.process_updates()
            except Exception as e:
                print(f"Error in streaming handler: {str(e)}")
                await asyncio.sleep(self.retry_delay)