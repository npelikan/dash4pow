from typing import Callable

import pandas as pd
import plotly.express as px

from shiny import Inputs, Outputs, Session, module, render, ui, reactive
from shinywidgets import render_plotly, output_widget, render_widget


@module.ui
def windrose_ui(name=""):
    return ui.card(ui.card_header(name), output_widget("plot"))


@module.server
def windrose_server(input, output, session, wx_df, station_id=""):
    @render_widget
    def plot():
        df = wx_df()
        df = df[df.station_id == station_id]
        df = df[
            df.date_time > pd.Timestamp.now(tz="America/Denver") - pd.Timedelta(days=3)
        ]
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


@module.ui
def timeseries_ui():
    return ui.navset_card_pill(
        ui.nav_panel("SWEq", output_widget("swe_plot")),
        ui.nav_panel("Temp", output_widget("temp_plot")),
    )


@module.server
def timeseries_server(input, output, session, wx_df, snotel_df, canyon_config):
    @render_widget
    def swe_plot():
        df = snotel_df()
        snotel_sites = list(canyon_config["snotel_sites"].keys())
        fig = px.line(
            df[df.siteCode.isin(snotel_sites)],
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

    @render_widget
    def temp_plot():
        wx_data = wx_df()
        wx_data = wx_data[
            wx_data.station_id.isin(list(canyon_config["wx_stations"].keys()))
        ][["station", "date_time", "air_temp_set_1"]]
        # convert to F
        wx_data.air_temp_set_1 = (wx_data.air_temp_set_1 * 1.8) + 32
        # rename to match snotel
        wx_data = wx_data.rename(
            columns={
                "station": "siteName",
                "date_time": "dateTime",
                "air_temp_set_1": "TOBS",
            }
        )

        sn_df = snotel_df()
        sn_df = sn_df[sn_df.siteCode.isin(list(canyon_config["snotel_sites"].keys()))]
        df = pd.concat((wx_data, sn_df))
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
