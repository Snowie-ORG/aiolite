#pylint: disable=C0116, W0212
"""
tests of pool functional
"""
import pytest

CREATE_TABLE_SQL = """ CREATE TABLE EXAMPLE (
            Email VARCHAR(255) NOT NULL,
            First_Name CHAR(25) NOT NULL,
            Last_Name CHAR(25),
            Score INT
        ); """
SELECT_SQL = "SELECT * FROM EXAMPLE"

@pytest.mark.asyncio
@pytest.mark.usefixtures("create_memory_pool")
async def test_initialization(create_memory_pool):
    pool = await create_memory_pool()
    assert pool.size == 1
    assert len(pool._connections) == 0
    assert len(pool._free) == 1
    await pool.close()

@pytest.mark.asyncio
@pytest.mark.usefixtures("create_memory_pool")
async def test_acquiring(create_memory_pool):
    pool = await create_memory_pool()
    conn = await pool.acquire()
    assert pool.size == 1
    assert len(pool._connections) == 1
    assert len(pool._free) == 0
    cursor = await conn.cursor()
    await cursor.execute(CREATE_TABLE_SQL)
    cursor = await cursor.execute(SELECT_SQL)
    rows = await cursor.fetchall()
    assert len(rows) == 0
    await cursor.close()
    await pool.close(immediately=True)

@pytest.mark.asyncio
@pytest.mark.usefixtures("create_memory_pool")
async def test_acquiring_with(create_memory_pool):
    pool = await create_memory_pool()
    async with pool.acquire() as conn:
        assert pool.size == 1
        assert len(pool._connections) == 1
        assert len(pool._free) == 0
        cursor = await conn.cursor()
        await cursor.execute(CREATE_TABLE_SQL)
        rows = await cursor.fetchall()
        assert len(rows) == 0
        await cursor.close()
    async with pool.acquire() as conn:
        assert pool.size == 1
        assert len(pool._connections) == 1
        assert len(pool._free) == 0
        cursor = await conn.cursor()
        cursor = await cursor.execute(SELECT_SQL)
        rows = await cursor.fetchall()
        assert len(rows) == 0
        await cursor.close()
    await pool.close()

@pytest.mark.asyncio
@pytest.mark.usefixtures("create_memory_pool")
async def test_acquiring_many(create_memory_pool):
    pool = await create_memory_pool()
    conn = await pool.acquire()
    assert pool.size == 1
    assert len(pool._connections) == 1
    assert len(pool._free) == 0
    cursor = await conn.cursor()
    await cursor.execute(CREATE_TABLE_SQL)
    cursor = await cursor.execute(SELECT_SQL)
    rows = await cursor.fetchall()
    assert len(rows) == 0
    await cursor.close()
    await pool.release(conn)
    await pool.close()
