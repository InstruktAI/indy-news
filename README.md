# Indy News

The API used by the [Indy News assistant](https://indy-news.instrukt.ai).

It uses [a selection of trusted news sources](https://github.com/Morriz/indy-news/blob/main/data/all.csv) to retrieve their publications for a time window and a potential topic of interest.

## Search for relevant independent media outlets

- [/media](http://127.0.0.1:8000/media?names=The%20Grayzone,Al%20Jazeera,Democracy%20Now)

## Search for relevant youtube videos

- [/youtube](http://127.0.0.1:8000/youtube?channels=@thegrayzone7996,@aljazeeraenglish,@DemocracyNow&query=israel&end_date=2025-12-12&period_days=90)

## Check the ratings DBs we used

It also contains some endpoints to see where the ratings come from:

- [/allsides](http://127.0.0.1:8000/allsides?query=israel)
- [/mediabiasfactcheck](http://127.0.0.1:8000/mediabiasfactcheck?query=israel)

### Databases used (see `data/` folder)

- all.csv: our source selection of media outlets
- allsides.com.json: snapshot of the AllSides db
- mediabiasfactcheck.com.json: snapshot of the [MediaBiasFactCheck db](https://mediabiasfactcheck.com)

### Dev instructions

1. Install and activate `.venv` and `pip install -r requirements.txt`

2. Run

- FastAPI: `.venv/bin/uvicorn --host "0.0.0.0" -p 8088`
- StreamLit `.venv/bin/streamlit run Home.py`
