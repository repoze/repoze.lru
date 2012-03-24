""" LRU caching class and decorator """
from __future__ import with_statement

import threading
import time

try:
    range = xrange
except NameError: # pragma: no cover
    pass

_MARKER = object()
# By default, expire items after 2**60 seconds. This fits into 64 bit
# integers and is close enough to "never" for practical purposes.
_DEFAULT_TIMEOUT = 2 ** 60

class LRUCache(object):
    """ Implements a pseudo-LRU algorithm (CLOCK)

    The Clock algorithm is not kept strictly to improve performance, e.g. to
    allow get() and invalidate() to work without acquiring the lock.
    """
    def __init__(self, size):
        size = int(size)
        if size < 1:
            raise ValueError('size must be >0')
        self.size = size
        self.lock = threading.Lock()
        self.hand = 0
        self.maxpos = size - 1
        self.clock_keys = None
        self.clock_refs = None
        self.data = None
        self.clear()

    def clear(self):
        """Remove all entries from the cache"""
        with self.lock:
            # If really clear()ing a full cache, clean up self.data first to
            # give garbage collection a chance to reduce memorey usage.
            # Instantiating "[_MARKER] * size" will temporarily have 2 lists
            # in memory -> high peak memory usage for tiny amount of time.
            # With self.data already clear, that peak should not exceed what
            # we normally use.
            self.data = {}
            size = self.size
            self.clock_keys = [_MARKER] * size
            self.clock_refs = [False] * size
            self.hand = 0

    def get(self, key, default=None):
        """Return value for key. If not in cache, return default"""
        try:
            pos, val = self.data[key]
        except KeyError:
            return default
        self.clock_refs[pos] = True
        return val

    def put(self, key, val):
        """Add key to the cache with value val"""
        # These do not change or they are just references, no need for locking.
        maxpos = self.maxpos
        clock_refs = self.clock_refs
        clock_keys = self.clock_keys
        data = self.data

        with self.lock:
            entry = data.get(key)
            if entry is not None:
                # We already have key. Only make sure data is up to date and
                # to remember that it was used.
                pos, old_val = entry
                if old_val is not val:
                    data[key] = (pos, val)
                self.clock_refs[pos] = True
                return
            # else: key is not yet in cache. Search place to insert it.

            hand = self.hand
            count = 0
            max_count = 107
            while 1:
                ref = clock_refs[hand]
                if ref == True:
                    clock_refs[hand] = False
                    hand += 1
                    if hand > maxpos:
                        hand = 0

                    count += 1
                    if count >= max_count:
                        # We have been searching long enough. Force eviction of
                        # next entry, no matter what its status is.
                        clock_refs[hand] = False
                else:
                    oldkey = clock_keys[hand]
                    # Maybe oldkey was not in self.data to begin with. If it
                    # was, self.invalidate() in another thread might have
                    # already removed it. del() would raise KeyError, so pop().
                    data.pop(oldkey, None)
                    clock_keys[hand] = key
                    clock_refs[hand] = True
                    data[key] = (hand, val)
                    hand += 1
                    if hand > maxpos:
                        hand = 0
                    self.hand = hand
                    break

    def invalidate(self, key):
        """Remove key from the cache"""
        # pop with default arg will not raise KeyError
        entry = self.data.pop(key, _MARKER)
        if entry is not _MARKER:
            # We have no lock, but worst thing that can happen is that we
            # set another key's entry to False.
            self.clock_refs[entry[0]] = False
        # else: key was not in cache. Nothing to do.


