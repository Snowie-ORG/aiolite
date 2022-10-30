"""
Pooling realization by aiosqlite lib
"""
from typing import Tuple, List, Dict, Any, Optional
from asyncio import Event, Lock
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
    def __init__(self, *connection_args, minsize: int = None, maxsize: int = None,
                 **connection_kwargs):
        """
        minsize arg (int, minsize > 0) is a minimal count of connections
        maxsize arg (int, maxsize > 0) is a maximal count of connections
        """
        assert isinstance(minsize, int) and minsize > 0, \
        "minsize (int value) must be greater than 0"
        assert isinstance(maxsize, int) and maxsize > 0 and minsize <= maxsize, \
        "maxsize (int value) must be greater than 0 and >= minsize"

        connection_url = None
        if len(connection_args) > 0:
            connection_url = connection_args[0]
        elif connection_kwargs.get('database'):
            connection_url = connection_kwargs['database']
        if connection_url == ":memory:":
            assert (minsize is None and maxsize is None) or (minsize == 1 and maxsize == 1), \
            "Can't use minsize != 1 and maxsize != 1 with :memory:"
            minsize = 1
            maxsize = 1
        else:
            minsize = 1
            maxsize = 10
        self._minsize: int = minsize
        self._maxsize: int = maxsize
        self._connections: List[aiosqlite.Connection] = []
        self._free: List[aiosqlite.Connection] = []
        self._connection_args: Tuple[Any, ...] = connection_args
        self._connection_kwargs: Dict[str, Any] = connection_kwargs
        self._release_event: Event = Event()
        self._lock: Lock = Lock()
        self._is_initialized: bool = False
        self._is_closing = False

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
        assert self.size == 0
        for _ in range(self.minsize):
            self._free.append(
                await aiosqlite.connect(*self._connection_args, **self._connection_kwargs)
            )
        self._is_initialized = True

    async def close(self, immediately=False):
        """close all pool connections"""
        assert self._is_initialized, "Pool has been closed"
        self._is_closing = True
        await self._lock.acquire()
        for connection in self._free:
            await connection.close()
        self._free = []
        if immediately:
            for connection in self._connections:
                await connection.close()
        else:
            while len(self._connections) > 0:
                if self._lock.locked():
                    self._lock.release()
                await self._release_event.wait()
                await self._lock.acquire()
        self._connections = []
        self._is_initialized = False
        self._is_closing = False
        self._lock.release()
        self._release_event.set()

    def acquire(self) -> PoolAcquireWrapper:
        """create acquire wrapper"""
        return PoolAcquireWrapper(self)

    async def _acquire(self) -> aiosqlite.Connection:
        """acquire connection if pool has size for it"""
        assert self._is_initialized or not self._is_closing, "Pool has been closed"
        await self._lock.acquire()
        if len(self._connections) >= self.maxsize:
            self._lock.release()
            await self._release_event.wait()
        else:
            self._lock.release()
        assert self._is_initialized or not self._is_closing, "Pool has been closed"
        connection = None
        async with self._lock:
            if len(self._free) > 0:
                connection = self._free.pop()
            else:
                connection = await aiosqlite.connect(*self._connection_args,
                                                     **self._connection_kwargs)
            self._connections.append(connection)
        return connection

    async def release(self, connection: aiosqlite.Connection):
        """kill connection and delete it from pool"""
        assert self._is_initialized
        assert connection in self._connections, \
        "unknown connection"
        async with self._lock:
            if len(self._free) < self.minsize and not self._is_closing:
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
        