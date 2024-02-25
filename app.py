import plotly.express as px

import pandas as pd

from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_plotly, render_widget

import requests
import zeep
from snotel_helpers import get_snotel_data
import pandas as pd
import os

site_config = {
    "BCC": {
        "snotel_sites": {
            "366:UT:SNTL": "Brighton, UT",
            "628:UT:SNTL": "Mill D, UT",
        },
        "wx_stations": {
            "C99": "Canyons - 9990",
            "REY": "Reynolds Peak",
            "UTCDF": "Cardiff Trailhead",
            "PC056": "Brighton",
        },
    },
    "LCC": {
        "snotel_sites": {
            "766:UT:SNTL": "Snowbird, UT",
            "1308:UT:SNTL": "Atwater Plot, UT",
        },
        "wx_stations": {
            "IFF": "Cardiff Peak",
            "PC064": "Albion Basin",
            "AMB": "Alta - Baldy",
            "HP": "Hidden Peak",
        },
    },
    "PC": {
        "snotel_sites": {
            "814:UT:SNTL": "Thaynes Canyon, UT",
        },
        "wx_stations": {
            "C99": "Canyons - 9990",
            "CDYBK": "Canyons - Daybreak",
            "REY": "Reynolds Peak",
        },
    },
}

station_ids = {}
snotel_sites = {}
for d in site_config.values():
    station_ids = station_ids | d["wx_stations"]
    snotel_sites = snotel_sites | d["snotel_sites"]

# station_ids = {
#     "C99": "Canyons - 9990",
#     "CDYBK": "Canyons - Daybreak",
#     "IFF": "Cardiff Peak",
#     "REY": "Reynolds Peak",
#     "UTCDF": "Cardiff Trailhead",
#     "PC056": "Brighton",
#     "PC064": "Albion Basin",
# }

# snotel_sites = {
#     "366:UT:SNTL": "Brighton, UT",
#     "766:UT:SNTL": "Snowbird, UT",
#     "628:UT:SNTL": "Mill D, UT",
#     "814:UT:SNTL": "Thaynes Canyon, UT",
#     "1308:UT:SNTL": "Atwater Plot, UT"
# }

snotel_sensors = {
    "TOBS": "Air Temperature (F)",
    "SNWD": "Snow Depth (in)",
    "WTEQ": "Snow Water Eq (in)",
}

ui.page_opts(fillable=True)


def forecast_data():
    resp = requests.get("https://utahavalanchecenter.org/forecast/salt-lake/json")
    j = resp.json()
    return j["advisories"][0]["advisory"]


def get_station_series(i):
    df = pd.DataFrame(i["OBSERVATIONS"])
    df["date_time"] = pd.to_datetime(df["date_time"]).dt.tz_convert(tz="America/Denver")
    df["station"] = i["NAME"]
    df["station_id"] = i["STID"]

    return df


@reactive.Calc
def wx_data() -> pd.DataFrame:
    url = "https://api.synopticdata.com/v2/stations/timeseries"

    resp = requests.get(
        url,
        params={
            "token": os.getenv("SYNOPTIC_TOKEN"),  # access token
            "stid": list(station_ids.keys()),  # mesonet station ids
            "recent": input.time() * 24 * 60,  # time in minutes
        },
    )

    j = resp.json()
    df = pd.concat((get_station_series(x) for x in j["STATION"]))
    df["date_time"] = pd.to_datetime(df["date_time"]).dt.tz_convert(tz="America/Denver")

    return df


@reactive.calc
def snotel_data() -> pd.DataFrame:
    client = zeep.Client("https://wcc.sc.egov.usda.gov/awdbWebService/services?WSDL")
    current_time = pd.Timestamp.now(tz="America/Denver")

    df = get_snotel_data(
        client,
        site_codes=list(snotel_sites.keys()),
        sensor_codes=list(snotel_sensors.keys()),
        start_date=(current_time - pd.Timedelta(days=input.time())).strftime(
            "%Y-%m-%d %H:00:00"
        ),
        end_date=current_time.strftime("%Y-%m-%d %H:00:00"),
    ).reset_index()

    df["siteName"] = df["siteCode"].replace(snotel_sites)
    df = df.reset_index()
    return df


def create_windrose(df):
    df["mag_binned"] = pd.cut(
        df.wind_speed_set_1,
        [0, 1, 2, 3, 4, 5, 6, 999],
        labels=["0-1", "1-2", "2-3", "3-4", "4-5", "5-6", "6+"],
    )

    df["dir_binned"] = pd.Categorical(
        df.wind_cardinal_direction_set_1d,
        categories=[
            "N",
            "NNE",
            "NE",
            "ENE",
            "E",
            "ESE",
            "SE",
            "SSE",
            "S",
            "SSW",
            "SW",
            "WSW",
            "W",
            "WNW",
            "NW",
            "NNW",
        ],
        ordered=False,
    )

    keepcols = ["mag_binned", "dir_binned"]
    dfe = df[keepcols].groupby(keepcols, as_index=False).size()
    dfe["frequency"] = dfe["size"] / (dfe["size"].sum())
    fig = px.bar_polar(
        dfe,
        r="frequency",
        theta="dir_binned",
        color="mag_binned",
        template="plotly_white",
        color_discrete_sequence=px.colors.sequential.Plasma_r,
    )
    fig = fig.update_layout(
        polar=dict(radialaxis=dict(showticklabels=False)), showlegend=False
    )
    return fig


## UI/UX

