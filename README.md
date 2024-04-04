# Indy News

Try it on [Streamlit](https://indy-news.streamlit.app/)!

## Search for relevant independent media outlets or videos covering a topic

Contains both a streamlit app and a FastAPI module. The app uses the following _SMART_ api endpoints:

- [/media](http://127.0.0.1:8000/media?query=israel)
- [/youtube](http://127.0.0.1:8000/youtube?query=israel)

When I say smart I mean that the search tech used is:

- vector db
- hybrid bm25 + vector retriever

It also contains some dumb endpoints that only match input against the "name" property:

- [/allsides](http://127.0.0.1:8000/allsides?query=israel)
- [/mediabiasfactcheck](http://127.0.0.1:8000/mediabiasfactcheck?query=israel)

### Databases used (see `data/` folder)

- all.csv: 80+ media outlets enriched with entries from [mediabiasfactcheck.com](https://mediabiasfactcheck.com) data (if found).
- allsides.com.json: snapshot of the AllSides db
- mediabiasfactcheck.com.json: snapshot of the MediaBiasFactCheck db

### Original sources used

The following got normalized and ended up in all.csv:

- [libguides.rowan.edu](https://libguides.rowan.edu)
- [localfutures.org](https://localfutures.org)
- [trustworthymedia.org](https://trustworthymedia.org)
- some individuals and teams that I esteem and follow myself ;)

### Dev instructions

Run streamlit locally: `.venv/bin/streamlit run Home.py`

Run api locally: `.venv/bin/uvicorn --host "0.0.0.0" -p 8088`
