from prisma import Prisma
from typing import Optional

# Global database instance
db: Optional[Prisma] = None

async def connect_db():
    """Connect to the database"""
    global db
    db = Prisma()
    await db.connect()
    print("Connected to database")

async def disconnect_db():
    """Disconnect from the database"""
    global db
    if db:
        await db.disconnect()
        print("Disconnected from database")

def get_db() -> Prisma:
    """Get the database instance"""
    if db is None:
        raise RuntimeError("Database not connected")
    return db
