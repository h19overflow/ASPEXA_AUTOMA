"""Database session factory for async SQLAlchemy."""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

Base = declarative_base()

engine = None
AsyncSessionLocal = None


def init_db(database_url: str):
    """Initialize the database connection."""
    global engine, AsyncSessionLocal
    
    engine = create_async_engine(
        database_url,
        echo=False,
        pool_pre_ping=True,
    )
    
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def get_session() -> AsyncSession:
    """Get a database session."""
    async with AsyncSessionLocal() as session:
        yield session
