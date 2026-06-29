import json
from typing import List, Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status, Query
from app.core.auth import verify_token

router = APIRouter(prefix="/telemetry", tags=["Telemetry WebSockets"])

import redis.asyncio as aioredis

class ConnectionManager:
    """Manages active WebSockets connections to broadcast telemetry states."""
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"WebSocket client connected. Active pool size: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            print(f"WebSocket client disconnected. Active pool size: {len(self.active_connections)}")

    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket) -> None:
        await websocket.send_json(message)

    async def broadcast(self, message: Dict[str, Any]) -> None:
        """Broadcasts a JSON payload to all active clients globally via Redis Pub/Sub channel."""
        from app.config import settings
        try:
            redis_client = aioredis.from_url(settings.REDIS_URL)
            await redis_client.publish("uabe_telemetry_broadcast", json.dumps(message))
        except Exception as e:
            print(f"Error publishing telemetry to Redis Pub/Sub: {e}. Falling back to local broadcast.")
            await self.local_broadcast(message)

    async def local_broadcast(self, message: Dict[str, Any]) -> None:
        """Broadcasts JSON payload locally to clients connected to this worker node instance."""
        inactive_sockets = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"Error sending payload to websocket connection: {e}")
                inactive_sockets.append(connection)

        # Cleanup any dead sockets
        for dead_socket in inactive_sockets:
            self.disconnect(dead_socket)

manager = ConnectionManager()

async def redis_pubsub_listener():
    """
    Subscribes to the shared Redis Pub/Sub telemetry channel and broadcasts
    received events to all locally connected WebSocket clients.
    """
    from app.config import settings
    import asyncio
    print("[TELEMETRY] Starting Redis Pub/Sub telemetry listener task...")
    
    while True:
        try:
            redis_client = aioredis.from_url(settings.REDIS_URL)
            pubsub = redis_client.pubsub()
            await pubsub.subscribe("uabe_telemetry_broadcast", "uabe:registry:refresh")
            
            async for message in pubsub.listen():
                if message and message["type"] == "message":
                    try:
                        channel = message.get("channel")
                        if isinstance(channel, bytes):
                            channel = channel.decode("utf-8")
                            
                        if channel == "uabe:registry:refresh":
                            import importlib
                            importlib.invalidate_caches()
                            from app.services.sandbox_executor import sandbox_executor
                            sandbox_executor.clear_module_cache()
                            print("[HOT-RELOAD] Dynamic registry refresh intercepted. Invalidated importlib cache registers.")
                        else:
                            data = json.loads(message["data"])
                            await manager.local_broadcast(data)
                    except Exception as ex:
                        print(f"[TELEMETRY] Error parsing pubsub message: {ex}")
        except asyncio.CancelledError:
            print("[TELEMETRY] Redis Pub/Sub listener task cancelled.")
            break
        except Exception as e:
            print(f"[TELEMETRY] Redis connection lost ({e}). Retrying in 5s...")
            await asyncio.sleep(5)

@router.websocket("/ws")
async def telemetry_websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(None)
):
    """
    Secure WebSocket telemetry endpoint.
    Verifies JWT token string in query parameters before completing TCP upgrades.
    """
    # Handshake authentication check
    if not token:
        print("WebSocket Connection Rejected: Missing token query parameter.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    payload = verify_token(token)
    if not payload:
        print("WebSocket Connection Rejected: Token is invalid or has expired.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Accept connection and add to active client pool
    await manager.connect(websocket)
    
    try:
        # Welcome telemetry packet
        await manager.send_personal_message(
            {
                "event": "connected",
                "message": "Connected to UABE Core Telemetry Stream Engine",
                "role": payload.get("role", "operator")
            },
            websocket
        )
        
        # Keep-alive loop listening for client heartbeat frames
        while True:
            data = await websocket.receive_text()
            # If client sends a ping, echo pong back
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await manager.send_personal_message({"type": "pong"}, websocket)
            except Exception:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"Exception during WebSocket stream handler: {e}")
        manager.disconnect(websocket)
