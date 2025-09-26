"""
WebSocket service for real-time market data
"""

import json
import asyncio
import websockets
from typing import Dict, List, Set, Callable, Optional, Any
from binance import ThreadedWebsocketManager
import logging

logger = logging.getLogger(__name__)


class BinanceWebSocketManager:
    def __init__(self):
        self.twm: Optional[ThreadedWebsocketManager] = None
        self.active_streams: Dict[str, str] = {}  # stream_name -> socket_key
        self.subscribers: Dict[str, Set[Callable]] = {}  # stream_name -> set of callbacks
        self.is_running = False

    def start(self, testnet: bool = True):
        """Start the WebSocket manager"""
        try:
            self.twm = ThreadedWebsocketManager(testnet=testnet)
            self.twm.start()
            self.is_running = True
            logger.info(f"WebSocket manager started (testnet: {testnet})")
        except Exception as e:
            logger.error(f"Failed to start WebSocket manager: {e}")
            raise

    def stop(self):
        """Stop the WebSocket manager"""
        if self.twm:
            self.twm.stop()
            self.is_running = False
            self.active_streams.clear()
            self.subscribers.clear()
            logger.info("WebSocket manager stopped")

    def subscribe_ticker(self, symbol: str, callback: Callable[[Dict], None]):
        """Subscribe to ticker updates for a symbol"""
        stream_name = f"ticker_{symbol.lower()}"

        if stream_name not in self.subscribers:
            self.subscribers[stream_name] = set()

        self.subscribers[stream_name].add(callback)

        # Start stream if not already active
        if stream_name not in self.active_streams:
            try:
                socket_key = self.twm.start_symbol_ticker_socket(
                    callback=lambda msg: self._handle_ticker_message(stream_name, msg),
                    symbol=symbol
                )
                self.active_streams[stream_name] = socket_key
                logger.info(f"Started ticker stream for {symbol}")
            except Exception as e:
                logger.error(f"Failed to start ticker stream for {symbol}: {e}")

    def subscribe_kline(self, symbol: str, interval: str, callback: Callable[[Dict], None]):
        """Subscribe to kline/candlestick updates for a symbol"""
        stream_name = f"kline_{symbol.lower()}_{interval}"

        if stream_name not in self.subscribers:
            self.subscribers[stream_name] = set()

        self.subscribers[stream_name].add(callback)

        # Start stream if not already active
        if stream_name not in self.active_streams:
            try:
                socket_key = self.twm.start_kline_socket(
                    callback=lambda msg: self._handle_kline_message(stream_name, msg),
                    symbol=symbol,
                    interval=interval
                )
                self.active_streams[stream_name] = socket_key
                logger.info(f"Started kline stream for {symbol} {interval}")
            except Exception as e:
                logger.error(f"Failed to start kline stream for {symbol} {interval}: {e}")

    def subscribe_depth(self, symbol: str, callback: Callable[[Dict], None]):
        """Subscribe to order book depth updates for a symbol"""
        stream_name = f"depth_{symbol.lower()}"

        if stream_name not in self.subscribers:
            self.subscribers[stream_name] = set()

        self.subscribers[stream_name].add(callback)

        # Start stream if not already active
        if stream_name not in self.active_streams:
            try:
                socket_key = self.twm.start_depth_socket(
                    callback=lambda msg: self._handle_depth_message(stream_name, msg),
                    symbol=symbol
                )
                self.active_streams[stream_name] = socket_key
                logger.info(f"Started depth stream for {symbol}")
            except Exception as e:
                logger.error(f"Failed to start depth stream for {symbol}: {e}")

    def unsubscribe(self, stream_name: str, callback: Callable[[Dict], None]):
        """Unsubscribe a callback from a stream"""
        if stream_name in self.subscribers:
            self.subscribers[stream_name].discard(callback)

            # Stop stream if no more subscribers
            if not self.subscribers[stream_name] and stream_name in self.active_streams:
                try:
                    self.twm.stop_socket(self.active_streams[stream_name])
                    del self.active_streams[stream_name]
                    del self.subscribers[stream_name]
                    logger.info(f"Stopped stream {stream_name}")
                except Exception as e:
                    logger.error(f"Failed to stop stream {stream_name}: {e}")

    def _handle_ticker_message(self, stream_name: str, message: Dict[str, Any]):
        """Handle ticker message and notify subscribers"""
        try:
            # Process ticker data
            processed_data = {
                'stream': stream_name,
                'type': 'ticker',
                'data': {
                    'symbol': message.get('s'),
                    'price': float(message.get('c', 0)),
                    'price_change': float(message.get('P', 0)),
                    'price_change_percent': float(message.get('P', 0)),
                    'volume': float(message.get('v', 0)),
                    'high': float(message.get('h', 0)),
                    'low': float(message.get('l', 0)),
                    'timestamp': message.get('E')
                }
            }

            # Notify all subscribers
            if stream_name in self.subscribers:
                for callback in self.subscribers[stream_name]:
                    try:
                        callback(processed_data)
                    except Exception as e:
                        logger.error(f"Error in ticker callback: {e}")

        except Exception as e:
            logger.error(f"Error processing ticker message: {e}")

    def _handle_kline_message(self, stream_name: str, message: Dict[str, Any]):
        """Handle kline message and notify subscribers"""
        try:
            kline = message.get('k', {})
            processed_data = {
                'stream': stream_name,
                'type': 'kline',
                'data': {
                    'symbol': kline.get('s'),
                    'interval': kline.get('i'),
                    'open_time': kline.get('t'),
                    'close_time': kline.get('T'),
                    'open': float(kline.get('o', 0)),
                    'high': float(kline.get('h', 0)),
                    'low': float(kline.get('l', 0)),
                    'close': float(kline.get('c', 0)),
                    'volume': float(kline.get('v', 0)),
                    'is_closed': kline.get('x', False)
                }
            }

            # Notify all subscribers
            if stream_name in self.subscribers:
                for callback in self.subscribers[stream_name]:
                    try:
                        callback(processed_data)
                    except Exception as e:
                        logger.error(f"Error in kline callback: {e}")

        except Exception as e:
            logger.error(f"Error processing kline message: {e}")

    def _handle_depth_message(self, stream_name: str, message: Dict[str, Any]):
        """Handle depth message and notify subscribers"""
        try:
            processed_data = {
                'stream': stream_name,
                'type': 'depth',
                'data': {
                    'symbol': message.get('s'),
                    'bids': [[float(bid[0]), float(bid[1])] for bid in message.get('b', [])],
                    'asks': [[float(ask[0]), float(ask[1])] for ask in message.get('a', [])],
                    'timestamp': message.get('E')
                }
            }

            # Notify all subscribers
            if stream_name in self.subscribers:
                for callback in self.subscribers[stream_name]:
                    try:
                        callback(processed_data)
                    except Exception as e:
                        logger.error(f"Error in depth callback: {e}")

        except Exception as e:
            logger.error(f"Error processing depth message: {e}")


