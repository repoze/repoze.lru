import functools
import random
import time

import pytest

from repoze import lru


def test_unboundedcache_ctor():
    cache = lru.UnboundedCache()

    assert cache._data == {}


def test_unboundedcache_get_miss_no_default():
    cache = lru.UnboundedCache()

    assert cache.get("nonesuch") is None


def test_unboundedcache_get_miss_explicit_default():
    cache = lru.UnboundedCache()
    default = object()

    assert cache.get("nonesuch", default) is default


def test_unboundedcache_get_hit():
    cache = lru.UnboundedCache()
    extant = cache._data["extant"] = object()

    assert cache.get("extant") is extant


def test_unboundedcache_clear():
    cache = lru.UnboundedCache()
    _extant = cache._data["extant"] = object()

    cache.clear()

    assert cache.get("extant") is None


def test_unboundedcache_invalidate_miss():
    cache = lru.UnboundedCache()

    cache.invalidate("nonesuch")  # does not raise


def test_unboundedcache_invalidate_hit():
    cache = lru.UnboundedCache()
    _extant = cache._data["extant"] = object()

    cache.invalidate("extant")

    assert cache.get("extant") is None


def test_unboundedcache_put():
    cache = lru.UnboundedCache()
    extant = object()

    cache.put("extant", extant)

    assert cache._data["extant"] is extant


def check_lru_cache_is_consistent(cache):
    # Return if cache is consistent, else raise fail test case.
    # cache.hand/maxpos/size
    assert cache.hand < len(cache.clock_keys)
    assert cache.hand >= 0
    assert cache.maxpos == cache.size - 1
    assert len(cache.clock_keys) == cache.size

    # lengths of data structures
    assert len(cache.clock_keys) == len(cache.clock_refs)
    assert len(cache.data) <= len(cache.clock_refs)

    # For each item in cache.data
    #   1. pos must be a valid index
    #   2. clock_keys must point back to the entry
    for key, value in cache.data.items():
        pos, val = value
        assert type(pos) is int or type(pos) is type(2**128)
        assert pos >= 0
        assert pos <= cache.maxpos

        clock_key = cache.clock_keys[pos]
        assert clock_key is key
        clock_ref = cache.clock_refs[pos]

    # All clock_refs must be True or False, nothing else.
    for clock_ref in cache.clock_refs:
        assert clock_ref is True or clock_ref is False


def check_expiring_lru_cache_is_consistent(cache):
    # Return if cache is consistent, else raise fail test case.
    #
    # This is slightly different for ExpiringLRUCache since self.data
    # contains 3-tuples instead of 2-tuples.
    # cache.hand/maxpos/size
    assert cache.hand < len(cache.clock_keys)
    assert cache.hand >= 0
    assert cache.maxpos == cache.size - 1
    assert len(cache.clock_keys) == cache.size

    # lengths of data structures
    assert len(cache.clock_keys) == len(cache.clock_refs)
    assert len(cache.data) <= len(cache.clock_refs)

    # For each item in cache.data
    #   1. pos must be a valid index
    #   2. clock_keys must point back to the entry
    for key, value in cache.data.items():
        pos, val, timeout = value
        assert type(pos) is int or type(pos) is type(2**128)
        assert pos >= 0
        assert pos <= cache.maxpos

        clock_key = cache.clock_keys[pos]
        assert clock_key is key
        clock_ref = cache.clock_refs[pos]

        assert type(timeout) is float

    # All clock_refs must be True or False, nothing else.
    for clock_ref in cache.clock_refs:
        assert clock_ref is True or clock_ref is False


@pytest.fixture(
    params=[
        (lru.LRUCache, check_lru_cache_is_consistent),
        (lru.ExpiringLRUCache, check_expiring_lru_cache_is_consistent),
    ]
)
def cache_class_and_checker(request):
    return request.param


@pytest.fixture
def cache_class(cache_class_and_checker):
    klass, _ = cache_class_and_checker
    return klass


def test_cache_size_lessthan_1(cache_class):
    with pytest.raises(lru.CacheSizeMustBeGreaterThanZero):
        cache_class(0)


