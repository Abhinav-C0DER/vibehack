import socketio

# Upgrade your initializer to accept connections from the frontend port
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*"  # Allows local cross-origin connections from port 3000
)

# The rest of your ASGI app wrapping follows below (e.g. socketio.ASGIApp...)
