repoze.lru
==========

``repoze.lru`` is a LRU (least recently used) cache implementation.  Keys and
values that are not used frequently will be evicted from the cache faster
than keys and values that are used frequently.  It works under Python 2.5,
Python 2.6, Python 2.7, and Python 3.2.

API
---

Creating an LRUCache object::

  from repoze.lru import LRUCache
  cache = LRUCache(100) # 100 max length

Retrieving from an LRUCache object::

  cache.get('nonexisting', 'foo') # will return 'foo'
  cache.get('nonexisting') # will return None
  cache.get('existing') # will return the value for existing

Adding to an LRUCache object::

  cache.put('key', 'value') # will add the key 'key' with the value 'value'

Clearing an LRUCache::

  cache.clear()

Obtaining cache statistics:

  cache.lookups     # number of calls to the get method
  cache.hits        # number of times a call to get found an object
  cache.misses      # number of times a call to get did not find an object
  cahce.evictions   # number of times a object was evicted from cache

Decorator
---------

A ``lru_cache`` decorator exists.  All values passed to the decorated
function must be hashable.  It does not support keyword arguments::

   from repoze.lru import lru_cache

   @lru_cache(500)
   def expensive_function(*arg):
       pass

Each function decorated with the lru_cache decorator uses its own
cache related to that function.
