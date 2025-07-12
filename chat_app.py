
"""
Real-Time Chat Application Backend
WebSocket server using asyncio and websockets library
"""

import asyncio
import websockets
import json
import logging
from datetime import datetime
from typing import Dict, Set
import signal
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ChatServer:
    def __init__(self):
        # Store connected clients: websocket -> user_info
        self.clients: Dict[websockets.WebSocketServerProtocol, dict] = {}
        # Store usernames to prevent duplicates
        self.usernames: Set[str] = set()
        
    async def register_client(self, websocket, username):
        """Register a new client"""
        if username in self.usernames:
            await self.send_error(websocket, "Username already taken")
            return False
            
        user_info = {
            'username': username,
            'joined_at': datetime.now().isoformat(),
            'typing': False
        }
        
        self.clients[websocket] = user_info
        self.usernames.add(username)
        
        logger.info(f"User '{username}' joined the chat")
        
        # Notify all clients about new user
        await self.broadcast_message({
            'type': 'join',
            'username': username,
            'timestamp': datetime.now().isoformat()
        })
        
        # Send updated user count
        await self.broadcast_user_count()
        return True
        
    async def unregister_client(self, websocket):
        """Unregister a client"""
        if websocket in self.clients:
            username = self.clients[websocket]['username']
            del self.clients[websocket]
            self.usernames.discard(username)
            
            logger.info(f"User '{username}' left the chat")
            
            # Notify all clients about user leaving
            await self.broadcast_message({
                'type': 'leave',
                'username': username,
                'timestamp': datetime.now().isoformat()
            })
            
            # Send updated user count
            await self.broadcast_user_count()
    
    async def broadcast_message(self, message, exclude_sender=None):
        """Broadcast message to all connected clients"""
        if not self.clients:
            return
            
        # Convert message to JSON
        message_json = json.dumps(message)
        
        # Send to all clients except the sender
        disconnected_clients = []
        for websocket, user_info in self.clients.items():
            if websocket != exclude_sender:
                try:
                    await websocket.send(message_json)
                except websockets.exceptions.ConnectionClosed:
                    disconnected_clients.append(websocket)
                except Exception as e:
                    logger.error(f"Error sending message to {user_info['username']}: {e}")
                    disconnected_clients.append(websocket)
        
        # Clean up disconnected clients
        for websocket in disconnected_clients:
            await self.unregister_client(websocket)
    
    async def broadcast_user_count(self):
        """Broadcast current user count to all clients"""
        count_message = {
            'type': 'users_count',
            'count': len(self.clients),
            'timestamp': datetime.now().isoformat()
        }
        await self.broadcast_message(count_message)
    
    async def send_error(self, websocket, error_message):
        """Send error message to specific client"""
        error_msg = {
            'type': 'error',
            'message': error_message,
            'timestamp': datetime.now().isoformat()
        }
        try:
            await websocket.send(json.dumps(error_msg))
        except Exception as e:
            logger.error(f"Error sending error message: {e}")
    
    async def handle_message(self, websocket, message_data):
        """Handle incoming message from client"""
        try:
            message_type = message_data.get('type')
            
            if message_type == 'join':
                username = message_data.get('username', '').strip()
                if not username:
                    await self.send_error(websocket, "Username cannot be empty")
                    return
                    
                if len(username) > 20:
                    await self.send_error(websocket, "Username too long (max 20 characters)")
                    return
                    
                await self.register_client(websocket, username)
                
            elif message_type == 'message':
                if websocket not in self.clients:
                    await self.send_error(websocket, "Not registered")
                    return
                    
                content = message_data.get('content', '').strip()
                if not content:
                    return
                    
                if len(content) > 500:
                    await self.send_error(websocket, "Message too long (max 500 characters)")
                    return
                
                username = self.clients[websocket]['username']
                
                # Broadcast message to all clients
                broadcast_message = {
                    'type': 'message',
                    'username': username,
                    'content': content,
                    'timestamp': datetime.now().isoformat()
                }
                
                await self.broadcast_message(broadcast_message, exclude_sender=websocket)
                
                # Echo back to sender for confirmation
                await websocket.send(json.dumps(broadcast_message))
                
                logger.info(f"Message from {username}: {content[:50]}...")
                
            elif message_type == 'typing':
                if websocket not in self.clients:
                    return
                    
                username = self.clients[websocket]['username']
                typing_status = message_data.get('typing', False)
                
                self.clients[websocket]['typing'] = typing_status
                
                # Broadcast typing status to other clients
                typing_message = {
                    'type': 'typing',
                    'username': username,
                    'typing': typing_status,
                    'timestamp': datetime.now().isoformat()
                }
                
                await self.broadcast_message(typing_message, exclude_sender=websocket)
                
            else:
                await self.send_error(websocket, f"Unknown message type: {message_type}")
                
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await self.send_error(websocket, "Server error processing message")
    
    async def handle_client(self, websocket, path):
        """Handle individual client connection"""
        client_address = websocket.remote_address
        logger.info(f"New connection from {client_address}")
        
        try:
            async for message in websocket:
                try:
                    message_data = json.loads(message)
                    await self.handle_message(websocket, message_data)
                except json.JSONDecodeError:
                    await self.send_error(websocket, "Invalid JSON format")
                except Exception as e:
                    logger.error(f"Error processing message from {client_address}: {e}")
                    await self.send_error(websocket, "Error processing message")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Connection closed for {client_address}")
        except Exception as e:
            logger.error(f"Error handling client {client_address}: {e}")
        finally:
            await self.unregister_client(websocket)
    
    async def start_server(self, host='localhost', port=8765):
        """Start the WebSocket server"""
        logger.info(f"Starting chat server on {host}:{port}")
        
        # Create server
        server = await websockets.serve(
            self.handle_client,
            host,
            port,
            ping_interval=20,
            ping_timeout=10,
            close_timeout=10
        )
        
        logger.info(f"Chat server is running on ws://{host}:{port}")
        logger.info("Press Ctrl+C to stop the server")
        
        return server

# Global server instance
chat_server = ChatServer()

async def main():
    """Main function to run the server"""
    try:
        # Start the server
        server = await chat_server.start_server()
        
        # Handle graceful shutdown
        def signal_handler():
            logger.info("Received shutdown signal")
            server.close()
        
        # Register signal handlers
        for sig in [signal.SIGTERM, signal.SIGINT]:
            asyncio.get_event_loop().add_signal_handler(sig, signal_handler)
        
        # Keep the server running
        await server.wait_closed()
        
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
    finally:
        logger.info("Server shutdown complete")

if __name__ == "__main__":
    # Check if websockets library is available
    try:
        import websockets
    except ImportError:
        print("Error: websockets library not found!")
        print("Please install it with: pip install websockets")
        sys.exit(1)
    
    # Run the server
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)