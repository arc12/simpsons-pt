# Simpson's Paradox
_This documents the configuration files which allow the Plaything to be customised and notes how they relate to various useage scenarios._

Plaything name: simpsons

## Plaything Specification
Refer to the README in the pg_shared repository/folder for common elements; this README refers only to the elements which are specific to the Simpson's Paradox Plaything.
The Specifications folder is Config/simpsons.

Available views:
- "explore-categorical"
- "simulate-categorical"
- "explore-continuous"

The Specification determines which of categorical vs continuous views are valid; be sure to set the __menu__ items correctly.

Notes:
- Simulate is only available for the categorical case and takes its starting parameter values from the CSV file which defines the Explore case, although this need not be included in the menu.
- The menu label used for both Explore views is the same but the URL differs; the menu does not include "Categorical" etc.

### "detail" - categorical
- question [simple text]: is the optional "poser" question to present on the Explore view.

These entries refer to column headings in the source data (see __asset_map__):
- outcome [simple text]: the column which is the outcome of interest, aka the dependent variable. This should contain only two values.
- outcome_numerator [simple text]: the category value in the __outcome__ column which will be the numerator when computing % outcomes.
- outcome_rate_label [simple text]: the label to use in the plots for the % outcome rate corresponding with __outcome_numerator__.
- input_count_label [simple text]: the label to use in the plots showing counts by input category/ies (summed over outcomes)
- initial_variable [simple text]: the column which will be shown in the initial plot as the independent variable, i.e. when this is plotted, the Simpson's Paradox is shown.
- category_orders [structure]: an optional setting to control the order in which categories appear on plot axes.
- simulate_categories [list of strings]: if the simulation view is to be used, this must be an ordered list of the two variables to use. The second MUST be a binary and is presented as a slider to control the balance of the two categories. It will normally be the same as __initial_variable__ so that the simulation matches the poser question. The first may be a category-type with multiple possible values; the user enters numbers of individuals (etc) for each of these. This is the variable which resolves the 'paradox'.

__category_orders__ may be omitted and only need contain entries for those columns for which ordering is desired. It is structured:
- {column heading}: list of categories. Example, where "Age" is a column heading: "category_orders": {"Age": ["< 50", "50 +"]}

### "detail" - continuous
- question: as above
- continuous_cols [list with two members]: the column headings for the two continuous variables in the CSV file
- category_orders: as above

### "asset_map"
The source data is declared differently for categorical and continuous cases:
- For categorical cases, the CSV must contain a column with heading "N" which is the tally and at least the columns declared in "outcome" and "initial_variable" entries in __detail__.
- For continuous cases, it must contain both of the __continuous_cols__ and at least one categorical column.

In both use "data" as the key in the __asset_map__ and follow the convention that capitalised words are used for headings and lower-case words (except for abbreviated names) for category values.
