"""Main FastAPI application entry point"""

from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi

import os
import time
import jwt
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from utils.logging_config import get_logger, PerformanceMonitor
from utils.config import get_settings
from .websocket_manager import connection_manager, websocket_handler
from .auth import authenticate_user, create_access_token

# Import API routers
from .routers import tasks, users, analytics, notifications, calendar

# Setup logging
logger = get_logger(__name__)

# Load settings
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title="Task Bot API",
    description="API for Task Bot with enhanced features",
    version="1.0.0",
    docs_url=None,  # Disable default docs
    redoc_url=None,  # Disable default redoc
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Authentication endpoints
@app.post("/api/auth/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()) -> Dict[str, str]:
    """Login endpoint to get an access token"""
    with PerformanceMonitor("login_for_access_token"):
        user = await authenticate_user(form_data.username, form_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = await create_access_token(
            data={"sub": user["username"], "id": user["id"], "is_admin": user.get("is_admin", False)},
            expires_delta=access_token_expires
        )
        
        return {"access_token": access_token, "token_type": "bearer"}


# WebSocket endpoints
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for real-time features"""
    from .websocket_manager import presence_manager
    
    await connection_manager.connect(websocket, user_id)
    
    # Set user as online
    await presence_manager.update_user_presence(user_id, "online")
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                await websocket_handler.handle_message(websocket, message)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON format"
                }))
    except WebSocketDisconnect:
        # Set user as offline and clean up
        await presence_manager.set_user_offline(user_id)
        connection_manager.disconnect(websocket)


@app.websocket("/ws/room/{room_id}")
async def room_websocket_endpoint(websocket: WebSocket, room_id: str, user_id: str):
    """WebSocket endpoint for room-specific real-time features"""
    await connection_manager.connect(websocket, user_id, {"room_id": room_id})
    
    # Auto-join the room
    await websocket_handler._handle_join_room(websocket, {"room_id": room_id})
    
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                # Add room context to message
                message["room_id"] = room_id
                await websocket_handler.handle_message(websocket, message)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON format"
                }))
    except WebSocketDisconnect:
        # Auto-leave the room
        await websocket_handler._handle_leave_room(websocket, {"room_id": room_id})
        connection_manager.disconnect(websocket)


# Health check endpoint
@app.get("/api/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": app.version,
        "connected_users": len(connection_manager.get_connected_users())
    }


# Custom API docs
@app.get("/api/docs", include_in_schema=False)
async def custom_swagger_ui_html() -> Any:
    """Custom Swagger UI"""
    return get_swagger_ui_html(
        openapi_url="/api/openapi.json",
        title=f"{app.title} - API Documentation",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@4/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@4/swagger-ui.css",
    )


@app.get("/api/openapi.json", include_in_schema=False)
async def get_open_api_endpoint() -> Dict[str, Any]:
    """Return OpenAPI schema"""
    return get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )


# Include routers
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["notifications"])
app.include_router(calendar.router, prefix="/api/calendar", tags=["calendar"])


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc) -> JSONResponse:
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred"},
    )


# Middleware for request logging and timing
@app.middleware("http")
async def log_requests(request, call_next):
    """Log all requests with timing information"""
    start_time = time.time()
    
    # Process the request
    response = await call_next(request)
    
    # Calculate processing time
    process_time = time.time() - start_time
    
    # Log the request
    logger.info(
        f"Request: {request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.4f}s"
    )
    
    # Add timing header
    response.headers["X-Process-Time"] = f"{process_time:.4f}"
    
    return response


# Rate limiting middleware (basic implementation)
from collections import defaultdict
import asyncio

# Simple in-memory rate limiter (in production, use Redis)
request_counts = defaultdict(list)
RATE_LIMIT_REQUESTS = 100  # requests per minute
RATE_LIMIT_WINDOW = 60  # seconds

@app.middleware("http")
async def rate_limit_middleware(request, call_next):
    """Basic rate limiting middleware"""
    client_ip = request.client.host
    current_time = time.time()
    
    # Clean old requests
    request_counts[client_ip] = [
        req_time for req_time in request_counts[client_ip]
        if current_time - req_time < RATE_LIMIT_WINDOW
    ]
    
    # Check rate limit
    if len(request_counts[client_ip]) >= RATE_LIMIT_REQUESTS:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "Rate limit exceeded"}
        )
    
    # Add current request
    request_counts[client_ip].append(current_time)
    
    response = await call_next(request)
    return response


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Run startup tasks"""
    logger.info("Starting up FastAPI application")
    # Initialize services if needed
    # from database import initialize_database
    # await initialize_database()


@app.on_event("shutdown")
async def shutdown_event():
    """Run shutdown tasks"""
    logger.info("Shutting down FastAPI application")
    # Clean up resources if needed
    # from database import close_database_connection
    # await close_database_connection()


# Run the application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)