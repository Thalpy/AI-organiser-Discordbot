"""Mock database manager for testing"""

class MockDatabaseManager:
    """Mock database manager for testing"""
    
    async def execute_query(self, query, params=None, fetch_one=False, fetch_all=False):
        """Mock execute query"""
        if fetch_one:
            return {"id": 1, "user_id": "test_user"}
        elif fetch_all:
            return [{"id": 1, "user_id": "test_user"}]
        return None

async def get_database_manager():
    """Get database manager instance"""
    return MockDatabaseManager()