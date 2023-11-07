# import logging

from pg_shared.dash_utils import create_dash_app_util
from simpsons import core, menu, Langstrings
from flask import session

from dash import html, dcc, callback_context, no_update
import plotly.express as px
from dash.dependencies import Output, Input  #, State

view_name = "explore-categorical"  # this is required

def create_dash(server, url_rule, url_base_pathname):
    """Create a Dash view"""
    app = create_dash_app_util(server, url_rule, url_base_pathname)

    # dash app definitions goes here
    # app.config.suppress_callback_exceptions = True
    app.title = "Simpson's Paradox Categorical Exploration"

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
                        html.Label("Compare category:", id="compare_label", style={"margin-top": "50px"}),
                        dcc.Dropdown(id="compare_options", searchable=False, clearable=False, style={"margin-left": "10px"}),
                        html.Label("Show Facets:", id="facet_label", style={"margin-top": "10px"}),
                        dcc.Dropdown(value="none", id="facet_options", searchable=False, clearable=False, style={"margin-left": "10px"})
                    ], className="col-sm-3"
                ),
                html.Div(
                    [
                        dcc.Loading(
                            dcc.Graph(id="rates_chart"),
                            type="circle"
                        ),
                        dcc.Loading(
                            dcc.Graph(id="counts_chart"),
                            type="circle"
                        )
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
            # category selectors
            Output("compare_label", "children"),
            Output("compare_options", "options"),
            Output("compare_options", "value"),  # initial value comes from Specification JSON so this one must be an output.
            Output("facet_label", "children"),
            Output("facet_options", "options"),
            Output("facet_options", "value"),  # this is reset to none when compare_options changes
            # charts
            Output("rates_chart", "figure"),
            Output("counts_chart", "figure")
        ],
        [
            Input("location", "pathname"),
            Input("location", "search"),
            Input("compare_options", "value"),
            Input("facet_options", "value")
            ]
    )
    def update_chart(pathname, querystring, compare_selected, facet_selected):
        specification_id = pathname.split('/')[-1]
        tag = None
        if len(querystring) > 0:
            for param, value in [pv.split('=') for pv in querystring[1:].split("&")]:
                if param == "tag":
                    tag = value
                    break
        spec = core.get_specification(specification_id)
        langstrings = Langstrings(spec.lang)

        # the category table and configured column usage
        outcome_col = spec.detail["outcome"]
        outcome_numerator = spec.detail["outcome_numerator"]
        outcome_rate_label = spec.detail["outcome_rate_label"]
        input_count_label = spec.detail.get("input_count_label", langstrings.get("COUNT"))
        initial_variable_col = spec.detail["initial_variable"]
        category_orders = spec.detail.get("category_orders", None)
        data = spec.load_asset_dataframe("data")
        prop_categories = set(data.columns).difference({"N", outcome_col})  # the columns which the user can choose to explore.
    
        if callback_context.triggered_id == "location":
            # initial load
            compare_selected = initial_variable_col
            menu_children = spec.make_menu(menu, langstrings, core.plaything_root, view_name, query_string=querystring, for_dash=True)
            compare_options = list(prop_categories)
            output = [
                menu_children,
                spec.title,
                spec.detail.get("question", ""),
                # compare label/options
                langstrings.get("COMPARE_LABEL"),
                compare_options,
                compare_selected,
                langstrings.get("FACET_LABEL"),
            ]
        else:
            output = [no_update] * 7

        # facet dropdown depends on category selected  
        facet_options = {k: k for k in prop_categories if k != compare_selected}
        facet_options.update({"none": langstrings.get("NONE")})
        if callback_context.triggered_id == "compare_options":  # if the user changed the category then reset the facet
            facet_selected = "none"
        output += [
            facet_options,
            facet_selected
        ]

        # activity log
        # TODO find a method for capturing the initial referrer. (the referrer in a callback IS the page itself)
        core.record_activity(view_name, specification_id, session,
                             activity={"compare_selected": compare_selected, "facet_selected": facet_selected},
                             referrer="(callback)", tag=tag)

        # Plot for outcome proportions
        # wrangle the table according to drop-downs
        # collapse
        group_cols = [compare_selected, outcome_col]
        if facet_selected != "none":
            group_cols.append(facet_selected)
        props_data = data.groupby(group_cols).N.apply("sum")
        # outcome fraction (as %)
        props_data = props_data.reset_index(level=outcome_col)
        group_cols.remove(outcome_col)
        props_data = props_data.groupby(group_cols).apply(lambda x: 100 * sum(x.loc[x[outcome_col] == outcome_numerator, "N"]) / sum(x.N))
        props_data.name = "outcome_rate"
        props_data = props_data.reset_index()

        if facet_selected == "none":
            outcome_figure = px.bar(props_data.sort_values(by=compare_selected),   # sort to get consistent label ordering (may be overridden by category_orders)
                                    x=compare_selected, y="outcome_rate", category_orders=category_orders)
        else:
            outcome_figure = px.bar(props_data.sort_values(by=[compare_selected, facet_selected]),
                                    x=compare_selected, y="outcome_rate", color=facet_selected, barmode="group", category_orders=category_orders)

        outcome_figure.update_yaxes({"title": outcome_rate_label})
        outcome_figure.update_layout({"hovermode": "x", "yaxis_ticksuffix": '%'})
        outcome_figure.update_traces({"hovertemplate": f"{outcome_rate_label} = %{{y:.2f}}%"})
        output.append(outcome_figure)

        # Plot for counts
        group_cols = [compare_selected]
        if facet_selected != "none":
            group_cols.append(facet_selected)
        counts_data = data.groupby(group_cols).N.apply("sum")
        counts_data.name = "Count"
        counts_data = counts_data.reset_index()
        if facet_selected == "none":
            counts_figure = px.bar(counts_data.sort_values(by=compare_selected),  # sort to get consistent label ordering (may be overridden by category_orders)
                                   x=compare_selected, y="Count", category_orders=category_orders)
        else:
            counts_figure = px.bar(counts_data.sort_values(by=[compare_selected, facet_selected]),
                                   x=compare_selected, y="Count", color=facet_selected, barmode="group", category_orders=category_orders)
        counts_figure.update_yaxes({"title": input_count_label})
        output.append(counts_figure)

        return output

    return app.server
