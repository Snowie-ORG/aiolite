"""
Pooling realization by aiosqlite lib
"""
from typing import Tuple, List, Dict, Any, Optional
from asyncio import Event
import aiosqlite


class PoolAcquireWrapper:
    """
    Wrapper class that allows you to access connection
    from with statement
    """
    def __init__(self, pool: "Pool"):
        assert isinstance(pool, Pool)
        self._pool: Pool = pool
        self.connection: Optional[aiosqlite.Connection] = None

    def __await__(self):
        return self._pool._acquire().__await__()

    async def __aenter__(self, *args, **kwargs) -> aiosqlite.Connection:
        self.connection = await self._pool._acquire()
        return self.connection

    async def __aexit__(self, *args, **kwargs):
        assert self.connection is not None
        await self._pool.release(self.connection)


class Pool:
    """
    Pool realization
    """
    def __init__(self, *connection_args, minsize: int = 1, maxsize: int = 10, **connection_kwargs):
        """
        minsize arg (int, minsize > 0) is a minimal count of connections
        maxsize arg (int, maxsize > 0) is a maximal count of connections
        """
        assert isinstance(minsize, int) and minsize > 0, \
        "minsize (int value) must be greater than 0"
        assert isinstance(maxsize, int) and maxsize > 0 and minsize <= maxsize, \
        "maxsize (int value) must be greater than 0 and >= minsize"
        self._minsize: int = minsize
        self._maxsize: int = maxsize
        self._connections: List[aiosqlite.Connection] = []
        self._free: List[aiosqlite.Connection] = []
        self._connection_args: Tuple[Any, ...] = connection_args
        self._connection_kwargs: Dict[str, Any] = connection_kwargs
        self._release_event: Event = Event()
        self._is_initialized: bool = False

    @property
    def minsize(self):
        """make private minsize property"""
        return self._minsize

    @property
    def maxsize(self):
        """make maxsize minsize property"""
        return self._maxsize

    @property
    def size(self):
        """property that counts pool connectionsn"""
        return len(self._connections) + len(self._free)

    async def init(self):
        """inits pool with given parameters"""
        await self.fill_free_pool()
        self._is_initialized = True

    async def close(self):
        """close all pool connections"""
        for connection in self._connections + self._free:
            await connection.close()
        self._connections = []
        self._free = []
        self._is_initialized = False
        self._release_event.set()

    def acquire(self) -> PoolAcquireWrapper:
        """create acquire wrapper"""
        return PoolAcquireWrapper(self)

    async def _acquire(self) -> aiosqlite.Connection:
        """acquire connection if pool has size for it"""
        assert self._is_initialized
        if len(self._connections) >= self._maxsize:
            await self._release_event.wait()
        assert self._is_initialized
        connection = None
        if len(self._free) > 0:
            connection = self._free.pop()
        else:
            connection = await aiosqlite.connect(*self._connection_args, **self._connection_kwargs)
        self._connections.append(connection)
        return connection

    async def fill_free_pool(self):
        """fill free pool with minsize connections"""
        free_fill_count = self.minsize - self.size
        if free_fill_count < 1 or self.size >= self.maxsize:
            return
        for _ in range(free_fill_count):
            self._free.append(
                await aiosqlite.connect(*self._connection_args, **self._connection_kwargs)
            )

    async def release(self, connection: aiosqlite.Connection):
        """kill connection and delete it from pool"""
        assert self._is_initialized
        assert connection in self._connections, \
        "unknown connection"
        if len(self._free) < self.minsize:
            await connection.rollback()
            self._free.append(connection)
        else:
            await connection.close()
        self._connections.remove(connection)
        self._release_event.set()


async def create_pool(*connection_args, minsize: int = 1, maxsize: int = 10,
                      **connection_kwargs):
    """create and init pool"""
    pool_instance = Pool(minsize=minsize, maxsize=maxsize, *connection_args, **connection_kwargs)
    await pool_instance.init()
    return pool_instance
        