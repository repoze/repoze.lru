Using :mod:`repoze.lru`
======================

``repoze.lru`` is a LRU (least recently used) cache implementation.  Keys and
values that are not used frequently will be evicted from the cache faster
than keys and values that are used frequently.  It works under Python 2.5,
Python 2.6, Python 2.7, and Python 3.2.

Using the API programmatically
------------------------------

Creating an LRUCache object:

.. doctest::

   >>> from repoze.lru import LRUCache
   >>> cache = LRUCache(100) # 100 max length

Retrieving from an LRUCache object:

.. doctest::

   >>> cache.get('nonexisting', 'foo') # return 'foo'
   'foo'
   >>> cache.get('nonexisting') is None
   True

Adding to an LRUCache object:

.. doctest::

   >>> cache.put('existing', 'value') # add the key 'key' with the value 'value'
   >>> cache.get('existing') # return the value for existing
   'value'

Clearing an LRUCache:

.. doctest::

   >>> cache.clear()


Decorating an "expensive" function call
---------------------------------------

:mod:`repoze.lru` provides a class :class:`~repoze.lru.lru_cache`, which
wrapps another callable, caching the results.  All values passed to the
decorated function must be hashable.  It does not support keyword arguments:

.. doctest::

   >>> from repoze.lru import lru_cache
   >>> @lru_cache(500)
   ... def expensive_function(*arg): #*
   ...     pass

Each function decorated with the lru_cache decorator uses its own
cache related to that function.
