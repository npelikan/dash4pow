import plotly.express as px
from pathlib import Path
import pandas as pd

from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_plotly, render_widget

import requests
from snotel_helpers import get_snotel_data
import pandas as pd
import pins
import dotenv
import os

dotenv.load_dotenv(Path(__file__).absolute().parent / ".env")

board = pins.board_connect(
    server_url=os.getenv("CONNECT_SERVER"), api_key=os.getenv("CONNECT_API_KEY")
)

# Pin config
SNOTEL_PIN_NAME = "nick.pelikan/snotel_data"
WX_PIN_NAME = "nick.pelikan/wx_data"

site_config = board.pin_read("nick.pelikan/snow_sites")

ui.page_opts(fillable=True)


forecast_r = requests.get("https://utahavalanchecenter.org/forecast/salt-lake/json")
forecast = forecast_r.json()["advisories"][0]["advisory"]

snotel_raw = board.pin_read(SNOTEL_PIN_NAME)
wx_raw = board.pin_read(WX_PIN_NAME)


with ui.sidebar():
    ui.input_slider("time", "Time (days)", 1, 30, 3)
    # ui.input_select("station", "Weather Station", choices=station_ids)
    # ui.input_selectize("snotel_station", "SNOTEL Station", choices=snotel_sites, selected="366:UT:SNTL", multiple=True)
    ui.markdown("## Forecast Issued:")
    forecast["date_issued"]
    ui.span()
    ui.tags.img(
        src=f"https://utahavalanchecenter.org/{forecast['overall_danger_rose_image']}"
    )


@reactive.Calc
def wx_data() -> pd.DataFrame:
    return wx_raw[
        wx_raw.date_time
        > pd.Timestamp.now(tz="America/Denver") - pd.Timedelta(days=input.time())
    ]


@reactive.Calc
def snotel_data() -> pd.DataFrame:
    return snotel_raw[
        snotel_raw.dateTime
        > pd.Timestamp.now(tz="America/Denver") - pd.Timedelta(days=input.time())
    ]


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
