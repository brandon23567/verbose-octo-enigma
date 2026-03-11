from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from dotenv import load_dotenv
import os 
from sqlalchemy.orm import declarative_base
from typing import AsyncGenerator

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("Unable to fetch the database url")


engine = create_async_engine(
    DATABASE_URL, 
    pool_pre_ping=True,
    connect_args = {
        "ssl": "require"
    }
)

Base = declarative_base()

LocalAsyncSession = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autoflush=False,
    expire_on_commit=False
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with LocalAsyncSession() as db:
        yield db 