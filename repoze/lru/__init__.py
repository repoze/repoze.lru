""" LRU caching class and decorator """

import threading

_marker = object()

class LRUCache(object):
    def __init__(self, size):
        """ Implements a psueudo-LRU algorithm (CLOCK) """
        if size < 1:
            raise ValueError('size must be >1')
        self.size = size
        self.lock = threading.Lock()
        self.clear()

    def clear(self):
        self.lock.acquire()
        try:
            size = self.size
            self.clock = []
            for i in xrange(0, size):
                self.clock.append({'key':_marker, 'ref':False})
            self.maxpos = size - 1
            self.hand = 0
            self.data = {}
        finally:
            self.lock.release()

    def get(self, key, default=None):
        try:
            datum = self.data[key]
        except KeyError:
            return default
        pos, val = datum
        self.clock[pos]['ref'] = True
        hand = pos + 1
        if hand > self.maxpos:
            hand = 0
        self.hand = hand
        return val

    def put(self, key, val, _marker=_marker):
        hand = self.hand
        maxpos = self.maxpos
        clock = self.clock
        data = self.data
        lock = self.lock

        end = hand - 1
        if end < 0:
            end = maxpos

        while 1:
            current = clock[hand]
            ref = current['ref']
            if ref is True:
                current['ref'] = False
                hand = hand + 1
                if hand > maxpos:
                    hand = 0
            elif ref is False or hand == end:
                lock.acquire()
                try:
                    oldkey = current['key']
                    if oldkey in data:
                        del data[oldkey]
                    current['key'] = key
                    current['ref'] = True
                    data[key] = (hand, val)
                    hand += 1
                    if hand > maxpos:
                        hand = 0
                    self.hand = hand
                finally:
                    lock.release()
                break

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
