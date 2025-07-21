"""
Authentication service for Discord Task Management Bot
Handles JWT tokens, Discord OAuth, and session management
"""

import hashlib
import os
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer
from passlib.context import CryptContext

from utils.logging_config import get_logger

from .database import get_database_manager

logger = get_logger(__name__)

# Security configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security scheme
security = HTTPBearer()


class AuthService:
    """Authentication service for user management"""
    
    def __init__(self):
        self.db = None
    
    async def initialize(self):
        """Initialize the auth service"""
        self.db = await get_database_manager()
    
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire, "type": "access"})
        
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """Create JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        
        to_encode.update({"exp": expire, "type": "refresh"})
        
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    async def create_user_session(
        self,
        user_id: str,
        discord_token: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, str]:
        """Create a new user session"""
        try:
            # Generate session token
            session_token = secrets.token_urlsafe(32)
            
            # Create session data
            session_data = {
                'user_id': user_id,
                'session_token': session_token,
                'discord_token': discord_token,
                'expires_at': datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
                'ip_address': ip_address,
                'user_agent': user_agent
            }
            
            # Save session to database
            success = await self.db.create_user_session(session_data)
            
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create session"
                )
            
            # Create tokens
            access_token = self.create_access_token({"sub": user_id, "session": session_token})
            refresh_token = self.create_refresh_token({"sub": user_id, "session": session_token})
            
            logger.info(f"Created session for user {user_id}")
            
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
            }
            
        except Exception as e:
            logger.error(f"Failed to create session for user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Session creation failed"
            )
    
    async def get_user_from_session(self, session_token: str) -> Optional[Dict[str, Any]]:
        """Get user data from session token"""
        try:
            session = await self.db.get_user_session(session_token)
            
            if not session:
                return None
            
            # Update last activity
            await self.db.update_session_activity(session_token)
            
            return {
                'user_id': session['user_id'],
                'session_token': session_token,
                'ip_address': session.get('ip_address'),
                'user_agent': session.get('user_agent')
            }
            
        except Exception as e:
            logger.error(f"Failed to get user from session {session_token}: {e}")
            return None
    
    async def revoke_session(self, session_token: str) -> bool:
        """Revoke a user session"""
        try:
            # Delete session from database
            query = "DELETE FROM user_sessions WHERE session_token = $1"
            await self.db.execute_query(query, (session_token,))
            
            logger.info(f"Revoked session {session_token}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to revoke session {session_token}: {e}")
            return False
    
    def hash_password(self, password: str) -> str:
        """Hash a password"""
        return pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def generate_api_key(self) -> tuple[str, str]:
        """Generate API key and its hash"""
        api_key = f"tb_{secrets.token_urlsafe(32)}"
        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        return api_key, api_key_hash
    
    async def create_api_key(
        self,
        user_id: str,
        key_name: str,
        permissions: list[str],
        expires_at: Optional[datetime] = None
    ) -> str:
        """Create a new API key for a user"""
        try:
            api_key, api_key_hash = self.generate_api_key()
            
            # Save API key to database
            query = """
                INSERT INTO api_keys (user_id, key_name, api_key_hash, permissions, expires_at)
                VALUES ($1, $2, $3, $4, $5)
            """
            
            await self.db.execute_query(
                query,
                (user_id, key_name, api_key_hash, permissions, expires_at)
            )
            
            logger.info(f"Created API key '{key_name}' for user {user_id}")
            
            return api_key
            
        except Exception as e:
            logger.error(f"Failed to create API key for user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="API key creation failed"
            )
    
    async def verify_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Verify API key and return user info"""
        try:
            api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            
            query = """
                SELECT user_id, permissions, expires_at, is_active
                FROM api_keys
                WHERE api_key_hash = $1
            """
            
            result = await self.db.execute_query(query, (api_key_hash,), fetch_one=True)
            
            if not result:
                return None
            
            # Check if key is active and not expired
            if not result['is_active']:
                return None
            
            if result['expires_at'] and result['expires_at'] < datetime.utcnow():
                return None
            
            # Update last used timestamp
            update_query = """
                UPDATE api_keys
                SET last_used_at = NOW()
                WHERE api_key_hash = $1
            """
            await self.db.execute_query(update_query, (api_key_hash,))
            
            return {
                'user_id': result['user_id'],
                'permissions': result['permissions'],
                'auth_type': 'api_key'
            }
            
        except Exception as e:
            logger.error(f"Failed to verify API key: {e}")
            return None


# Global auth service instance
auth_service: Optional[AuthService] = None


async def get_auth_service() -> AuthService:
    """Get the global auth service instance"""
    global auth_service
    if auth_service is None:
        auth_service = AuthService()
        await auth_service.initialize()
    return auth_service


async def get_current_user(
    request: Request,
    token: str = Depends(security)
) -> Dict[str, Any]:
    """Get current user from JWT token or API key"""
    try:
        auth_svc = await get_auth_service()
        
        # Check if it's an API key
        if token.credentials.startswith("tb_"):
            user_data = await auth_svc.verify_api_key(token.credentials)
            if user_data:
                user_data['ip_address'] = request.client.host
                return user_data
        
        # Verify JWT token
        payload = auth_svc.verify_token(token.credentials)
        
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        # Get user from session
        session_token = payload.get("session")
        if not session_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token format"
            )
        
        user_data = await auth_svc.get_user_from_session(session_token)
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session not found or expired"
            )
        
        user_data['ip_address'] = request.client.host
        user_data['auth_type'] = 'jwt'
        
        return user_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )


async def get_optional_user(
    request: Request,
    token: Optional[str] = Depends(security)
) -> Optional[Dict[str, Any]]:
    """Get current user if authenticated, otherwise return None"""
    if not token:
        return None
    
    try:
        return await get_current_user(request, token)
    except HTTPException:
        return None