import streamlit as st
import streamlit.components.v1 as components

with open("index.html") as f:
    html_code = f.read()
    components.html(html_code, height=0)

st.sidebar.title("Indy News Search")


st.markdown(
    """
# Indy News Search
### Search independent media outlets for news across YouTube, X/Twitter, and Substack
#### Source code: [InstruktAI/indy-news](https://github.com/InstruktAI/indy-news)
##### [Sources used](https://github.com/InstruktAI/indy-news/blob/main/data/sources.csv)

Please try one of the options in the menu, for example [Youtube](/Youtube).
"""
)
