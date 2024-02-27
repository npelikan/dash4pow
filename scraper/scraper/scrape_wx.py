import requests
import os
import pandas as pd
import plotly.express as px

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

cyn = ss[ss.station == "Canyons - 9990"]

bins_mag = [0, 1, 2, 3, 4, 5, 6, 999]
bins_mag_labels = ["0-1", "1-2", "2-3", "3-4", "4-5", "5-6", "6+"]

cyn["mag_binned"] = pd.cut(cyn.wind_speed_set_1, bins_mag, labels=bins_mag_labels)
cyn["dir_binned"] = pd.Categorical(cyn.wind_cardinal_direction_set_1d, categories=['N','NNE','NE','ENE','E','ESE','SE','SSE','S','SSW','SW','WSW','W','WNW','NW','NNW'], ordered=False)

keepcols = ["mag_binned", "dir_binned"]
dfe = cyn[keepcols].groupby(keepcols, as_index=False).size()
dfe["frequency"] = dfe["size"] / (dfe["size"].sum())



px.bar_polar(cyn, r="wind_speed_set_1", theta="wind_direction_set_1")

for pfx in dataseries:
    matchcols = [x for x in ss.columns if x.startswith(pfx)]
    if len(matchcols) < 1:
        continue
    elif len(matchcols) == 1:
        ss[pfx] = ss[matchcols[0]]
    else:
        ss[pfx] = ss[matchcols].bfill(axis=1).iloc[:, 0]


