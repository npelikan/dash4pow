import requests
import os
import pandas as pd

url = "https://api.synopticdata.com/v2/stations/timeseries"

resp =  requests.get(url, params={
    "token": os.getenv("MESONET_TOKEN"), # access token
    "stid": ["iff", "rey", "C99"], # mesonet station ids
    "recent": 1440 # time in minutes
})

j = resp.json()

def get_station_series(i):
    df = pd.DataFrame(i["OBSERVATIONS"])
    df["date_time"] = pd.to_datetime(df["date_time"]).dt.tz_convert(tz="America/Denver")
    df["station"] = i["NAME"]
    
    return df

ss = pd.concat((get_station_series(x) for x in j["STATION"]))
ss = ss.set_index(["station", "date_time"])

for pfx in dataseries:
    matchcols = [x for x in ss.columns if x.startswith(pfx)]
    if len(matchcols) < 1:
        continue
    elif len(matchcols) == 1:
        ss[pfx] = ss[matchcols[0]]
    else:
        ss[pfx] = ss[matchcols].bfill(axis=1).iloc[:, 0]


