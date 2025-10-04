import logging
from datetime import datetime
from html import unescape
from typing import List, Optional

from bs4 import BeautifulSoup
from pydantic import BaseModel
from substack_api import Newsletter

logger = logging.getLogger(__name__)


def html_to_text(html_content: str) -> str:
    """Convert HTML to plain text, preserving structure"""
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
    text = unescape(text)

    return text


class SubstackPost(BaseModel):
    id: int
    slug: str
    title: str
    subtitle: Optional[str] = None
    url: str
    published_at: datetime
    publication_name: str
    content: Optional[str] = None  # Plain text content
    preview: Optional[str] = None  # Text preview/description


async def substack_search(
    publications: Optional[str] = None,
    query: Optional[str] = None,
    max_posts_per_publication: int = 10,
    get_content: bool = True,
) -> List[SubstackPost]:
    """
    Search for posts from Substack publications
    """
    logger.debug(
        f"substack_search called with: publications={publications}, max_posts={max_posts_per_publication}"
    )
    results = []

    publication_list = publications.split(",") if publications else []

    for pub in publication_list:
        try:
            # Initialize newsletter with the Substack URL
            newsletter_url = f"https://{pub.strip()}.substack.com"
            logger.debug(f"Fetching from {newsletter_url}")
            newsletter = Newsletter(newsletter_url)

            # Get or search posts from publication
            if query:
                # Use search when query is provided
                logger.debug(
                    f"Searching posts with query: {query}, limit: {max_posts_per_publication}"
                )
                posts = newsletter.search_posts(
                    query=query, limit=max_posts_per_publication
                )
            else:
                # Use get_posts with sorting when no query
                logger.debug(
                    f"Getting posts with sorting: new, limit: {max_posts_per_publication}"
                )
                posts = newsletter.get_posts(
                    sorting="new", limit=max_posts_per_publication
                )
            logger.debug(f"Got {len(posts)} posts from {pub}")

            for post in posts:
                try:
                    # Get post metadata
                    metadata = post.get_metadata()
                    logger.debug(f"Processing post: {metadata.get('title', 'Unknown')}")

                    # Get the published date - check both possible fields
                    date_str = metadata.get("post_date") or metadata.get("published_at")
                    if not date_str:
                        logger.warning(f"No date found for post: {post.url}")
                        continue

                    # Parse post date
                    post_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))

                    # Filter out paywalled content - only return free posts
                    audience = metadata.get("audience")
                    if audience == "only_paid":
                        continue

                    title = metadata.get("title", "")
                    subtitle = metadata.get("subtitle", "")

                    # Get content - either from metadata or fetch it
                    content_text = None
                    preview = metadata.get("description") or metadata.get(
                        "preview_description"
                    )

                    # Get content (body_html) from metadata
                    html_content = metadata.get("body_html")

                    if html_content:
                        # Convert HTML to plain text
                        content_text = html_to_text(html_content)

                    # No need to filter by query here - search_posts already handles it

                    results.append(
                        SubstackPost(
                            id=metadata.get("id", 0),
                            slug=post.slug,
                            title=title,
                            subtitle=subtitle if subtitle else None,
                            url=post.url,
                            published_at=post_date,
                            publication_name=pub.strip(),
                            content=content_text,
                            preview=preview,
                        )
                    )

                except Exception as e:
                    logger.error(f"Error processing post {post.url}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error fetching posts from {pub}: {e}")
            continue

    logger.debug(f"Returning {len(results)} total posts")
    return results