def test_cache_get(cache_class_and_checker):
    cache_class, checker = cache_class_and_checker

    cache = cache_class(1)
    # Must support different types of keys
    assert cache.get("foo") is None
    assert cache.get(42) is None
    assert cache.get(("foo", 42)) is None
    assert cache.get(None) is None
    assert cache.get("") is None
    assert cache.get(object()) is None
    # Check if default value is used
    assert cache.get("foo", "bar") == "bar"
    assert cache.get("foo", default="bar") == "bar"

    checker(cache)


def test_put(cache_class_and_checker):
    cache_class, checker = cache_class_and_checker

    cache = cache_class(8)
    checker(cache)

    # Must support different types of keys
    cache.put("foo", "FOO")
    cache.put(42, "fortytwo")
    cache.put(("foo", 42), "tuple_as_key")
    cache.put(None, "None_as_key")
    cache.put("", "empty_string_as_key")
    cache.put(3.141, "float_as_key")
    my_object = object()
    cache.put(my_object, "object_as_key")

    checker(cache)

    assert cache.get("foo") == "FOO"
    assert cache.get(42) == "fortytwo"
    assert cache.get(("foo", 42)) == "tuple_as_key"
    assert cache.get(None) == "None_as_key"
    assert cache.get("") == "empty_string_as_key"
    assert cache.get(3.141) == "float_as_key"
    assert cache.get(my_object) == "object_as_key"

    # put()ing again must overwrite
    cache.put(42, "fortytwo again")
    assert cache.get(42) == "fortytwo again"

    checker(cache)


def test_cache_invalidate(cache_class_and_checker):
    cache_class, checker = cache_class_and_checker

    cache = cache_class(3)
    cache.put("foo", "bar")
    cache.put("FOO", "BAR")

    cache.invalidate("foo")
    assert cache.get("foo") is None
    assert cache.get("FOO") == "BAR"
    checker(cache)

    cache.invalidate("FOO")
    assert cache.get("foo") is None
    assert cache.get("FOO") is None
    assert cache.data == {}
    checker(cache)

    cache.put("foo", "bar")
    cache.invalidate("nonexistingkey")
    assert cache.get("foo") == "bar"
    assert cache.get("FOO") is None
    checker(cache)


def test_cache_small_cache(cache_class_and_checker):
    cache_class, checker = cache_class_and_checker

    # Cache of size 1 must work
    cache = cache_class(1)

    cache.put("foo", "bar")
    assert cache.get("foo") == "bar"
    checker(cache)

    cache.put("FOO", "BAR")
    assert cache.get("FOO") == "BAR"
    assert cache.get("foo") is None
    checker(cache)

    # put() again
    cache.put("FOO", "BAR")
    assert cache.get("FOO") == "BAR"
    assert cache.get("foo") is None
    checker(cache)

    # invalidate()
    cache.invalidate("FOO")
    checker(cache)
    assert cache.get("FOO") is None
    assert cache.get("foo") is None

    # clear()
    cache.put("foo", "bar")
    assert cache.get("foo") == "bar"
    cache.clear()
    checker(cache)
    assert cache.get("FOO") is None
    assert cache.get("foo") is None


def test_cache_w_equal_but_not_identical(cache_class_and_checker):
    cache_class, checker = cache_class_and_checker

    # equal but not identical keys must be treated the same
    cache = cache_class(1)
    tuple_one = (1, 1)
    tuple_two = (1, 1)
    cache.put(tuple_one, 42)

    assert cache.get(tuple_one) == 42
    assert cache.get(tuple_two) == 42
    checker(cache)

    cache = cache_class(1)
    cache.put(tuple_one, 42)
    cache.invalidate(tuple_two)
    assert cache.get(tuple_one) is None
    assert cache.get(tuple_two) is None


def test_cache_w_perfect_hitrate(cache_class_and_checker):
    cache_class, checker = cache_class_and_checker

    # If cache size equals number of items, expect 100% cache hits
    size = 1000
    cache = cache_class(size)

    for count in range(size):
        cache.put(count, f"item{count}")

    for _cache_op in range(10000):
        item = random.randrange(0, size - 1)
        if random.getrandbits(1):
            assert cache.get(item) == f"item{item}"
        else:
            cache.put(item, f"item{item}")

    assert cache.misses == 0
    assert cache.evictions == 0

    checker(cache)


