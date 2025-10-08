import streamlit as st
import streamlit.components.v1 as components

from api.main import search_allsides

with open("index.html", encoding="utf-8") as f:
    html_code = f.read()
    components.html(html_code, height=0)

st.sidebar.title("Indy News Search")
st.title("Search AllSides DB")
st.markdown(
    """
## Search for media outlets by partial name
Uses a snapshot of the AllSides DB (1604 records) and checks wether input is found in the *NAME* only.
(Ratings might differ from those in MediaBiasFactCheck, which seems not always up to date and is not as comprehensive.)
""",
)
name = st.text_input("Search by name...", value="Democracy Now", max_chars=255)

limit = st.slider("Select number of results", 1, 25, (5))

if name == "":
    st.stop()


def search_and_display_results() -> None:
    results = search_allsides(name, limit)
    st.json(results, expanded=True)


search_and_display_results()
