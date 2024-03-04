from pathlib import Path

import pandas as pd
from modules import windrose_ui, windrose_server, timeseries_ui, timeseries_server

from shiny import App, Inputs, Outputs, Session, reactive, ui, render, module

import requests
import pins
import dotenv
import os

dotenv.load_dotenv(Path(__file__).absolute().parent / ".env")


# Pin config
SNOTEL_PIN_NAME = "nick.pelikan/snotel_data"
WX_PIN_NAME = "nick.pelikan/wx_data"

board = pins.board_connect(
    server_url=os.getenv("CONNECT_SERVER"), api_key=os.getenv("CONNECT_API_KEY")
)

site_config = board.pin_read("nick.pelikan/snow_sites")

forecast_r = requests.get("https://utahavalanchecenter.org/forecast/salt-lake/json")
forecast = forecast_r.json()["advisories"][0]["advisory"]


def pin_check(board, pin_name):
    meta = board.pin_meta(pin_name)
    return meta.pin_hash


def poll_snotel():
    return pin_check(board=board, pin_name=SNOTEL_PIN_NAME)


@reactive.poll(poll_snotel, 900)
def snotel_df() -> pd.DataFrame:
    return board.pin_read(SNOTEL_PIN_NAME)


def poll_wx():
    return pin_check(board=board, pin_name=WX_PIN_NAME)


@reactive.poll(poll_snotel, 900)
def wx_df() -> pd.DataFrame:
    return board.pin_read(WX_PIN_NAME)


@module.ui
def canyon_ui(canyon_name):
    canyon_config = site_config[canyon_name]
    out = ui.nav_panel(
        canyon_name,
        ui.layout_columns(
            *(
                windrose_ui(f"{k}_{canyon_name}", name=v)
                for k, v in canyon_config["wx_stations"].items()
            ),
            fill=False,
            height="300px",
        ),
        timeseries_ui(f"{canyon_name}_ts"),
    )
    return out


app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.input_slider("time", "Time (days)", 1, 30, 3),
        # ui.input_select("station", "Weather Station", choices=station_ids)
        # ui.input_selectize("snotel_station", "SNOTEL Station", choices=snotel_sites, selected="366:UT:SNTL", multiple=True)
        ui.markdown("## Forecast Issued:"),
        forecast["date_issued"],
        ui.span(),
        ui.tags.img(
            src=f"https://utahavalanchecenter.org/{forecast['overall_danger_rose_image']}"
        ),
    ),
    ui.navset_tab(*(canyon_ui(id=k, canyon_name=k) for k in site_config.keys())),
)


@module.server
def canyon_server(input, output, session, canyon_name, wx_filtered, snotel_filtered):

    canyon_config = site_config[canyon_name]
    [
        windrose_server(f"{k}_{canyon_name}", wx_df=wx_filtered, station_id=k)
        for k, v in canyon_config["wx_stations"].items()
    ]
    timeseries_server(
        f"{canyon_name}_ts",
        wx_df=wx_filtered,
        snotel_df=snotel_filtered,
        canyon_config=canyon_config,
    )


def server(input: Inputs, output: Outputs, session: Session):
    @reactive.calc
    def wx_filtered():
        raw = wx_df()
        return raw[
            raw.date_time
            > pd.Timestamp.now(tz="America/Denver") - pd.Timedelta(days=input.time())
        ]

    @reactive.calc
    def snotel_filtered():
        raw = snotel_df()
        return raw[
            raw.dateTime.dt.tz_localize(tz="America/Denver")
            > pd.Timestamp.now(tz="America/Denver") - pd.Timedelta(days=input.time())
        ]

    [
        canyon_server(
            id=k,
            canyon_name=k,
            wx_filtered=wx_filtered,
            snotel_filtered=snotel_filtered,
        )
        for k in site_config.keys()
    ]


app = App(app_ui, server)
