# import logging

from pg_shared.dash_utils import create_dash_app_util
from simpsons import core, menu, Langstrings
from flask import session

from dash import html, dcc, callback_context, no_update
import plotly.express as px
from dash.dependencies import Output, Input  #, State

view_name = "explore-categorical"

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
                        html.Label("Compare category:", id="rate_compare_label", style={"margin-top": "50px"}),
                        dcc.Dropdown(id="rate_compare_options", searchable=False, clearable=False, style={"margin-left": "10px"}),
                        html.Label("Show Facets:", id="rate_facet_label", style={"margin-top": "10px"}),
                        dcc.Dropdown(value="none", id="rate_facet_options", searchable=False, clearable=False, style={"margin-left": "10px"})
                    ], className="col-sm-3"
                ),
                html.Div(
                    [
                        dcc.Loading(
                            dcc.Graph(id="outcome_chart"),
                            type="circle"
                        )
                    ], className="col"
                )
            ], className="row"
        ),

        # Count Breakdown
        html.Div(
            [
                html.Div(
                    [
                        html.Label("Show:", id="show_label", style={"margin-top": "50px"}),
                        dcc.Dropdown(id="show_options", searchable=False, clearable=False, style={"margin-left": "10px"}),
                        html.Label("Filter on:", id="filter_label", style={"margin-top": "10px"}),
                        dcc.Dropdown(id="filter_options", searchable=False, clearable=False, style={"margin-left": "10px"}),
                        html.Label("="),
                        dcc.Dropdown(value="none", id="filter_category", searchable=False, clearable=False, style={"margin-left": "10px"})
                    ], className="col-sm-3"
                ),
                html.Div(
                    [
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
            # top chart controls = outcome props
            Output("rate_compare_label", "children"),
            Output("rate_compare_options", "options"),
            Output("rate_compare_options", "value"),  # initial value comes from Specification JSON so this one must be an output.
            Output("rate_facet_label", "children"),
            Output("rate_facet_options", "options"),
            Output("rate_facet_options", "value"),  # this is reset to none when rate_compare_options changes
            # bottom chart controls = counts
            Output("show_label", "children"),
            Output("show_options", "options"),
            Output("show_options", "value"),
            Output("filter_label", "children"),
            Output("filter_options", "options"),
            Output("filter_options", "value"),
            Output("filter_category", "options"),
            Output("filter_category", "value"),
            # charts
            Output("outcome_chart", "figure"),
            Output("counts_chart", "figure")
        ],
        [
            Input("location", "pathname"),
            Input("location", "search"),
            Input("rate_compare_options", "value"),
            Input("rate_facet_options", "value"),
            Input("show_options", "value"),
            Input("filter_options", "value"),
            Input("filter_category", "value")
            ]
    )
    def update_chart(pathname, querystring, rate_compare_selected, rate_facet_selected, show_selected, filter_selected, filter_category):
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
        initial_variable_col = spec.detail["initial_variable"]
        category_orders = spec.detail.get("category_orders", None)
        data = spec.load_asset_dataframe("category_counts")
        prop_categories = set(data.columns).difference({"N", outcome_col})  # the columns which the user can choose to explore.
    
        if callback_context.triggered_id == "location":
            # initial load
            rate_compare_selected = initial_variable_col
            menu_children = spec.make_menu(menu, langstrings, core.plaything_root, view_name, query_string=querystring, for_dash=True)
            rate_compare_options = list(prop_categories)
            output = [
                menu_children,
                spec.title,
                spec.detail.get("question", ""),
                # compare label/options
                langstrings.get("COMPARE_LABEL"),
                rate_compare_options,
                rate_compare_selected,
                langstrings.get("FACET_LABEL"),
            ]
        else:
            output = [no_update] * 7

        # facet dropdown depends on category selected  
        rate_facet_options = {k: k for k in prop_categories if k != rate_compare_selected}
        rate_facet_options.update({"none": langstrings.get("NONE")})
        if callback_context.triggered_id == "rate_compare_options":  # if the user changed the category then reset the facet
            rate_facet_selected = "none"
        output += [
            rate_facet_options,
            rate_facet_selected
        ]

        cnt_categories = list(data.columns)  # the columns which the user can choose to explore.
        cnt_categories.remove("N")
        if callback_context.triggered_id == "location":
            # initial load pt 2, labels for counts block and primary drop-down
            show_selected = outcome_col
            filter_selected = initial_variable_col
            output += [
                langstrings.get("SHOW_LABEL"),
                cnt_categories,
                show_selected,
                langstrings.get("FILTER_ON_LABEL")
            ]
        else:
            output += [no_update] * 4

        # filter-on dropdown depends on primary col selection  
        filter_options = {k: k for k in cnt_categories if k != show_selected}
        if callback_context.triggered_id == "show_options":  # if the user changed the category then reset the filter-on col
            filter_selected = cnt_categories[0]
        filter_categories = list(data[filter_selected].unique())
        if (filter_category is None) or (callback_context.triggered_id == "filter_options"):
            filter_category = filter_categories[0] 
        output += [
            filter_options,
            filter_selected,
            filter_categories,
            filter_category
        ]

        # activity log
        # TODO find a method for capturing the initial referrer. (the referrer in a callback IS the page itself)
        core.record_activity(view_name, specification_id, session,
                             activity={"rate_compare_selected": rate_compare_selected, "rate_facet_selected": rate_facet_selected},
                             referrer="(callback)", tag=tag)

        # Plot for outcome proportions
        # wrangle the table according to drop-downs
        # collapse
        group_cols = [rate_compare_selected, outcome_col]
        if rate_facet_selected != "none":
            group_cols.append(rate_facet_selected)
        props_data = data.groupby(group_cols).N.apply("sum")
        # outcome fraction (as %)
        props_data = props_data.reset_index(level=outcome_col)
        group_cols.remove(outcome_col)
        props_data = props_data.groupby(group_cols).apply(lambda x: 100 * sum(x.loc[x[outcome_col] == outcome_numerator, "N"]) / sum(x.N))
        props_data.name = "outcome_rate"
        props_data = props_data.reset_index()

        if rate_facet_selected == "none":
            props_data.sort_values(by=rate_compare_selected, inplace=True)
            outcome_figure = px.bar(props_data, x=rate_compare_selected, y="outcome_rate", category_orders=category_orders)
        else:
            props_data.sort_values(by=[rate_compare_selected, rate_facet_selected], inplace=True)
            outcome_figure = px.bar(props_data, x=rate_compare_selected, y="outcome_rate", color=rate_facet_selected, barmode="group", category_orders=category_orders)

        outcome_figure.update_yaxes({"title": outcome_rate_label})
        outcome_figure.update_layout({"hovermode": "x", "yaxis_ticksuffix": '%'})
        outcome_figure.update_traces({"hovertemplate": f"{outcome_rate_label} = %{{y:.2f}}%"})
        output.append(outcome_figure)

        # Plot for counts
        filtered_data = data[data[filter_selected] == filter_category]
        counts_figure = px.histogram(filtered_data, x=show_selected, y="N")
        counts_figure.update_yaxes({"title": langstrings.get("COUNT")})
        output.append(counts_figure)

        return output

    return app.server