with ui.sidebar():
    ui.input_slider("time", "Time (days)", 1, 30, 3)
    # ui.input_select("station", "Weather Station", choices=station_ids)
    # ui.input_selectize("snotel_station", "SNOTEL Station", choices=snotel_sites, selected="366:UT:SNTL", multiple=True)
    ui.markdown("## Forecast Issued:")
    forecast_data()["date_issued"]

with ui.nav_panel(title="BCC"):
    with ui.layout_columns(fill=False, height="300px"):
        with ui.card():
            ui.card_header("Brighton")

            @render_plotly
            def windrose_b():
                df = wx_data()
                fig = create_windrose(df[df.station_id == "PC056"])
                return fig

        with ui.card():
            ui.card_header("Reynolds Peak")

            @render_plotly
            def windrose_rp():
                df = wx_data()
                fig = create_windrose(df[df.station_id == "REY"])
                return fig

        with ui.card():
            ui.card_header("PC Ridgeline")

            @render_plotly
            def windrose_c9():
                df = wx_data()
                fig = create_windrose(df[df.station_id == "C99"])
                return fig

    with ui.navset_card_tab(title="Time Series Data"):

        with ui.nav_panel("SWEq"):

            @render_widget
            def swe_bcc():
                df = snotel_data()
                fig = px.line(
                    df[df.siteCode.isin(["366:UT:SNTL", "628:UT:SNTL"])],
                    x="dateTime",
                    y="WTEQ",
                    color="siteName",
                    template="plotly_white",
                )
                fig.update_layout(
                    yaxis_title="Snow Water Eq (in H2O)",
                    xaxis_title=None,
                    legend_title=None,
                )
                return fig

        with ui.nav_panel("Air Temp"):

            @render_widget
            def temp_bcc():
                wx_df = wx_data()
                wx_df = wx_df[
                    wx_df.station_id.isin(
                        list(site_config["BCC"]["wx_stations"].keys())
                    )
                ][["station", "date_time", "air_temp_set_1"]]
                # convert to F
                wx_df.air_temp_set_1 = (wx_df.air_temp_set_1 * 1.8) + 32
                # rename to match snotel
                wx_df = wx_df.rename(
                    columns={
                        "station": "siteName",
                        "date_time": "dateTime",
                        "air_temp_set_1": "TOBS",
                    }
                )

                sn_df = snotel_data()
                sn_df = sn_df[
                    sn_df.siteCode.isin(list(site_config["BCC"]["snotel_sites"].keys()))
                ]
                df = pd.concat((wx_df, sn_df))
                fig = px.line(
                    df,
                    x="dateTime",
                    y="TOBS",
                    color="siteName",
                    template="plotly_white",
                )
                fig.update_layout(
                    yaxis_title="Air Temp (deg F)", xaxis_title=None, legend_title=None
                )
                return fig


with ui.nav_panel(title="LCC"):
    with ui.layout_columns(fill=False, height="300px"):
        with ui.card():
            ui.card_header("Cardiff Peak")

            @render_plotly
            def windrose_cp():
                df = wx_data()
                fig = create_windrose(df[df.station_id == "IFF"])
                return fig

        with ui.card():
            ui.card_header("Albion Basin")

            @render_plotly
            def windrose_ab():
                df = wx_data()
                fig = create_windrose(df[df.station_id == "PC064"])
                return fig

        with ui.card():
            ui.card_header("Alta - Baldy")

            @render_plotly
            def windrose_amb():
                df = wx_data()
                fig = create_windrose(df[df.station_id == "AMB"])
                return fig

        with ui.card():
            ui.card_header("Hidden Peak")

            @render_plotly
            def windrose_hp():
                df = wx_data()
                fig = create_windrose(df[df.station_id == "HP"])
                return fig

    with ui.navset_card_tab(title="Time Series Data"):

        with ui.nav_panel("SWEq"):

            @render_widget
            def swe_lcc():
                df = snotel_data()
                fig = px.line(
                    df[
                        df.siteCode.isin(
                            list(site_config["LCC"]["snotel_sites"].keys())
                        )
                    ],
                    x="dateTime",
                    y="WTEQ",
                    color="siteName",
                    template="plotly_white",
                )
                fig.update_layout(
                    yaxis_title="Snow Water Eq (in H2O)",
                    xaxis_title=None,
                    legend_title=None,
                )

                return fig

        with ui.nav_panel("Air Temp"):

            @render_widget
            def temp_lcc():
                wx_df = wx_data()
                wx_df = wx_df[
                    wx_df.station_id.isin(
                        list(site_config["LCC"]["wx_stations"].keys())
                    )
                ][["station", "date_time", "air_temp_set_1"]]
                # convert to F
                wx_df.air_temp_set_1 = (wx_df.air_temp_set_1 * 1.8) + 32
                # rename to match snotel
                wx_df = wx_df.rename(
                    columns={
                        "station": "siteName",
                        "date_time": "dateTime",
                        "air_temp_set_1": "TOBS",
                    }
                )

                sn_df = snotel_data()
                sn_df = sn_df[
                    sn_df.siteCode.isin(list(site_config["LCC"]["snotel_sites"].keys()))
                ]
                df = pd.concat((wx_df, sn_df))
                fig = px.line(
                    df,
                    x="dateTime",
                    y="TOBS",
                    color="siteName",
                    template="plotly_white",
                )
                fig.update_layout(
                    yaxis_title="Air Temp (deg F)", xaxis_title=None, legend_title=None
                )
                return fig


# with ui.navset_card_underline(title="SNOTEL Data"):
#     for id, name in snotel_sensors.items():
#         with ui.nav_panel(name):
#             @render_plotly
#             def viz():
#                 df = snotel_data()
#                 fig = px.line(df, x="dateTime", y=id, color="siteName")
#                 return fig
