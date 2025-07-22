"""Mock Discord web bridge for testing"""

from dataclasses import dataclass
from typing import Any, Dict

@dataclass
class BridgeMessage:
    """Mock bridge message"""
    type: str
    data: Dict[str, Any]

async def get_discord_web_bridge():
    """Get Discord web bridge instance"""
    return MockDiscordWebBridge()

class MockDiscordWebBridge:
    """Mock Discord web bridge for testing"""
    
    async def send_message(self, message: BridgeMessage):
        """Mock send message"""
        pass