def test_cache_w_imperfect_hitrate(cache_class_and_checker):
    cache_class, checker = cache_class_and_checker

    # If cache size == half the number of items -> hit rate ~50%
    size = 1000
    cache = cache_class(size / 2)

    for count in range(size):
        cache.put(count, f"item{count}")

    hits = 0
    misses = 0
    total_gets = 0
    for _cache_op in range(10000):
        item = random.randrange(0, size - 1)
        if random.getrandbits(1):
            entry = cache.get(item)
            total_gets += 1
            assert (entry == f"item{item}") or entry is None
            if entry is None:
                misses += 1
            else:
                hits += 1
        else:
            cache.put(item, f"item{item}")

    # Cache hit rate should be roughly 50%
    hit_ratio = hits / float(total_gets) * 100
    assert hit_ratio > 45
    assert hit_ratio < 55

    # The internal cache counters should have the same information
    internal_hit_ratio = 100 * cache.hits / cache.lookups
    assert internal_hit_ratio > 45
    assert internal_hit_ratio < 55

    # The internal miss counters should also be around 50%
    internal_miss_ratio = 100 * cache.misses / cache.lookups
    assert internal_miss_ratio > 45
    assert internal_miss_ratio < 55

    checker(cache)


def test_cache_eviction_counter(cache_class):

    cache = cache_class(2)
    cache.put(1, 1)
    cache.put(2, 1)
    assert cache.evictions == 0

    cache.put(3, 1)
    cache.put(4, 1)
    assert cache.evictions == 2

    cache.put(3, 1)
    cache.put(4, 1)
    assert cache.evictions == 2

    cache.clear()
    assert cache.evictions == 0


def test_lru_cache_ops():
    cache = lru.LRUCache(3)
    assert cache.get("a") is None

    cache.put("a", "1")
    pos, value = cache.data.get("a")
    assert cache.clock_refs[pos] is True
    assert cache.clock_keys[pos] == "a"
    assert value == "1"
    assert cache.get("a") == "1"
    assert cache.hand == pos + 1

    pos, value = cache.data.get("a")
    assert cache.clock_refs[pos] is True
    assert cache.hand == pos + 1
    assert len(cache.data) == 1

    cache.put("b", "2")
    pos, value = cache.data.get("b")
    assert cache.clock_refs[pos] is True
    assert cache.clock_keys[pos] == "b"
    assert len(cache.data) == 2

    cache.put("c", "3")
    pos, value = cache.data.get("c")
    assert cache.clock_refs[pos] is True
    assert cache.clock_keys[pos] == "c"
    assert len(cache.data) == 3

    pos, value = cache.data.get("a")
    assert cache.clock_refs[pos] is True

    cache.get("a")
    # All items have ref==True. cache.hand points to "a". Putting
    # "d" will set ref=False on all items and then replace "a",
    # because "a" is the first item with ref==False that is found.
    cache.put("d", "4")
    assert len(cache.data) == 3
    assert cache.data.get("a") is None

    # Only item "d" has ref==True. cache.hand points at "b", so "b"
    # will be evicted when "e" is inserted. "c" will be left alone.
    cache.put("e", "5")
    assert len(cache.data) == 3
    assert cache.data.get("b") is None
    assert cache.get("d") == "4"
    assert cache.get("e") == "5"
    assert cache.get("a") is None
    assert cache.get("b") is None
    assert cache.get("c") == "3"

    check_lru_cache_is_consistent(cache)


