import asyncio

import streamlit as st
import streamlit.components.v1 as components

from api.youtube import youtube_search

with open("index.html", "r") as f:
    html_code = f.read()
    components.html(html_code, height=0)

st.sidebar.title("Indy News Search")
st.title("Youtube overview by topic")
st.markdown(
    """
## Get an overview of youtube videos that indy media are publishing on a topic.
Will query youtube channels for videos from either:
- channels provided: ("Query" then becomes optional: returns the latest channel videos if empty)
- curated channels (channels found in the db matching "Query")
(Results are cached one hour.)
"""
)
query = st.text_input(
    "Query (leave empty to get latest)...",
    placeholder="israel",
    max_chars=255,
)
channels = st.text_input(
    "Optionally provide channels to search in...",
    max_chars=255,
    placeholder="aljazeeraenglish,DemocracyNow",
)
max_channels = st.slider("Or select max number of channels", 1, 25, (12))

max_videos_per_channel = st.slider(
    "Select max number of videos per channel", 1, 25, (1)
)
period_days = st.text_input("Period (days since now)", 3)
show_as_videos = st.checkbox("Show as videos", value=True)
get_transcripts = False
if not show_as_videos:
    get_transcripts = st.checkbox("Get transcripts", value=False)

if query == "" and channels == "":
    st.warning("Select at least either query or channels.")
    st.stop()


async def get_youtube_results() -> None:
    results = await youtube_search(
        query=query,
        channels=channels,
        period_days=period_days,
        max_channels=max_channels,
        max_videos_per_channel=max_videos_per_channel,
        get_transcripts=get_transcripts,
    )

    if show_as_videos:
        for item in results:
            #     st.markdown(
            #         f"[{item['title']}](https://www.youtube.com{item['url_suffix']})",
            #     )
            st.video(f"https://www.youtube.com{item.url_suffix}")
    else:
        st.json(results, expanded=True)


asyncio.run(get_youtube_results())
