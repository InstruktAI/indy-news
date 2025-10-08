from typing import Any

from cachetools import TTLCache
from cachetools.keys import hashkey

from lib.parameterized_lock import parameterized_lock


def async_threadsafe_ttl_cache(func: Any = None, ttl: int = 60) -> Any:
    cache: Any = TTLCache(maxsize=100, ttl=ttl)

    def decorator(decorated_func: Any) -> Any:
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Does not use 'session' in the key
            kwargs_for_key = {k: v for k, v in kwargs.items() if k != "session"}
            key = hashkey(*args, **kwargs_for_key)
            if key in cache:
                return cache[key]
            with parameterized_lock(key):
                if key in cache:
                    return cache[key]
                cache[key] = await decorated_func(*args, **kwargs)
                return cache[key]

        return wrapper

    # Allows to call the decorator with or without parenthesis
    return decorator(func) if callable(func) else decorator


def sync_threadsafe_ttl_cache(func: Any = None, ttl: int = 60) -> Any:
    cache: Any = TTLCache(maxsize=100, ttl=ttl)

    def decorator(decorated_func: Any) -> Any:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Does not use 'session' in the key
            kwargs_for_key = {k: v for k, v in kwargs.items() if k != "session"}
            key = hashkey(*args, **kwargs_for_key)
            if key in cache:
                return cache[key]
            with parameterized_lock(key):
                if key in cache:
                    return cache[key]
                cache[key] = decorated_func(*args, **kwargs)
                return cache[key]

        return wrapper

    # Allows to call the decorator with or without parenthesis
    return decorator(func) if callable(func) else decorator
