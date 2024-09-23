import asyncio
import os
from datetime import datetime
from http.cookies import SimpleCookie
from typing import Dict, List

import dotenv
from pydantic import BaseModel
from twikit import Client
from twikit import Tweet as TwikitTweet
from twikit import User as TwikitUser

from api.store import get_data, query_media
from lib.cache import async_threadsafe_ttl_cache
from lib.utils import get_since_date

dotenv.load_dotenv()

# client = GuestClient()
client = Client(
    "en-US",
    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
)


class User(BaseModel, TwikitUser):
    # The unique identifier of the user.
    id: int
    # The screen name of the user.
    screen_name: str


class Tweet(BaseModel, TwikitTweet):
    # The unique identifier of the tweet.
    id: int
    # The created_at converted to datetime.
    created_at_datetime: datetime
    # The full text of the tweet.
    text: str
    # The language of the tweet.
    lang: str
    # Hashtags included in the tweet text.
    hashtags: List[str]
    # User that created the tweet.
    user: User


def get_client() -> Client:
    # if exists, load cookies from file
    if client._user_id is not None:
        return client
    cookies_raw = os.getenv("X_COOKIES")
    cookie = SimpleCookie()
    cookie.load(cookies_raw)
    cookies = {k: v.value for k, v in cookie.items()}
    client.set_cookies(cookies)
    return client


@async_threadsafe_ttl_cache(ttl=180)
async def x_search(
    query: str = None,
    users: str = None,
    period_days: int = 3,
    max_users: int = 20,
    max_tweets_per_user: int = 20,
) -> List[Tweet]:
    if users:
        users_arr = _fix_users([f"from:{user}" for user in users.lower().split(",")])

    else:
        media = await query_media(query, top_k=max_users * 2)
        users_arr = []
        for item in media[:max_users]:
            if item["X"] != "n/a":
                users_arr.append(f"from:{item['X']}")

    query_str = f" {query}" if query else ""
    users_str = "(" + " OR ".join(users_arr) + ")" if len(users_arr) > 0 else ""
    [year, month, day] = get_since_date(period_days)
    query = f"{users_str}{query_str} since:{year}-{month}-{day}"
    if len(users_arr) == 0:
        return []
    tweets: List[Tweet] = []
    _tweets = await get_client().search_tweet(query=query, product="Latest", count=20)
    tweets.extend(_tweets)
    while (len(_tweets) == 20) and len(tweets) < max_users * max_tweets_per_user:
        _tweets = await _tweets.next()
        tweets.extend(_tweets)
        await asyncio.sleep(1)
    print("Number of tweets found: " + str(len(tweets)))
    return _max_per_user(tweets, max_tweets_per_user)


def _max_per_user(tweets: List[Tweet], max_tweets_per_user: int = 10) -> List[Tweet]:
    ret: Dict[int, List[Tweet]] = {}
    for tweet in tweets:
        if not tweet.user.id in ret:
            ret[tweet.user.id] = []
        if len(ret[tweet.user.id]) >= max_tweets_per_user:
            break
        ret[tweet.user.id].append(tweet)
    # flatten the dict
    return [tweet for tweets in ret.values() for tweet in tweets]


def _fix_users(users: List[str]) -> List[str]:
    data = get_data()
    fixed_users = []
    for user in users:
        # look up as partial match in our db
        found = next((item for item in data if user in item["X"]), None)
        if found:
            fixed_users.append(found["X"])
        # we always append, even if we did not correct it (which might throw a 400 later)
        else:
            fixed_users.append(user)
    return fixed_users