def test_expiring_lru_cache_ops():
    # Test a sequence of operations
    #
    # Looks at internal data, which is different for ExpiringLRUCache.
    cache = lru.ExpiringLRUCache(3)
    assert cache.get("a") is None

    cache.put("a", "1")
    pos, value, expires = cache.data.get("a")
    assert cache.clock_refs[pos] is True
    assert cache.clock_keys[pos] == "a"
    assert value == "1"
    assert cache.get("a") == "1"
    assert cache.hand == pos + 1

    pos, value, expires = cache.data.get("a")
    assert cache.clock_refs[pos] is True
    assert cache.hand == pos + 1
    assert len(cache.data) == 1

    cache.put("b", "2")
    pos, value, expires = cache.data.get("b")
    assert cache.clock_refs[pos] is True
    assert cache.clock_keys[pos] == "b"
    assert len(cache.data) == 2

    cache.put("c", "3")
    pos, value, expires = cache.data.get("c")
    assert cache.clock_refs[pos] is True
    assert cache.clock_keys[pos] == "c"
    assert len(cache.data) == 3

    pos, value, expires = cache.data.get("a")
    assert cache.clock_refs[pos] is True

    cache.get("a")
    # All items have ref==True. cache.hand points to "a". Putting
    # "d" will set ref=False on all items and then replace "a",
    # because "a" is the first item with ref==False that is found.
    cache.put("d", "4")
    assert len(cache.data) == 3
    assert cache.data.get("a") is None

    # Only item "d" has ref==True. cache.hand points at "b", so "b"
    # will be evicted when "e" is inserted. "c" will be left alone.
    cache.put("e", "5")
    assert len(cache.data) == 3
    assert cache.data.get("b") is None
    assert cache.get("d") == "4"
    assert cache.get("e") == "5"
    assert cache.get("a") is None
    assert cache.get("b") is None
    assert cache.get("c") == "3"

    check_expiring_lru_cache_is_consistent(cache)


def test_expiring_lru_cache_default_timeout():
    # Default timeout provided at init time must be applied.
    # Provide no default timeout -> entries must remain valid
    cache = lru.ExpiringLRUCache(3)
    cache.put("foo", "bar")

    time.sleep(0.1)
    cache.put("FOO", "BAR")
    assert cache.get("foo") == "bar"
    assert cache.get("FOO") == "BAR"
    check_expiring_lru_cache_is_consistent(cache)

    # Provide short default timeout -> entries must become invalid
    cache = lru.ExpiringLRUCache(3, default_timeout=0.1)
    cache.put("foo", "bar")

    time.sleep(0.1)
    cache.put("FOO", "BAR")
    assert cache.get("foo") is None
    assert cache.get("FOO") == "BAR"
    check_expiring_lru_cache_is_consistent(cache)


def test_expiring_lru_cache_w_different_timeouts():
    # Timeouts must be per entry, default applied when none provided
    cache = lru.ExpiringLRUCache(3, default_timeout=0.1)

    cache.put("one", 1)
    cache.put("two", 2, timeout=0.2)
    cache.put("three", 3, timeout=0.3)

    # All entries still here
    assert cache.get("one") == 1
    assert cache.get("two") == 2
    assert cache.get("three") == 3

    # Entry "one" must expire, "two"/"three" remain valid
    time.sleep(0.1)
    assert cache.get("one") is None
    assert cache.get("two") == 2
    assert cache.get("three") == 3

    # Only "three" remains valid
    time.sleep(0.1)
    assert cache.get("one") is None
    assert cache.get("two") is None
    assert cache.get("three") == 3

    # All have expired
    time.sleep(0.1)
    assert cache.get("one") is None
    assert cache.get("two") is None
    assert cache.get("three") is None

    check_expiring_lru_cache_is_consistent(cache)


def test_expiring_lru_cache_w_renew_timeout():
    # Re-putting an entry must update timeout
    cache = lru.ExpiringLRUCache(3, default_timeout=0.2)

    cache.put("foo", "bar")
    cache.put("foo2", "bar2", timeout=10)
    cache.put("foo3", "bar3", timeout=10)

    time.sleep(0.1)
    # All must still be here
    assert cache.get("foo") == "bar"
    assert cache.get("foo2") == "bar2"
    assert cache.get("foo3") == "bar3"
    check_expiring_lru_cache_is_consistent(cache)

    # Set new timeouts by re-put()ing the entries
    cache.put("foo", "bar")
    cache.put("foo2", "bar2", timeout=0.1)
    cache.put("foo3", "bar3")

    time.sleep(0.1)
    # "foo2" must have expired
    assert cache.get("foo") == "bar"
    assert cache.get("foo2") is None
    assert cache.get("foo3") == "bar3"
    check_expiring_lru_cache_is_consistent(cache)


def test_decorator_ctor_no_size():
    decorator = lru.lru_cache(maxsize=None)
    assert isinstance(decorator.cache, lru.UnboundedCache)
    assert decorator.cache._data == {}


