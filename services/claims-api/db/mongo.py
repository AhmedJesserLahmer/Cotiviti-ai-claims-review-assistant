from motor.motor_asyncio import AsyncIOMotorClient

from core.config import settings

_client = AsyncIOMotorClient(settings.mongo_uri, serverSelectionTimeoutMS=5000)
db = _client[settings.mongo_db_name]
