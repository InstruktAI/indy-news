# Indy News

The FastAPI used by the [Indy News assistant](https://indy-news.instrukt.ai).
A service that aggregates content from independent media outlets across YouTube, X/Twitter, and Substack.

<img src="https://raw.githubusercontent.com/InstruktAI/indy-news/main/logo.jpg" alt="Indy News Logo" />

## Why Independent News Matters

In an era dominated by corporate media conglomerates, independent journalism serves as a critical counterweight to mainstream propaganda. Corporate media often omits, downplays, or censors stories that challenge establishment narratives or powerful interests. Independent outlets reveal what is censored, provide context that is suppressed, and amplify voices that are silenced.

However, discovering and tracking quality independent sources across multiple platforms remains challenging.

Indy News solves this by:

- **Curating** a vetted collection of independent media outlets spanning the political spectrum
- **Aggregating** their content from YouTube, X, and Substack in one unified API
- **Enabling** time-based and topic-based searches across all platforms simultaneously
- **Revealing** stories and perspectives that are censored or ignored by mainstream media

This makes independent journalism more discoverable and accessible, empowering readers to break free from algorithmic filter bubbles, counter establishment propaganda, and seek diverse viewpoints.

## Data Sources

[Curated source list](https://github.com/InstruktAI/indy-news/blob/main/data/sources.csv) - Independent media outlets with platform handles

## Live Streamlit App

A Streamlit interface is deployed at **[indy-news.streamlit.app](https://indy-news.streamlit.app)**

Available pages:

- **Media** - Search and browse independent media sources
- **Youtube** - Search YouTube videos by channel and topic with transcript support
- **X** - Search X/Twitter posts by user and topic with date filtering
- **Substack** - Search Substack articles by publication and topic

## Getting Started

```bash
# Install dependencies
make install

# Run the API server
make run
```

The API will be available at `http://127.0.0.1:8088`

### X/Twitter Setup

X search requires authenticated cookies. Export your browser cookies and add to `.env`:

```bash
SVC_COOKIES='lang=en; guest_id=123; auth_token=...; ct0=...; twid=u%3D1234567890; ...
```

If you want to clone this repo and scrape your own X sources, you can use our open source [cookie-service](https://github.com/InstruktAI/cookie-service). Once running it accepts the necessary credentials and will rotate your cookies automatically.

## API Endpoints

### Content Search

Search across platforms with optional time windows and topic filters:

- **[/youtube](http://127.0.0.1:8000/youtube?channels=@thegrayzone7996,@aljazeeraenglish&query=israel&end_date=2025-02-06&period_days=90)** - YouTube videos with transcript support
- **[/x](http://127.0.0.1:8000/x?users=TheGrayzoneNews,AJEnglish&query=israel&end_date=2025-02-06&period_days=90)** - X/Twitter posts
- **[/substack](http://127.0.0.1:8000/substack?publications=grayzoneproject&query=israel)** - Substack articles
- **[/news](http://127.0.0.1:8000/news?query=israel&end_date=2025-02-06&period_days=90)** - Combined YouTube + X search

### Source Discovery

- **[/sources](http://127.0.0.1:8000/sources)** - List all curated sources with metadata
- **[/source-media](http://127.0.0.1:8000/source-media)** - Get platform handles for sources
- **[/media](http://127.0.0.1:8000/media?names=The%20Grayzone,Democracy%20Now)** - Search source database

## Development

```bash
make format    # Format code with isort and black
make lint      # Run pylint and mypy
make test      # Run pytest suite
```

See [CLAUDE.md](./CLAUDE.md) for architecture details.