def test_decorator_ctor_w_size_no_timeout():
    decorator = lru.lru_cache(maxsize=10)
    assert isinstance(decorator.cache, lru.LRUCache)
    assert decorator.cache.size == 10


def test_decorator_ctor_w_size_w_timeout():
    decorator = lru.lru_cache(maxsize=10, timeout=30)
    assert isinstance(decorator.cache, lru.ExpiringLRUCache)
    assert decorator.cache.size == 10
    assert decorator.cache.default_timeout == 30


def test_decorator_ctor_nocache():
    decorator = lru.lru_cache(10, None)
    assert decorator.cache.size == 10


def test_decorator_singlearg():
    cache = DummyLRUCache()
    decorator = lru.lru_cache(0, cache)

    def wrapped(key):
        return key

    decorated = decorator(wrapped)

    result = decorated(1)
    assert cache[(1,)] == 1
    assert result == 1
    assert len(cache) == 1

    result = decorated(2)
    assert cache[(2,)] == 2
    assert result == 2
    assert len(cache) == 2

    result = decorated(2)
    assert cache[(2,)] == 2
    assert result == 2
    assert len(cache) == 2


def test_decorator_cache_attr():
    cache = DummyLRUCache()
    decorator = lru.lru_cache(0, cache)

    def wrapped(key):  # pragma NO COVER
        return key

    decorated = decorator(wrapped)
    assert decorated._cache is cache


def test_decorator_multiargs():
    cache = DummyLRUCache()
    decorator = lru.lru_cache(0, cache)

    def moreargs(*args):
        return args

    decorated = decorator(moreargs)
    result = decorated(3, 4, 5)
    assert cache[(3, 4, 5)] == (3, 4, 5)
    assert result == (3, 4, 5)
    assert len(cache) == 1


def test_decorator_multiargs_keywords():
    cache = DummyLRUCache()
    decorator = lru.lru_cache(0, cache)

    def moreargs(*args, **kwargs):
        return args, kwargs

    decorated = decorator(moreargs)
    result = decorated(3, 4, 5, a=1, b=2, c=3)

    assert cache[((3, 4, 5), frozenset([("a", 1), ("b", 2), ("c", 3)]))] == (
        (3, 4, 5),
        {"a": 1, "b": 2, "c": 3},
    )
    assert result == ((3, 4, 5), {"a": 1, "b": 2, "c": 3})
    assert len(cache) == 1


def test_decorator_multiargs_keywords_ignore_unhashable_true():
    cache = DummyLRUCache()
    decorator = lru.lru_cache(0, cache, ignore_unhashable_args=True)

    def moreargs(*args, **kwargs):
        return args, kwargs

    decorated = decorator(moreargs)

    result = decorated(3, 4, 5, a=1, b=[1, 2, 3])

    assert len(cache) == 0
    assert result == ((3, 4, 5), {"a": 1, "b": [1, 2, 3]})


def test_decorator_multiargs_keywords_ignore_unhashable():
    cache = DummyLRUCache()
    decorator = lru.lru_cache(0, cache, ignore_unhashable_args=False)

    def moreargs(*args, **kwargs):  # pragma: NO COVER
        return args, kwargs

    decorated = decorator(moreargs)

    with pytest.raises(TypeError):
        decorated(3, 4, 5, a=1, b=[1, 2, 3])


def test_decorator_expiry():
    # When timeout is given, decorator must eventually forget entries
    @lru.lru_cache(1, None, timeout=0.1)
    def sleep_a_bit(param):
        time.sleep(0.1)
        return 2 * param

    # First call must take at least 0.1 seconds
    start = time.time()
    result1 = sleep_a_bit("hello")
    stop = time.time()
    assert result1 == 2 * "hello"
    assert stop - start > 0.1

    # Second call must take less than 0.1 seconds.
    start = time.time()
    result2 = sleep_a_bit("hello")
    stop = time.time()
    assert result2 == 2 * "hello"
    assert stop - start < 0.1

    time.sleep(0.1)
    # This one must calculate again and take at least 0.1 seconds
    start = time.time()
    result3 = sleep_a_bit("hello")
    stop = time.time()
    assert result3 == 2 * "hello"
    assert stop - start > 0.1


