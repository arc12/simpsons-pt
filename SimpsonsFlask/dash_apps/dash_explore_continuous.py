# import logging

from pg_shared.dash_utils import create_dash_app_util
from simpsons import core, menu, Langstrings
from flask import session

from dash import html, dcc, callback_context, no_update
import plotly.graph_objects as go
from dash.dependencies import Output, Input  #, State

from sklearn.linear_model import LinearRegression

import numpy as np
from numpy.random import multivariate_normal
import pandas as pd

view_name = "explore-continuous"  # this is required

def create_dash(server, url_rule, url_base_pathname):
    """Create a Dash view"""
    app = create_dash_app_util(server, url_rule, url_base_pathname)

    # dash app definitions goes here
    # app.config.suppress_callback_exceptions = True
    app.title = "Simpson's Paradox Continuous Exploration"

    app.layout = html.Div([
        dcc.Location(id="location"),
        html.Div(id="menu"),
        html.Div(
            [
                html.H1("", id="heading", className="header-title"),
                html.P(html.Strong("", id="question"))
            ],
            className="header"
        ),

        # Outcome Proportion
        html.Div(
            [
                html.Div(
                    [
                        html.Label("Group by:", id="group_label", style={"margin-top": "50px"}),
                        dcc.Dropdown(value="none", id="group_options", searchable=False, clearable=False, style={"margin-left": "10px"})
                    ], className="col-sm-3"
                ),
                html.Div(
                    [
                        dcc.Loading(dcc.Graph(id="chart"), type="circle")
                    ], className="col"
                )
            ], className="row"
        )

    ],
    className="wrapper"
    )
    
    # This callback handles: A) initial setup of the menu, langstring labels, drop-down options (also langstrings) AND B) the chart.
    # The callback_context is used to control whether or not A updates occur, as this should only occur on initial page load.
    # Doing this saves having two call-backs on the first page load, one for each of A and B
    @app.callback(
        [
            Output("menu", "children"),
            Output("heading", "children"),
            Output("question", "children"),
            # group by selector
            Output("group_label", "children"),
            Output("group_options", "options"),
            # charts
            Output("chart", "figure")
        ],
        [
            Input("location", "pathname"),
            Input("location", "search"),
            Input("group_options", "value")
            ]
    )
    def update_chart(pathname, querystring, group_selected):
        specification_id = pathname.split('/')[-1]
        tag = None
        if len(querystring) > 0:
            for param, value in [pv.split('=') for pv in querystring[1:].split("&")]:
                if param == "tag":
                    tag = value
                    break
        spec = core.get_specification(specification_id)
        langstrings = Langstrings(spec.lang)

        # config/data
        continuous_cols = spec.detail["continuous_cols"]
        data = spec.load_asset_dataframe("data")
        group_options = {k: k for k in set(data.columns).difference(set(continuous_cols))}  # the columns which the user can choose to group by.
        group_options["none"] = langstrings.get("NONE")

    
        if callback_context.triggered_id == "location":
            # initial load
            menu_children = spec.make_menu(menu, langstrings, core.plaything_root, view_name, query_string=querystring, for_dash=True)
            output = [
                menu_children,
                spec.title,
                spec.detail.get("question", ""),
                langstrings.get("GROUP_BY"),
                group_options
            ]
        else:
            output = [no_update] * 5

        def fit(df):
            lm = LinearRegression(fit_intercept=True)
            X, y = df[continuous_cols[0]].values.reshape(-1, 1), df[continuous_cols[1]].values
            lm.fit(X, y)
            min_x, max_x = min(X)[0], max(X)[0]
            min_x_y, max_x_y = lm.predict(np.array([min_x, max_x]).reshape(-1, 1))
            return [min_x, max_x], [min_x_y, max_x_y]

        if group_selected == "none":
            lm_fit = fit(data)
            traces = [
                go.Scatter(x=data[continuous_cols[0]], y=data[continuous_cols[1]], mode="markers", showlegend=False),
                go.Scatter(x=lm_fit[0], y=lm_fit[1], mode = "lines", name="fit", line={"color": "black", "dash": "dot"}, showlegend=False)
            ]
        else:
            colours = ["#636EFA", "#EF553B", "#00CC96", "#AB63FA", "#FFA15A", "#19D3F3", "#FF6692", "#B6E880", "#FF97FF", "#FECB52"]
            traces = []
            col_ix = 0
            for cat, cat_data in data.groupby(group_selected):
                lm_fit = fit(cat_data)
                traces.append(go.Scatter(x=cat_data[continuous_cols[0]], y=cat_data[continuous_cols[1]], mode="markers", marker_color=colours[col_ix], showlegend=True, name=cat))
                traces.append(go.Scatter(x=lm_fit[0], y=lm_fit[1], mode = "lines", name=f"fit_{cat}", line={"color": "black", "dash": "dot"}, showlegend=False))
                col_ix = (col_ix + 1) % len(colours)

        output.append(
            go.Figure(
                data=traces,
                layout=go.Layout(xaxis={"title": continuous_cols[0]}, yaxis={"title": continuous_cols[1]}, legend={"title": group_selected}, margin_t=55, height=600)
            )
        )

        # activity log
        # TODO find a method for capturing the initial referrer. (the referrer in a callback IS the page itself)
        core.record_activity(view_name, specification_id, session,
                             activity={"group_selected": group_selected},
                             referrer="(callback)", tag=tag)

        return output

    return app.server
