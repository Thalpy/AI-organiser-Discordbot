"""Authentication module for API"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt

# Mock authentication functions for testing
async def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Mock user authentication"""
    if username == "test_user" and password == "test_password":
        return {
            "id": "test_user_id",
            "username": "test_user",
            "is_admin": False
        }
    return None

async def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Mock access token creation"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, "secret_key", algorithm="HS256")

async def get_current_active_user() -> Dict[str, Any]:
    """Mock current user getter"""
    return {
        "id": "test_user_id",
        "username": "test_user",
        "is_admin": False
    }