def test_decorator_partial():
    # lru_cache decorator must not crash on functools.partial instances
    def add(a, b):
        return a + b

    add_five = functools.partial(add, 5)

    decorated = lru.lru_cache(20)(add_five)
    assert decorated(3) == 8


def test_cachemaker_named_cache():
    maker = lru.CacheMaker()
    size = 10
    name = "name"
    decorated = maker.lrucache(maxsize=size, name=name)(_adder)
    assert list(maker._cache.keys()) == [name]
    assert maker._cache[name].size == size
    decorated(10)
    decorated(11)
    assert len(maker._cache[name].data) == 2


def test_cachemaker_exception():
    maker = lru.CacheMaker()
    size = 10
    name = "name"
    _decorated = maker.lrucache(maxsize=size, name=name)(_adder)

    with pytest.raises(lru.CacheAlreadyInUse):
        maker.lrucache(maxsize=size, name=name)

    with pytest.raises(lru.CacheMaxsizeRequired):
        maker.lrucache()


def test_cachemaker_defaultvalue_and_clear():
    size = 10
    maker = lru.CacheMaker(maxsize=size)

    for _i in range(100):
        decorated = maker.lrucache()(_adder)
        decorated(10)

    assert len(maker._cache) == 100

    for _cache in maker._cache.values():
        assert _cache.size == size
        assert len(_cache.data) == 1

    ## and test clear cache
    maker.clear()

    for _cache in maker._cache.values():
        assert _cache.size == size
        assert len(_cache.data) == 0


def test_cachemaker_clear_with_single_name():
    maker = lru.CacheMaker(maxsize=10)
    one = maker.lrucache(name="one")(_adder)
    two = maker.lrucache(name="two")(_adder)

    for i in range(100):
        _ = one(i)
        _ = two(i)

    assert len(maker._cache["one"].data) == 10
    assert len(maker._cache["two"].data) == 10

    maker.clear("one")

    assert len(maker._cache["one"].data) == 0
    assert len(maker._cache["two"].data) == 10


def test_cachemaker_clear_with_multiple_names():
    maker = lru.CacheMaker(maxsize=10)
    one = maker.lrucache(name="one")(_adder)
    two = maker.lrucache(name="two")(_adder)
    three = maker.lrucache(name="three")(_adder)

    for i in range(100):
        _ = one(i)
        _ = two(i)
        _ = three(i)

    assert len(maker._cache["one"].data) == 10
    assert len(maker._cache["two"].data) == 10
    assert len(maker._cache["three"].data) == 10

    maker.clear("one", "three")

    assert len(maker._cache["one"].data) == 0
    assert len(maker._cache["two"].data) == 10
    assert len(maker._cache["three"].data) == 0


def test_cachemaker_memoized():
    maker = lru.CacheMaker(maxsize=10)

    memo = maker.memoized("test")

    assert isinstance(memo, lru.lru_cache)
    assert isinstance(memo.cache, lru.UnboundedCache)
    assert memo.cache is maker._cache["test"]


def test_cachemaker_expiring():
    size = 10
    timeout = 10
    name = "name"
    cache = lru.CacheMaker(maxsize=size, timeout=timeout)
    for i in range(100):
        if not i:
            decorator = cache.expiring_lrucache(name=name)
            decorated = decorator(_adder)
            assert cache._cache[name].size == size
        else:
            decorator = cache.expiring_lrucache()
            decorated = decorator(_adder)
            assert decorator.cache.default_timeout == timeout
        decorated(10)

    assert len(cache._cache) == 100

    for _cache in cache._cache.values():
        assert _cache.size == size
        assert _cache.default_timeout == timeout
        assert len(_cache.data) == 1

    ## and test clear cache
    cache.clear()

    for _cache in cache._cache.values():
        assert _cache.size == size
        assert len(_cache.data) == 0


def test_cachemaker_expiring_w_timeout():
    size = 10
    maker_timeout = 10
    timeout = 20
    name = "name"
    cache = lru.CacheMaker(maxsize=size, timeout=maker_timeout)

    decorator = cache.expiring_lrucache(name=name, timeout=20)

    assert decorator.cache.default_timeout == timeout


class DummyLRUCache(dict):
    def put(self, k, v):
        return self.__setitem__(k, v)


def _adder(x):
    return x + 10
