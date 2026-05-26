import socketio
from app.api import auth, rooms, users
from app.sockets.server import sio
import app.sockets.connection  # Register connection/disconnection & join_room handlers
import app.sockets.chat        # Register messaging & whispering handlers
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.db.session import init_db
from app.api import auth

# This runs once when the server starts
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("👻 Waking up the ghosts... (Initializing DB)")
    init_db()
    yield
    print("⚰️ Server going to sleep...")

app = FastAPI(
    title="Vibehack API",
    description="The backend for the anonymous, reputation-based chat.",
    version="1.0.0",
    lifespan=lifespan
)

# Allow your friend's frontend (React/Next.js) to talk to this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Change this to the frontend URL before production!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connect the routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(rooms.router, prefix="/api/rooms", tags=["Rooms"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])

@app.get("/")
def read_root():
    return {"message": "Welcome to the Vibehack API. The ghosts are waiting."}
# Create the ASGI application that handles both HTTP and WebSockets
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)

# Overwrite or re-bind the primary routing instance for Uvicorn
app = socket_app
