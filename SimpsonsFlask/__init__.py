import logging

from flask import Flask, render_template, session, request, abort, Blueprint

from pg_shared import prepare_app
from SimpsonsFlask.dash_apps import dash_explore_categorical
from simpsons import PLAYTHING_NAME, Langstrings, core, menu

plaything_root = core.plaything_root

# Using a blueprint is the neatest way of setting up a URL path which starts with the plaything name (see the bottom, when the blueprint is added to the app)
# This strategy would also allow for a single Flask app to deliver more than one plaything, subject to some refactoring of app creation and blueprint addition.
pt_bp = Blueprint(PLAYTHING_NAME, __name__, template_folder='templates')

@pt_bp.route("/")
# Root shows set of index cards, one for each enabled plaything specification. There is no context language for this; lang is declared at specification level.
# Order of cards follows alphanum sort of the specification ids. TODO consider sort by title.
def index():
    core.record_activity("ROOT", None, session, referrer=request.referrer)

    return render_template("index_cards.html", specifications=core.get_specifications(),
                           with_link=True, url_base=plaything_root, query_string=request.query_string.decode())

@pt_bp.route("/validate")
# similar output style to root route, but performs some checks and shows error-case specifications and disabled specifications
def validate():
    core.record_activity("validate", None, session, referrer=request.referrer, tag=request.args.get("tag", None))

    return render_template("index_cards.html",
                           specifications=core.get_specifications(include_disabled=True, check_assets=["world_pop"], check_optional_assets=["about"]),
                           with_link=False)

# @pt_bp.route("/about/<specification_id>", methods=['GET'])
# def about(specification_id: str):
#     view_name = "about"

#     core.record_activity(view_name, specification_id, session, referrer=request.referrer, tag=request.args.get("tag", None))
#     spec = core.get_specification(specification_id)
#     if "about" not in spec.asset_map:
#         abort(404, "'about' is not configured")

#     langstrings = Langstrings(spec.lang)

#     return render_template("about.html",
#                            about=spec.load_asset_markdown(view_name, render=True),
#                            top_menu=spec.make_menu(menu, langstrings, plaything_root, view_name, query_string=request.query_string.decode()))

app = prepare_app(Flask(__name__), url_prefix=plaything_root)
app.register_blueprint(pt_bp, url_prefix=plaything_root)

# DASH Apps and route spec. NB these do need the URL prefix
dec_view = dash_explore_categorical.view_name
app = dash_explore_categorical.create_dash(app, f"{plaything_root}/{dec_view}/<specification_id>", f"{plaything_root}/dash/{dec_view}/")