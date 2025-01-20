from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from models import Base, Users

# Create a SQLAlchemy engine
DATABASE_URL = "postgresql+asyncpg://postgres:postgres@postgres_container:5432/postgres"
engine = create_async_engine(DATABASE_URL, echo=True)


async_session = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        async with session.begin():
            session.add(Users(user_id=1, api_key="test", name="John"))
            session.add(Users(user_id=2, api_key="test2", name="Alice"))
        await session.commit()
