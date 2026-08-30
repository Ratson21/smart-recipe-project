from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings


class _MongoDB:
    client: AsyncIOMotorClient | None = None
    db: AsyncIOMotorDatabase | None = None

    async def connect(self) -> None:
        self.client = AsyncIOMotorClient(settings.mongodb_url)
        self.db = self.client[settings.database_name]
        # Lightweight ping to verify the connection at startup
        await self.client.admin.command("ping")

    async def close(self) -> None:
        if self.client:
            self.client.close()
            self.client = None
            self.db = None


mongodb = _MongoDB()


def get_db() -> AsyncIOMotorDatabase:
    """FastAPI dependency - returns the active database handle."""
    return mongodb.db
