import os
from pydantic import BaseModel


class Settings(BaseModel):
    """
    Application configuration settings.
    Uses environment variables with sensible defaults.
    """
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "SubLedger - SaaS Subscription & Billing System")
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # SQLite default; can be overridden by PostgreSQL URL: postgresql://user:password@localhost/subledger
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./subledger.db")
    
    # For SQLite concurrency handling
    DB_ECHO: bool = os.getenv("DB_ECHO", "False").lower() in ("true", "1", "yes")


settings = Settings()
