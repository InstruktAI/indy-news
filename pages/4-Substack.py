import asyncio

import streamlit as st
import streamlit.components.v1 as components

from api.main import get_substack_publications
from api.substack import substack_search

with open("index.html", encoding="utf-8") as f:
    html_code = f.read()
    components.html(html_code, height=0)

st.sidebar.title("Indy News Search")
st.title("Substack posts overview by topic")
st.markdown(
    """
## Get an overview of Substack posts that indy media are publishing (potentially on a topic).
(Results are cached one day.)
""",
)
query = st.text_input(
    "Topic (leave empty to get latest)...",
    placeholder="israel",
    max_chars=255,
    value=(st.query_params.query if "query" in st.query_params else ""),
)
publications = st.multiselect(
    "Provide one or more Substack publications to search in...",
    [pub for pub in get_substack_publications() if pub != "n/a"],
    default=[],
)

max_posts_per_publication = st.slider(
    "Select max number of posts per publication",
    1,
    25,
    (
        st.query_params.max_posts_per_publication
        if "max_posts_per_publication" in st.query_params
        else 10
    ),
)

get_content = st.checkbox(
    "Get full post content (slower)",
    value=(st.query_params.get_content if "get_content" in st.query_params else True),
)

if not publications or publications == "":
    st.warning("Select at least one or more publications and potentially a query")
    st.stop()


async def get_substack_results() -> None:
    results = await substack_search(
        query=query,
        publications=",".join(publications),
        max_posts_per_publication=max_posts_per_publication,
        get_content=get_content,
    )

    st.json(results, expanded=True)


asyncio.run(get_substack_results())
