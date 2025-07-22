"""Mock sync service for testing"""

async def get_sync_service():
    """Get sync service instance"""
    return MockSyncService()

async def sync_task_update(task_data, user_id, source):
    """Mock sync task update"""
    pass

class MockSyncService:
    """Mock sync service for testing"""
    
    async def sync_task_update(self, task_data, user_id, source):
        """Mock sync task update"""
        pass