import logging
from datetime import datetime
from html import unescape
from typing import Any

from bs4 import BeautifulSoup
from pydantic import BaseModel
from substack_api import Newsletter

from lib.cache import sync_threadsafe_ttl_cache as cache

logger = logging.getLogger(__name__)


def html_to_text(html_content: str) -> str:
    """Convert HTML to plain text, preserving structure."""
    if not html_content:
        return ""

    # Parse HTML
    soup = BeautifulSoup(html_content, "html.parser")

    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()

    # Get text
    text = soup.get_text()

    # Break into lines and remove leading/trailing space
    lines = (line.strip() for line in text.splitlines())
    # Break multi-headlines into a line each
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    # Drop blank lines
    text = "\n".join(chunk for chunk in chunks if chunk)

    # Unescape HTML entities
    return unescape(text)


class SubstackPost(BaseModel):
    id: int
    slug: str
    title: str
    subtitle: str | None = None
    url: str
    published_at: datetime
    publication_name: str
    content: str | None = None  # Plain text content
    preview: str | None = None  # Text preview/description


def _fetch_newsletter_posts(
    newsletter_url: str, query: str | None, max_posts: int
) -> list[Any]:
    """Fetch posts from a Substack newsletter."""
    logger.debug(f"Fetching from {newsletter_url}")
    newsletter = Newsletter(newsletter_url)

    if query:
        logger.debug(f"Searching posts with query: {query}, limit: {max_posts}")
        return newsletter.search_posts(query=query, limit=max_posts)

    logger.debug(f"Getting posts with sorting: new, limit: {max_posts}")
    return newsletter.get_posts(sorting="new", limit=max_posts)


def _process_substack_post(post: Any, pub_name: str) -> SubstackPost | None:
    """Process a single Substack post and return SubstackPost object."""
    metadata = post.get_metadata()
    logger.debug(f"Processing post: {metadata.get('title', 'Unknown')}")

    date_str = metadata.get("post_date") or metadata.get("published_at")
    if not date_str:
        logger.warning(f"No date found for post: {post.url}")
        return None

    if metadata.get("audience") == "only_paid":
        return None

    content_text = None
    html_content = metadata.get("body_html")
    if html_content:
        content_text = html_to_text(html_content)

    return SubstackPost(
        id=metadata.get("id", 0),
        slug=post.slug,
        title=metadata.get("title", ""),
        subtitle=metadata.get("subtitle") or None,
        url=post.url,
        published_at=datetime.fromisoformat(date_str),
        publication_name=pub_name,
        content=content_text,
        preview=metadata.get("description") or metadata.get("preview_description"),
    )


@cache(ttl=86400)
async def substack_search(
    publications: str | None = None,
    query: str | None = None,
    max_posts_per_publication: int = 10,
    get_content: bool = True,
) -> list[SubstackPost]:
    """Search for posts from Substack publications."""
    logger.debug(
        f"substack_search called with: publications={publications}, max_posts={max_posts_per_publication}"
    )
    results = []
    publication_list = publications.split(",") if publications else []

    for pub in publication_list:
        try:
            newsletter_url = f"https://{pub.strip()}.substack.com"
            posts = _fetch_newsletter_posts(
                newsletter_url, query, max_posts_per_publication
            )
            logger.debug(f"Got {len(posts)} posts from {pub}")

            for post in posts:
                try:
                    substack_post = _process_substack_post(post, pub.strip())
                    if substack_post:
                        results.append(substack_post)
                except (AttributeError, KeyError, ValueError, TypeError) as e:
                    logger.exception(f"Error processing post {post.url}: {e}")
                    continue

        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            AttributeError,
            KeyError,
        ) as e:
            logger.exception(f"Error fetching posts from {pub}: {e}")
            continue

    logger.debug(f"Returning {len(results)} total posts")
    return results
