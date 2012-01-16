""" LRU caching class and decorator """

import threading

try:
    range = xrange
except NameError: # pragma: no cover
    pass

_marker = object()

class LRUCache(object):
    def __init__(self, size):
        """ Implements a psueudo-LRU algorithm (CLOCK) """
        if size < 1:
            raise ValueError('size must be >1')
        self.size = size
        self.lock = threading.Lock()
        self.hand = 0
        self.maxpos = size - 1
        self.clock_keys = None
        self.clock_refs = None
        self.data = None
        self.clear()

    def clear(self):
        self.lock.acquire()
        try:
            # If really clear()ing a full cache, clean up self.data first to
            # give garbage collection a chance to reduce memorey usage.
            # Instantiating "[_marker] * size" will temporarily have 2 lists
            # in memory -> high peak memory usage for tiny amount of time.
            # With self.data already clear, that peak should not exceed what
            # we normally use.
            self.data = {}
            size = self.size
            self.clock_keys = [_marker] * size
            self.clock_refs = [False] * size
            self.hand = 0
        finally:
            self.lock.release()

    def get(self, key, default=None):
        try:
            pos, val = self.data[key]
        except KeyError:
            return default
        self.clock_refs[pos] = True
        return val

    def put(self, key, val, _marker=_marker):
        # These do not change or they are just references, no need for locking.
        maxpos = self.maxpos
        clock_refs = self.clock_refs
        clock_keys = self.clock_keys
        data = self.data
        lock = self.lock

        lock.acquire()
        try:
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
        finally:
            lock.release()

    def invalidate(self, key):
        """Remove key from the cache"""
        # pop with default arg will not raise KeyError
        entry = self.data.pop(key, _marker)
        if entry is not _marker:
            # We have no lock, but worst thing that can happen is that we
            # set another key's entry to False.
            self.clock_refs[entry[0]] = False
        # else: key was not in cache. Nothing to do.

class lru_cache(object):
    """ Decorator for LRU-cached function """
    def __init__(self, maxsize, cache=None): # cache is an arg to serve tests
        if cache is None:
            cache = LRUCache(maxsize)
        self.cache = cache

    def __call__(self, f):
        cache = self.cache
        marker = _marker
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
