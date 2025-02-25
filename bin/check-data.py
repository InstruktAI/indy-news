import pandas as pd
import requests

# Load the CSV file (ensure the file name and path are correct)
df = pd.read_csv("data/updated.csv")

headers = {"User-Agent": "Mozilla/5.0"}


def check_youtube_channel(handle):
    if pd.isna(handle) or handle.lower() == "n/a":
        return None
    # The handle should start with '@'; we assume the URL is https://www.youtube.com/<handle>
    # For example, '@BAHeraldcom' becomes 'https://www.youtube.com/@BAHeraldcom'
    url = "https://www.youtube.com/" + handle
    try:
        response = requests.get(url, headers=headers)
        return response.status_code, url
    except Exception as e:
        return f"Error: {e}", url


# Iterate over each row and check the YouTube channel
results = []
for idx, row in df.iterrows():
    name = row["Name"]
    yt_handle = row["Youtube"]
    if pd.isna(yt_handle) or yt_handle.lower() == "n/a":
        result = f"{name}: No YouTube handle provided."
    else:
        status, url = check_youtube_channel(yt_handle)
        if status == 200:
            result = f"{name}: {yt_handle} ({url}) appears valid (status: {status})."
        else:
            result = f"{name}: {yt_handle} ({url}) may be invalid or inaccessible (status: {status})."
    results.append(result)

# Print the results
for res in results:
    print(res)
