from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.config.settings import Settings


def create_database_engine(settings: Settings) -> AsyncEngine:
    if not settings.database_url:
        raise ValueError("DATABASE_URL is required for direct PostgreSQL access")
    url = settings.database_url
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return create_async_engine(url, pool_pre_ping=True)
