repoze.lru
==========

``repoze.lru`` is a LRU (least recently used) cache implementation.
Keys and values that are not used frequently will be evicted from the
cache faster than keys and values that are used frequently.

API
---

Creating an LRUCache object:

.. code-block:: python

  from repoze.lru import LRUCache
  cache = LRUCache(100) # 100 max length

Retrieving from an LRUCache object:

.. code-block:: python

  cache.get('nonexisting', 'foo') # will return 'foo'
  cache.get('nonexisting') # will return None
  cache.get('existing') # will return the value for existing

Adding to an LRUCache object:

.. code-block:: python

  cache.put('key', 'value') # will add the key 'key' with the value 'value'


Decorator
---------

A ``lru_cached`` decorator exists.  All values passed to the decorated
function must be hashable.  It does not support keyword arguments.

.. code-block:: python

   from repoze.lru import lru_cache

   @lru_cache(500)
   def expensive_function(*arg):
       pass

Each function decorated with the lru_cache decorator uses its own
cache related to that function.


