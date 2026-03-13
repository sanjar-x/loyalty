import pytest
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine, async_sessionmaker
from tests.conftest import test_session_var
from dishka import AsyncContainer

@pytest.fixture(scope="function")
async def db_session(test_engine: AsyncEngine) -> AsyncSession:
    """
    Creates a nested transaction for each test. Everything committed within the
    test will be rolled back at the end, ensuring database purity and fast test execution.
    """
    async with test_engine.connect() as conn:
        transaction = await conn.begin()
        await conn.begin_nested()
        
        # Create a session bound to this connection
        maker = async_sessionmaker(
            bind=conn, 
            expire_on_commit=False, 
            join_transaction_mode="create_savepoint"
        )
        session = maker()
        
        # Set the contextvar so Dishka TestOverridesProvider injects THIS session
        token = test_session_var.set(session)
        
        yield session
        
        test_session_var.reset(token)
        
        await session.close()
        await transaction.rollback()
