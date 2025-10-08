# Indy News

The API used by the [Indy News assistant](https://indy-news.instrukt.ai).

It uses [a selection of trusted news sources](https://github.com/Morriz/indy-news/blob/main/data/all.csv) to retrieve their publications for a time window and a potential topic of interest.

## Search for relevant independent media outlets

- [/media](http://127.0.0.1:8000/media?names=The%20Grayzone,Al%20Jazeera,Democracy%20Now)

## Search for relevant youtube videos

- [/youtube](http://127.0.0.1:8000/youtube?channels=@thegrayzone7996,@aljazeeraenglish,@DemocracyNow&query=israel&end_date=2025-02-06&period_days=90)

## Search for relevant X tweets

- [/x](http://127.0.0.1:8000/x?users=TheGrayzoneNews,AJEnglish,democracynow&query=israel&end_date=2025-02-06&period_days=90)

Prerequisites: Please first log in to X and log your cookies an place them in `.env` under `SVC_COOKIE`. It should look like this:

```
SVC_COOKIES='  lang=en; guest_id=123; night_mode=2; _twitter_sess=ABC--DEF; d_prefs=GJHHJVS; guest_id_ads=v1%3A1223423434; guest_id_marketing=v1%3A23423423423; personalization_id="v1_dasdiuhjKIvhhb=="; kdt=KJBNDFSbfsdksLKSDFJSDF; auth_token=sfsefsdfs234n2bn34j23kj4n2k; ct0=jsdfkdnksdndajsk21323kjn42kj; att=1kjfnaskNknlnlsfsaldkf; lang=en; twid=u%3D1342342342'
```

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

```

```
