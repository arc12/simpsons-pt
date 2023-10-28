import logging

from pg_shared.dash_utils import create_dash_app_util
from simpsons import core, menu, Langstrings
from flask import abort, session
import pandas as pd
from dash import html, dcc, callback_context, no_update
import plotly.express as px
from dash.dependencies import Output, Input, State

view_name = "simulate-categorical"  # this is required

def create_dash(server, url_rule, url_base_pathname):
    """Create a Dash view"""
    app = create_dash_app_util(server, url_rule, url_base_pathname)

    # dash app definitions goes here
    # app.config.suppress_callback_exceptions = True
    app.title = "Simpson's Paradox Categorical Simulation"

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

        # Input controls are generated on 1st load as they are determined by config.
        html.Div([], id="sim_params"),

        html.Div(
            [
                html.Button("", id="sim_button"),
                html.Strong(id="sim_error")
            ]
        ),

        html.Div(
            [
                html.Div(dcc.Checklist(id="sim_options"), className="col-md-2"),
                html.Div(dcc.Loading(dcc.Graph(id="rates_chart"), type="circle"), className="col-md-10")
            ], className="row"
        )

    ],
    className="wrapper"
    )
    
    # This callback handles the initial setup of the menu, langstring labels, and simulation input components, which use config values for initial settings
    @app.callback(
        [
            Output("menu", "children"),
            Output("heading", "children"),
            Output("sim_params", "children"),
            Output("sim_button", "children"),
            Output("sim_options", "options")
        ],
        [
            Input("location", "pathname"),
            Input("location", "search")
        ]
    )
    def add_sim_inputs(pathname, querystring):
        specification_id = pathname.split('/')[-1]
        tag = None
        if len(querystring) > 0:
            for param, value in [pv.split('=') for pv in querystring[1:].split("&")]:
                if param == "tag":
                    tag = value
                    break
        spec = core.get_specification(specification_id)
        langstrings = Langstrings(spec.lang)

        menu_children = spec.make_menu(menu, langstrings, core.plaything_root, view_name, query_string=querystring, for_dash=True)

        if "simulate_categories" not in spec.detail:
            return [menu_children, "Error: 'simulate_categories' missing from config", None, None, None]

        # the category table and configured column usage
        outcome_col = spec.detail["outcome"]
        sim_cols = spec.detail["simulate_categories"]
        outcome_numerator = spec.detail["outcome_numerator"]
        outcome_rate_label = spec.detail["outcome_rate_label"]
        input_count_label = spec.detail.get("input_count_label", langstrings.get("COUNT"))
        data = spec.load_asset_dataframe("category_counts")
    
        col1_sums = data.groupby(sim_cols[0]).N.sum()
        col2_values = list(data[sim_cols[1]].unique())
        col2_values.sort()
        col2_pc_category = col2_values[0]
        col2_pc = pd.pivot_table(data, values="N", index=sim_cols[0], columns=sim_cols[1]).apply(lambda x: int(100 * x[col2_pc_category] / sum(x)), axis=1)
        if len(col2_values) != 2:
            return [menu_children, "Error: 'simulate_categories' is mis-specified", None, None, None]
        base_pc = pd.pivot_table(data, values="N", index=sim_cols, columns=outcome_col).apply(lambda x: 100 * x[outcome_numerator] / sum(x), axis=1)
        # generally round the percentages to integers but some situations may have very small values
        if base_pc.median() > 20:
            base_pc = base_pc.round(0).astype(int)
        else:
            base_pc = base_pc.round(2)

        # I initially tried using Bootstrap grid layout but React.js had problems on the client side. Might be my mis-use but still... now using tables
        # heading - col widths should match the parameter input structure
        sim_params_header = html.Tr(
            [
                html.Th(sim_cols[0]),  # for row label (=col1 value)
                html.Th(input_count_label),  # count against that category
                html.Th(f"{sim_cols[1]}: % {col2_pc_category}"),  # for col2 proportion slider
                html.Th(outcome_rate_label + ": " + ", ".join(col2_values))  # for outcome percentages for each col1:col2 combination

            ]
        )

        # !! text input types will need validating as numbers in simulation
        # one row for each value of col1
        sim_params_rows = []
        for cat1, cnt1 in col1_sums.items():
            cells = [
                html.Th(cat1),
                html.Td(dcc.Input(type="text", value=cnt1, size=5, id="c1_" + cat1.replace(" ", "_"))),  # count for col1 category
                html.Td(dcc.Input(type="range", value=col2_pc.loc[cat1], min=1, max=100, id=f"c2_{cat1.replace(' ', '_')}~{col2_pc_category}")),  # col2 proportion slider
                # category pair base rates
                html.Td([dcc.Input(type="text", value=base_pc.loc[(cat1, cat2)], size=6, id=f"br_{cat1.replace(' ', '_')}~{cat2.replace(' ', '_')}") for cat2 in col2_values])
            ]
            sim_params_rows.append(html.Tr(cells))
        
        sim_params = html.Table([
            html.Thead(sim_params_header),
            html.Tbody(sim_params_rows)
        ], className="table")

        output = [
            menu_children,
            spec.title,
            sim_params,
            langstrings.get("SIMULATE"),
            {"facet": langstrings.get("FACET_LABEL")}  # sim options
        ]

        return output

    @app.callback(
        [
            Output("rates_chart", "figure"),
            Output("sim_error", "children")
        ],
        [
            Input("location", "pathname"),
            Input("location", "search"),
            State("sim_params", "children"),
            Input("sim_options", "value"),
            Input("sim_button", "n_clicks")
        ],
        prevent_initial_call = True
    )
    def update_chart(pathname, querystring, sim_params, sim_options, n_clicks):
        specification_id = pathname.split('/')[-1]
        tag = None
        if len(querystring) > 0:
            for param, value in [pv.split('=') for pv in querystring[1:].split("&")]:
                if param == "tag":
                    tag = value
                    break
        spec = core.get_specification(specification_id)
        # langstrings = Langstrings(spec.lang)
    
        # the category table and configured column usage
        outcome_col = spec.detail["outcome"]
        outcome_numerator = spec.detail["outcome_numerator"]
        outcome_rate_label = spec.detail["outcome_rate_label"]
        initial_variable_col = spec.detail["initial_variable"]
        category_orders = spec.detail.get("category_orders", None)
        sim_cols = spec.detail.get("simulate_categories", None)

        if len([] if sim_params is None else sim_params) == 0:
            # pre-sim, show blank bar chart with correct axis labels
            dummy_fig = px.bar(pd.DataFrame(columns=[initial_variable_col, "outcome_rate"]), x=initial_variable_col, y="outcome_rate")
            dummy_fig.update_yaxes({"title": outcome_rate_label})
            return dummy_fig, ""

        facet = "facet" in ([] if sim_options is None else sim_options)

        # extract the simulation parameters from the HTML mess! This ABSOLUTELY depends on the structure, although the ids etc would allow a semantic extraction
        has_error = None  # TODO add check numeric and range -  add some text next to button to give warning when input data is invalid (give cat 1 value)
        data_d = []
        for row in sim_params["props"]["children"][1]["props"]["children"]:  # [1] picks out <tbody>
            try:
                cells = row["props"]["children"]
                cat1 = cells[0]["props"]["children"]
                cat1_cnt = float(cells[1]["props"]["children"]["props"]["value"])
                cat2_pc = float(cells[2]["props"]["children"]["props"]["value"])
                col2_pc_category = cells[2]["props"]["children"]["props"]["id"].split("~")[1]  # extract of category for col2 ensures no accidental category transposition
                base_rates = {ri["props"]["id"].split("~")[1]: float(ri["props"]["value"])  for ri in cells[3]["props"]["children"]}
                # list of dicts with keys matching the CSV headers in the source data
                for cat2, base_rate in base_rates.items():
                    cat2_prop = 0.01 * (cat2_pc if cat2 == col2_pc_category else (100 - cat2_pc))
                    # outcome = outcome_numerator
                    data_d.append({
                        sim_cols[0]: cat1,
                        sim_cols[1]: cat2,
                        outcome_col: outcome_numerator,
                        "N": cat1_cnt * cat2_prop * 0.01 * base_rate
                    })
                    # outcome = not
                    data_d.append({
                        sim_cols[0]: cat1,
                        sim_cols[1]: cat2,
                        outcome_col: "not",
                        "N": cat1_cnt * cat2_prop * 0.01 * (100 - base_rate)
                    })
            except Exception as ex:
                # we will assume this is normally a parameter entry issue but log anyway
                has_error = f"Sim parameter error for: {cat1}."
                logging.warn(f"{has_error}\n{ex}")
        
        # EXIT IF ERROR
        if has_error is not None:
            return no_update, has_error

        data = pd.DataFrame(data_d)

        if not facet:
            data = data.groupby([sim_cols[1], outcome_col]).N.apply("sum")
            plot_data = pd.pivot_table(data.reset_index(), values="N", index=sim_cols[1], columns=outcome_col).apply(lambda x: 100 * x[outcome_numerator] / sum(x), axis=1)
            plot_data.name = "outcome_rate"  # Series
            outcome_figure = px.bar(plot_data.reset_index().sort_values(by=sim_cols[1]),   # sort to get consistent label ordering (may be overridden by category_orders)
                                x=sim_cols[1], y="outcome_rate", category_orders=category_orders)
        else:
            plot_data = pd.pivot_table(data, values="N", index=sim_cols, columns=outcome_col).apply(lambda x: 100 * x[outcome_numerator] / sum(x), axis=1)
            plot_data.name = "outcome_rate"  # Series
            outcome_figure = px.bar(plot_data.reset_index().sort_values(by=[sim_cols[1], sim_cols[0]]),   # sort to get consistent label ordering (may be overridden by category_orders)
                                x=sim_cols[1], y="outcome_rate", color=sim_cols[0], barmode="group", category_orders=category_orders)

        outcome_figure.update_yaxes({"title": outcome_rate_label})
        outcome_figure.update_layout({"hovermode": "x", "yaxis_ticksuffix": '%'})
        outcome_figure.update_traces({"hovertemplate": f"{outcome_rate_label} = %{{y:.2f}}%"})

        # activity log
        core.record_activity(view_name, specification_id, session,
                             activity={"has_error": has_error},  # TODO add some info? All of the params?
                             referrer="(callback)", tag=tag)



        return outcome_figure, ""

    return app.server
