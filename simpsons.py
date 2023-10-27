from pg_shared import LangstringsBase, Core

# Some central stuff which is used by both plain Flask and Dash views.

PLAYTHING_NAME = "simpsons"

class Langstrings(LangstringsBase):
    langstrings = {
        "MENU_EXPLORE": {
            "en": "Explore"
        },
        "MENU_ABOUT": {
            "en": "About"
        },
        "MENU_SIMULATE": {
            "en": "Simulate"
        },
        "COMPARE_LABEL": {
            "en": "Compare category"
        },
        "FACET_LABEL": {
            "en": "Show Facets"
        },
        "NONE": {
            "en": "None"
        },
        "COUNT": {
            "en": "Count"
        },
        "SIMULATE": {
            "en": "Simulate"
        },
    }

# The menu is only shown if menu=1 in query-string AND only for specific views. Generally make the menu contain all views it is coded for
# Structure is view: LANGSTRING_KEY,
# - where "view" is the part after the optional plaything_root (and before <specification_id> if present) in the URL. e.g. "about" is a view.
# - and LANGSTRING_KEY is defined in the Langstrings class above
# The ROOT for a plaything is the index cards page and should not be in the menu.
# This defines the default order and the maximum scope of views in the meny. A plaything specification may override.
menu = {
    "explore-categorical": "MENU_EXPLORE",
    "explore-continuous": "MENU_EXPLORE",
    "simulate-categorical": "MENU_SIMULATE"
}

# This sets up core features such as logger, activity recording, core-config.
core = Core(PLAYTHING_NAME)