class ExpiringLRUCache(object):
    """ Implements a pseudo-LRU algorithm (CLOCK) with expiration times

    The Clock algorithm is not kept strictly to improve performance, e.g. to
    allow get() and invalidate() to work without acquiring the lock.
    """
    def __init__(self, size, default_timeout=_DEFAULT_TIMEOUT):
        self.default_timeout = default_timeout
        size = int(size)
        if size < 1:
            raise ValueError('size must be >0')
        self.size = size
        self.lock = threading.Lock()
        self.hand = 0
        self.maxpos = size - 1
        self.clock_keys = None
        self.clock_refs = None
        self.data = None
        self.clear()

    def clear(self):
        """Remove all entries from the cache"""
        with self.lock:
            # If really clear()ing a full cache, clean up self.data first to
            # give garbage collection a chance to reduce memorey usage.
            # Instantiating "[_MARKER] * size" will temporarily have 2 lists
            # in memory -> high peak memory usage for tiny amount of time.
            # With self.data already clear, that peak should not exceed what
            # we normally use.
            # self.data contains (pos, val, expires) triplets
            self.data = {}
            size = self.size
            self.clock_keys = [_MARKER] * size
            self.clock_refs = [False] * size
            self.hand = 0

    def get(self, key, default=None):
        """Return value for key. If not in cache or expired, return default"""
        try:
            pos, val, expires = self.data[key]
        except KeyError:
            return default
        if expires > time.time():
            # cache entry still valid
            self.clock_refs[pos] = True
            return val
        else:
            # cache entry has expired. Make sure the space in the cache can
            # be recycled soon.
            self.clock_refs[pos] = False
            return default

    def put(self, key, val, timeout=None):
        """Add key to the cache with value val

        key will expire in $timeout seconds. If key is already in cache, val
        and timeout will be updated.
        """
        # These do not change or they are just references, no need for locking.
        maxpos = self.maxpos
        clock_refs = self.clock_refs
        clock_keys = self.clock_keys
        data = self.data
        lock = self.lock
        if timeout is None:
            timeout = self.default_timeout

        with self.lock:
            entry = data.get(key)
            if entry is not None:
                # We already have key. Only make sure data is up to date and
                # to remember that it was used.
                pos = entry[0]
                data[key] = (pos, val, time.time() + timeout)
                clock_refs[pos] = True
                return
            # else: key is not yet in cache. Search place to insert it.

            hand = self.hand
            count = 0
            max_count = 107
            while 1:
                ref = clock_refs[hand]
                if ref == True:
                    clock_refs[hand] = False
                    hand += 1
                    if hand > maxpos:
                        hand = 0

                    count += 1
                    if count >= max_count:
                        # We have been searching long enough. Force eviction of
                        # next entry, no matter what its status is.
                        clock_refs[hand] = False
                else:
                    oldkey = clock_keys[hand]
                    # Maybe oldkey was not in self.data to begin with. If it
                    # was, self.invalidate() in another thread might have
                    # already removed it. del() would raise KeyError, so pop().
                    data.pop(oldkey, None)
                    clock_keys[hand] = key
                    clock_refs[hand] = True
                    data[key] = (hand, val, time.time() + timeout)
                    hand += 1
                    if hand > maxpos:
                        hand = 0
                    self.hand = hand
                    break

    def invalidate(self, key):
        """Remove key from the cache"""
        # pop with default arg will not raise KeyError
        entry = self.data.pop(key, _MARKER)
        if entry is not _MARKER:
            # We have no lock, but worst thing that can happen is that we
            # set another key's entry to False.
            self.clock_refs[entry[0]] = False
        # else: key was not in cache. Nothing to do.

class lru_cache(object):
    """ Decorator for LRU-cached function

    timeout parameter specifies after how many seconds a cached entry should
    be considered invalid.
    """
    def __init__(self, maxsize, cache=None, timeout=None): # cache is an arg to serve tests
        if cache is None:
            if timeout is None:
                cache = LRUCache(maxsize)
            else:
                cache = ExpiringLRUCache(maxsize, default_timeout=timeout)
        self.cache = cache

    def __call__(self, f):
        cache = self.cache
        marker = _MARKER
        def lru_cached(*arg):
            val = cache.get(arg, marker)
            if val is marker:
                val = f(*arg)
                cache.put(arg, val)
            return val
        lru_cached.__module__ = f.__module__
        lru_cached.__name__ = f.__name__
        lru_cached.__doc__ = f.__doc__
        return lru_cached