class WebSocketConnectionManager:
    def __init__(self):
        self.active_connections: List[websockets.WebSocketServerProtocol] = []
        self.binance_ws = BinanceWebSocketManager()

    async def connect(self, websocket: websockets.WebSocketServerProtocol):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connection established. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: websockets.WebSocketServerProtocol):
        """Remove a WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket connection closed. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: websockets.WebSocketServerProtocol):
        """Send a message to a specific WebSocket connection"""
        try:
            await websocket.send(message)
        except Exception as e:
            logger.error(f"Error sending message to websocket: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: str):
        """Broadcast a message to all connected WebSocket clients"""
        if self.active_connections:
            disconnected = []
            for connection in self.active_connections:
                try:
                    await connection.send(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to websocket: {e}")
                    disconnected.append(connection)

            # Remove disconnected clients
            for connection in disconnected:
                self.disconnect(connection)

    def start_binance_websocket(self, testnet: bool = True):
        """Start Binance WebSocket manager"""
        if not self.binance_ws.is_running:
            self.binance_ws.start(testnet)

    def stop_binance_websocket(self):
        """Stop Binance WebSocket manager"""
        if self.binance_ws.is_running:
            self.binance_ws.stop()

    def subscribe_to_ticker(self, symbol: str):
        """Subscribe to ticker updates and broadcast to all clients"""
        def ticker_callback(data):
            asyncio.create_task(self.broadcast(json.dumps(data)))

        self.binance_ws.subscribe_ticker(symbol, ticker_callback)

    def subscribe_to_kline(self, symbol: str, interval: str):
        """Subscribe to kline updates and broadcast to all clients"""
        def kline_callback(data):
            asyncio.create_task(self.broadcast(json.dumps(data)))

        self.binance_ws.subscribe_kline(symbol, interval, kline_callback)


# Global instance
websocket_manager = WebSocketConnectionManager()