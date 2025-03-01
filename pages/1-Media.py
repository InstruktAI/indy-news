import streamlit as st
import streamlit.components.v1 as components

from api.main import get_source_names, search_media

with open("index.html", "r") as f:
    html_code = f.read()
    components.html(html_code, height=0)

st.sidebar.title("Indy News Search")
st.title("Search media outlets")
st.markdown(
    """
## Search for relevant independent media outlets
"""
)
sources = st.multiselect(
    "Select one or more names of sources...",
    get_source_names(),
    default=["The Grayzone", "Al Jazeera", "Democracy Now"],
)

media = search_media(",".join(sources))

st.json(media, expanded=True)
