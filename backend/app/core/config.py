from pydantic import BaseModel
import os
from dotenv import load_dotenv

# Load standard .env file if present
load_dotenv()

class Settings(BaseModel):
    # App Settings
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./vibehack.db")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your_super_secret_random_string_here")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    
    # Redis Settings
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))

settings = Settings()
