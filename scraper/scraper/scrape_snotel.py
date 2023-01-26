import zeep
import pandas as pd
import yaml
from functools import reduce
from pathlib import Path

fp = Path(__file__).parent

with open(fp / "config.yml", "r") as f:
    config = yaml.load(f, Loader=yaml.Loader)

client = zeep.Client("https://wcc.sc.egov.usda.gov/awdbWebService/services?WSDL")


def filter_valdict(d):
    return {k:v for k,v in d.items() if k in ('dateTime', 'value')}


def process_site(i, sensor_code):
    i = zeep.helpers.serialize_object(i)
    df = pd.DataFrame.from_records(filter_valdict(x) for x in i['values'])
    df["siteCode"] = i["stationTriplet"]
    df["dateTime"] = pd.to_datetime(df["dateTime"])
    df = df.set_index(["siteCode", "dateTime"])
    df = df.rename(columns = {"value": sensor_code})
    
    return df


def get_single_sensor_data(site_codes, sensor_code, start_date, end_date):
    resp = client.service.getHourlyData(
        stationTriplets=site_codes,
        elementCd=sensor_code,
        ordinal=1,
        beginDate=start_date,
        endDate=end_date
    )

    return pd.concat((process_site(x, sensor_code=sensor_code) for x in resp))


def get_snotel_data(site_codes, start_date, end_date):
    sensors = ["TOBS",  "SNWD", "WTEQ"]

    dfl = (
        get_single_sensor_data(
            sensor_code=x,
            site_codes=site_codes,
            start_date=start_date,
            end_date=end_date
        ) for x in sensors
    )

    out_df = reduce(lambda l, r: pd.merge(l, r, left_index=True, right_index=True), dfl)