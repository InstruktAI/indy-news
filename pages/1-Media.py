import asyncio

import streamlit as st
import streamlit.components.v1 as components

from api.main import search_media

with open("index.html", "r") as f:
    html_code = f.read()
    components.html(html_code, height=0)

st.sidebar.title("Indy News Search")
st.title("Search media outlets by topic")
st.markdown(
    """
## Search for relevant independent media outlets covering a topic
Uses a vector+BM25 combo retriever to query a custom vector db built from all.csv (83 records),
which is enriched with data from MediaBiasFactCheck.
(Results are cached one day.)
"""
)
query = st.text_input("Search for topics/keywords...", value="israel", max_chars=255)

limit = st.slider("Select number of results", 1, 25, (5))

if query == "":
    st.stop()


async def search_and_display_results() -> None:
    results = await search_media(query, limit=limit)
    st.json(results, expanded=True)


asyncio.run(search_and_display_results())
