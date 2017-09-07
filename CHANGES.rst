Changelog
=========

0.8 (unreleased)
----------------

- TBD

0.7 (2017-09-06)
----------------

- Add ``CacheMaker.memoize`` to create named, unbounded caches.

- Add ``UnboundedCache``, backed by a dict.

- Add an ``ignore_unhashable_args`` option to ``lru_cache``:  if True, the
  cache will discard arguments which cannot be hashed, rather than raising
  a ``TypeError``.

- Expose cache object on the wrapped function, e.g. to allow extracting cache
  performance data easily (PR #20).

- Avoid crash when memoizing a ``functools.partial`` instance (PR #21).

- Add explicit support for Python3.4, 3.5, and 3.6.

- Drop support for Python 2.6 and 3.2.

0.6 (2012-07-12)
----------------

- Added a ``CacheMaker`` helper class:  a maker keeps references (by name)
  to the caches it creates, to permit them to be cleared.

- Added statistics to each cache, tracking lookups, hits, misses, and
  evictions.

- Automated building Sphinx docs and testing example snippets under ``tox``.

- Added Sphinx documentation.

- Dropped support for Python 2.5.

- Added support for PyPy.

- Added ``setup.py docs`` alias (installs ``Sphinx`` and dependencies).

- Added ``setup.py dev`` alias (runs ``develop`` plus installs ``nose``
  and ``coverage``).

- Added support for CI under supported Pythons using ``tox``.

- Bug: Remove potential race condition on lock in face of interrupts
  (Issue #10).

0.5 (2012-03-24)
----------------

- Feature: added a new "invalidate()" method to allow removal of items from
  the cache (issue #8).

- Bug: LRUCache.put() could take multiple seconds on large caches (Issue #7).

- Bug: LRUCache was not thread safe (Issue #6).

- Bug: LRUCache.clock would waste RAM (Issue #4).

- Bug: repeated pushing of an entry would remove other cache entries
  (Issue #3).

- Bug: LRUCache would evict entries even when not full (Issue #2).

0.4 (2011-09-04)
----------------

- Moved to GitHub (https://github.com/repoze/repoze.lru).

- Added Python 3.2 support.

- Python 2.4 no longer supported.

- Added tox.ini for easier testing.

0.3 (2009/06/16)
----------------

- Add a thread lock around ``clear`` logic.

0.2 (2009/06/15)
----------------

- Add a ``clear`` method.

0.1 (2009/06/14)
----------------

- Initial release.
