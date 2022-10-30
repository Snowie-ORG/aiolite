"""
fixture for autocreating memory aiosqlite pool
"""
import pytest
from asyncsqlite.pool import Pool, create_pool

@pytest.fixture
def create_memory_pool() -> Pool:
    """fixture func that returns func that creates pool"""
    async def memory_pool_creator():
        return await create_pool(":memory:", minsize=1, maxsize=1)
    return memory_pool_creator
