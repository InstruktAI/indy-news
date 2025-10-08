import asyncio

import streamlit as st
import streamlit.components.v1 as components

from api.main import get_x_users
from api.x import x_search

with open("index.html", encoding="utf-8") as f:
    html_code = f.read()
    components.html(html_code, height=0)

st.sidebar.title("Indy News Search")
st.title("X/Twitter overview by topic")
st.markdown(
    """
## Get an overview of X/Twitter posts that indy media are publishing (potentially on a topic).
(Results are cached one hour.)
""",
)
query = st.text_input(
    "Topic (leave empty to get latest)...",
    placeholder="israel",
    max_chars=255,
    value=(st.query_params.query if "query" in st.query_params else ""),
)
users = st.multiselect(
    "Provide one or more X users to search in...",
    [user for user in get_x_users() if user != "n/a"],
    default=["AJEnglish", "democracynow", "TheGrayzoneNews"],
)

max_tweets_per_user = st.slider(
    "Select max number of tweets per user",
    1,
    50,
    (
        st.query_params.max_tweets_per_user
        if "max_tweets_per_user" in st.query_params
        else 20
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

if not users or users == "":
    st.warning("Select at least one or more users and potentially a query")
    st.stop()


async def get_x_results() -> None:
    results = await x_search(
        query=query,
        users=",".join(users),
        period_days=period_days,
        end_date=end_date.strftime("%Y-%m-%d"),
        max_tweets_per_user=max_tweets_per_user,
    )

    st.json(results, expanded=True)


asyncio.run(get_x_results())
