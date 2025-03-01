import streamlit as st
import streamlit.components.v1 as components

with open("index.html", "r") as f:
    html_code = f.read()
    components.html(html_code, height=0)

st.sidebar.title("Indy News Search")


st.markdown(
    """
# Indy News Search
### Uses a database with a selection of media outlets that get enriched with entries from [mediabiasfactcheck.com](https://mediabiasfactcheck.com) data (if found)
#### Source code: [morriz/indy-news](https://github.com/Morriz/indy-news)
##### [Sources used](https://github.com/Morriz/indy-news/blob/main/data/all.csv)

Please try one of the options in the menu, for example [Youtube](/Youtube).
"""
)
