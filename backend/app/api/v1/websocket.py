"""
WebSocket endpoints for real-time data
"""

import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from typing import Dict, Any
import logging

from ...services.websocket_service import websocket_manager
from ...auth.jwt_handler import get_current_user_ws
from ...models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_connections: Dict[str, str] = {}  # user_id -> connection_id

    async def connect(self, websocket: WebSocket, connection_id: str, user: User):
        """Accept WebSocket connection for authenticated user"""
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        self.user_connections[str(user.id)] = connection_id

        # Start Binance WebSocket if not already running
        websocket_manager.start_binance_websocket(user.use_testnet)

        logger.info(f"User {user.username} connected via WebSocket. Connection ID: {connection_id}")

    def disconnect(self, connection_id: str):
        """Disconnect WebSocket"""
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            del self.active_connections[connection_id]

            # Remove user connection mapping
            user_id_to_remove = None
            for user_id, conn_id in self.user_connections.items():
                if conn_id == connection_id:
                    user_id_to_remove = user_id
                    break

            if user_id_to_remove:
                del self.user_connections[user_id_to_remove]

            logger.info(f"WebSocket disconnected. Connection ID: {connection_id}")

    async def send_personal_message(self, message: dict, connection_id: str):
        """Send message to specific connection"""
        if connection_id in self.active_connections:
            try:
                websocket = self.active_connections[connection_id]
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending message: {e}")
                self.disconnect(connection_id)

    async def broadcast_to_user(self, message: dict, user_id: str):
        """Send message to specific user"""
        if user_id in self.user_connections:
            connection_id = self.user_connections[user_id]
            await self.send_personal_message(message, connection_id)


manager = ConnectionManager()


@router.websocket("/ws/{connection_id}")
async def websocket_endpoint(websocket: WebSocket, connection_id: str):
    """Main WebSocket endpoint"""
    try:
        # Get token from query parameters
        token = websocket.query_params.get("token")
        if not token:
            await websocket.close(code=4001, reason="Missing authentication token")
            return

        # Authenticate user
        try:
            user = await get_current_user_ws(token)
        except Exception as e:
            await websocket.close(code=4001, reason="Invalid authentication token")
            return

        # Connect user
        await manager.connect(websocket, connection_id, user)

        try:
            while True:
                # Receive message from client
                data = await websocket.receive_text()
                message = json.loads(data)

                # Handle different message types
                await handle_websocket_message(message, connection_id, user)

        except WebSocketDisconnect:
            manager.disconnect(connection_id)
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            manager.disconnect(connection_id)

    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        try:
            await websocket.close(code=4000, reason="Connection error")
        except:
            pass


async def handle_websocket_message(message: dict, connection_id: str, user: User):
    """Handle incoming WebSocket messages"""
    try:
        message_type = message.get("type")
        data = message.get("data", {})

        if message_type == "subscribe_ticker":
            symbol = data.get("symbol")
            if symbol:
                # Subscribe to ticker updates
                def ticker_callback(ticker_data):
                    asyncio.create_task(manager.send_personal_message(ticker_data, connection_id))

                websocket_manager.binance_ws.subscribe_ticker(symbol, ticker_callback)

                # Send confirmation
                await manager.send_personal_message({
                    "type": "subscription_confirmed",
                    "data": {"stream": "ticker", "symbol": symbol}
                }, connection_id)

        elif message_type == "subscribe_kline":
            symbol = data.get("symbol")
            interval = data.get("interval", "1m")
            if symbol:
                # Subscribe to kline updates
                def kline_callback(kline_data):
                    asyncio.create_task(manager.send_personal_message(kline_data, connection_id))

                websocket_manager.binance_ws.subscribe_kline(symbol, interval, kline_callback)

                # Send confirmation
                await manager.send_personal_message({
                    "type": "subscription_confirmed",
                    "data": {"stream": "kline", "symbol": symbol, "interval": interval}
                }, connection_id)

        elif message_type == "subscribe_depth":
            symbol = data.get("symbol")
            if symbol:
                # Subscribe to order book depth updates
                def depth_callback(depth_data):
                    asyncio.create_task(manager.send_personal_message(depth_data, connection_id))

                websocket_manager.binance_ws.subscribe_depth(symbol, depth_callback)

                # Send confirmation
                await manager.send_personal_message({
                    "type": "subscription_confirmed",
                    "data": {"stream": "depth", "symbol": symbol}
                }, connection_id)

        elif message_type == "unsubscribe":
            stream_name = data.get("stream")
            if stream_name:
                # Note: Unsubscribe logic would need to be implemented
                # This is a simplified version
                await manager.send_personal_message({
                    "type": "unsubscription_confirmed",
                    "data": {"stream": stream_name}
                }, connection_id)

        elif message_type == "ping":
            # Respond to ping with pong
            await manager.send_personal_message({
                "type": "pong",
                "timestamp": message.get("timestamp")
            }, connection_id)

        else:
            # Unknown message type
            await manager.send_personal_message({
                "type": "error",
                "message": f"Unknown message type: {message_type}"
            }, connection_id)

    except Exception as e:
        logger.error(f"Error handling WebSocket message: {e}")
        await manager.send_personal_message({
            "type": "error",
            "message": "Error processing message"
        }, connection_id)


@router.get("/ws/status")
async def websocket_status():
    """Get WebSocket connection status"""
    return {
        "active_connections": len(manager.active_connections),
        "binance_ws_running": websocket_manager.binance_ws.is_running,
        "active_streams": list(websocket_manager.binance_ws.active_streams.keys())
    }