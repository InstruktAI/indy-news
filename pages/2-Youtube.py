import asyncio

import streamlit as st
import streamlit.components.v1 as components

from api.main import search_youtube

with open("index.html", "r") as f:
    html_code = f.read()
    components.html(html_code, height=0)

st.sidebar.title("Indy News Search")
st.title("Youtube overview by topic")
st.markdown(
    """
## Get an overview of youtube videos that indy media are publishing on a topic.
First uses "Media" endpoint to find sources and then queries youtube for videos from those sources.
(Results are cached one hour.)
"""
)
query = st.text_input("Search for topics/keywords...", value="israel", max_chars=255)

max_channels = st.slider("Select max number of channels", 1, 25, (12))
max_videos_per_channel = st.slider(
    "Select max number of videos per channel", 1, 25, (1)
)
period_days = st.text_input("Period (days since now)", 3)

if query == "":
    st.stop()


async def get_youtube_results() -> None:
    results = await search_youtube(
        query, period_days, max_channels, max_videos_per_channel
    )

    for item in results:
        #     st.markdown(
        #         f"[{item['title']}](https://www.youtube.com{item['url_suffix']})",
        #     )
        st.video(f"https://www.youtube.com{item.url_suffix}")


asyncio.run(get_youtube_results())
