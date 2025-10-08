import asyncio
import logging
import os
from datetime import datetime
from http.cookies import SimpleCookie

import dotenv
from fastapi import HTTPException
from pydantic import BaseModel
from twikit import Client
from twikit import Tweet as TwikitTweet
from twikit import User as TwikitUser

from api.store import get_data
from lib.cache import async_threadsafe_ttl_cache
from lib.utils import get_since_date

logger = logging.getLogger(__name__)

dotenv.load_dotenv()

# check if we have cookies in env and save to file if not already there
if not os.getenv("SVC_COOKIES"):
    msg = "SVC_COOKIES environment variable not set, cannot authenticate"
    raise ValueError(msg)
cookies_raw = os.getenv("SVC_COOKIES")
cache_dir = os.getenv("CACHE", "cache")
cookies_file: str = os.path.join(cache_dir, "cookies.txt")
if not os.path.exists(cookies_file):
    os.makedirs(cache_dir, exist_ok=True)
    with open(cookies_file, "w", encoding="utf-8") as f:
        f.write(cookies_raw)

client = Client(
    user_agent=(
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
    ),
)


class User(BaseModel, TwikitUser):
    # The unique identifier of the user.
    id: int
    # The screen name of the user.
    screen_name: str


class Tweet(BaseModel, TwikitTweet):
    # The unique identifier of the tweet.
    id: str
    # The full text of the tweet.
    text: str
    # The language of the tweet.
    lang: str
    # Hashtags included in the tweet text.
    hashtags: list[str]
    # User that created the tweet.
    user: User


async def _get_client() -> Client:
    with open(cookies_file, encoding="utf-8") as cookie_file:
        cookies_str = cookie_file.read()
    cookie = SimpleCookie()
    cookie.load(cookies_str)
    cookies = {k: v.value for k, v in cookie.items()}
    client.set_cookies(cookies)
    return client


def _validate_x_search_params(
    users: str | None, query: str | None, period_days: int, end_date: str | None
) -> str | None:
    """Validate x_search parameters."""
    if users == "":
        users = None
    if not users and not query:
        raise ValueError("Either users or query must be provided")
    if period_days <= 1:
        raise ValueError("period_days must be 1 or more")
    if end_date:
        try:
            datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError as e:
            if "does not match format" in str(e):
                raise ValueError("end_date must be in YYYY-MM-DD format") from e
            raise
    return users


def _build_x_search_query(
    users_arr: list[str], query: str | None, period_days: int, end_date: str | None
) -> str:
    """Build the X search query string."""
    query_str = f" {query}" if query else ""
    [year, month, day] = get_since_date(period_days, end_date)
    since = f"since:{year}-{month}-{day} "
    until = f"until:{end_date}" if end_date else ""
    users_str = " (" + " OR ".join(users_arr) + ")" if len(users_arr) > 0 else ""
    return f"{since}{until}{users_str}{query_str}".strip()


async def _fetch_tweets(search: str, count: int) -> list[Tweet]:
    """Fetch tweets using the X API client."""
    tweets: list[Tweet] = []
    x_client = await _get_client()
    _tweets = await x_client.search_tweet(query=search, product="Latest", count=count)
    tweets.extend(_tweets)
    while (len(_tweets) == 20) and len(tweets) < count:
        _tweets = await _tweets.next()
        tweets.extend(_tweets)
        await asyncio.sleep(1)
    return tweets


# cache results for one hour
@async_threadsafe_ttl_cache(ttl=3600)
async def x_search(
    users: str | None,
    query: str | None = None,
    period_days: int = 3,
    end_date: str | None = None,
    max_tweets_per_user: int = 20,
) -> list[Tweet]:
    """Search for tweets from specific users or matching a query."""
    users = _validate_x_search_params(users, query, period_days, end_date)

    logger.debug(
        f"Searching for tweets with users: {users}, query: {query}, "
        f"period_days: {period_days}, end_date: {end_date}, max_tweets_per_user: {max_tweets_per_user}"
    )

    users_arr = (
        [f"from:{user}" for user in _filter_users(users.lower().split(","))]
        if users
        else []
    )
    search = _build_x_search_query(users_arr, query, period_days, end_date)
    count = len(users_arr) * max_tweets_per_user if users_arr else max_tweets_per_user

    try:
        tweets = await _fetch_tweets(search, count)
        return _max_per_user(tweets, max_tweets_per_user)
    except HTTPException as e:
        logger.exception(e)
        return []
    except (ConnectionError, TimeoutError, ValueError) as e:
        logger.exception(
            HTTPException(status_code=500, detail=f"Failed to fetch tweets: {e!s}")
        )
        return []


def _max_per_user(tweets: list[Tweet], max_tweets_per_user: int = 10) -> list[Tweet]:
    ret: dict[int, list[Tweet]] = {}
    for tweet in tweets:
        if tweet.user.id not in ret:
            ret[tweet.user.id] = []
        if len(ret[tweet.user.id]) >= max_tweets_per_user:
            continue
        ret[tweet.user.id].append(tweet)
    # flatten the dict
    return [tweet for tweets in ret.values() for tweet in tweets]


def _filter_users(users: list[str]) -> list[str]:
    """Only allow users in our data store."""
    data = get_data()
    fixed_users = []
    for user in users:
        # look up as partial match in our db
        found = next(
            (item for item in data if user.lower() in str(item.get("X", "")).lower()),
            None,
        )
        if found and found["X"] and found["X"].lower() != "n/a":
            fixed_users.append(found["X"])
    return fixed_users
