import asyncio

import streamlit as st
import streamlit.components.v1 as components

from api.main import get_youtube_channels
from api.youtube import youtube_search

with open("index.html", encoding="utf-8") as f:
    html_code = f.read()
    components.html(html_code, height=0)

st.sidebar.title("Indy News Search")
st.title("Youtube overview by topic")
st.markdown(
    """
## Get an overview of youtube videos that indy media are publishing (potentially on a topic).
(Results are cached one hour.)
""",
)
query = st.text_input(
    "Topic (leave empty to get latest)...",
    placeholder="israel",
    max_chars=255,
    value=(st.query_params.query if "query" in st.query_params else ""),
)
channels = st.multiselect(
    "Provide one or more channels to search in...",
    get_youtube_channels(),
    default=["@thegrayzone7996", "@aljazeeraenglish", "@DemocracyNow"],
)

max_videos_per_channel = st.slider(
    "Select max number of videos per channel",
    1,
    25,
    (
        st.query_params.max_videos_per_channel
        if "max_videos_per_channel" in st.query_params
        else 2
    ),
)
end_date = st.date_input(
    "End date (defaults to today)",
    value="today",
)
period_days = int(
    st.text_input(
        "Period (days up till end_date)",
        st.query_params.period_days if "period_days" in st.query_params else 3,
    ),
)
show_as_videos = st.checkbox(
    "Show as videos",
    value=(
        st.query_params.show_as_videos if "show_as_videos" in st.query_params else True
    ),
)

get_transcripts = False
if not show_as_videos:
    get_transcripts = st.checkbox(
        "Get transcripts",
        value=(
            st.query_params.get_transcripts
            if "get_transcripts" in st.query_params
            else False
        ),
    )

if not channels or channels == "":
    st.warning("Select at least one or more channels and potentially a query")
    st.stop()


async def get_youtube_results() -> None:
    results = await youtube_search(
        query=query,
        channels=",".join(channels),
        period_days=period_days,
        end_date=end_date.strftime("%Y-%m-%d"),
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
