from dash import Dash, html, dcc, dependencies
import dash_bootstrap_components as dbc
from calculator import app as calculator_app
from stats import app as stats_app
from simulation import app as simulation_app

# Initialize the main app with RTL support and dark theme
app = Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.DARKLY,
        'https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/css/bootstrap.rtl.min.css'
    ],
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
    suppress_callback_exceptions=True  # Add this line to suppress callback exceptions
)

# Custom CSS with RTL support and dark theme, combining styles from all apps
app.index_string = '''
<!DOCTYPE html>
<html dir="rtl" lang="he">
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            /* General styles */
            body { 
                direction: rtl;
                text-align: right;
                background-color: #222;
                color: white;
            }

            /* Tab styles */
            .nav-tabs {
                border-bottom-color: #444;
            }
            .nav-tabs .nav-link {
                color: #fff;
                background-color: #303030;
                border-color: #444;
                margin-right: 4px;
            }
            .nav-tabs .nav-link:hover {
                border-color: #444;
                background-color: #375a7f;
            }
            .nav-tabs .nav-link.active {
                color: #fff;
                background-color: #375a7f;
                border-color: #444;
            }

            /* Listbox styles from calculator app */
            .listbox {
                border: 1px solid #444;
                height: 300px;
                overflow-y: auto;
                background: #333;
                border-radius: 4px;
                color: white;
            }
            .listbox-item {
                padding: 8px 12px;
                cursor: pointer;
                border-bottom: 1px solid #444;
                color: white;
            }
            .listbox-item:hover {
                background-color: #444;
            }
            .listbox-item.selected {
                background-color: #375a7f;
            }

            /* Table styles */
            .table {
                color: white !important;
                background-color: #303030;
            }
            .table-striped tbody tr:nth-of-type(odd) {
                background-color: #2c2c2c;
                color: white !important;
            }
            .table-hover tbody tr:hover {
                background-color: #375a7f;
                color: white !important;
            }
            .table td, .table th {
                color: white !important;
            }

            /* Card styles */
            .card {
                background-color: #303030;
                border-color: #444;
            }
            .card-body {
                color: white;
            }

            /* Dropdown styling */
            .Select-menu-outer {
                text-align: right;
                background-color: #333 !important;
            }
            .Select-value {
                color: white !important;
                background-color: #333 !important;
            }
            .Select-value-label {
                color: white !important;
            }
            .Select-control {
                background-color: #333 !important;
                border-color: #666 !important;
            }
            .Select-placeholder {
                color: #ccc !important;
            }
            .Select.is-focused > .Select-control {
                background-color: #333 !important;
            }
            .Select-menu {
                background-color: #333 !important;
                color: white !important;
            }
            .Select-option {
                background-color: #333 !important;
                color: white !important;
            }
            .Select-option.is-focused {
                background-color: #444 !important;
            }

            /* Scrollbar styling */
            ::-webkit-scrollbar {
                width: 8px;
            }
            ::-webkit-scrollbar-track {
                background: #2a2a2a;
            }
            ::-webkit-scrollbar-thumb {
                background: #555;
                border-radius: 4px;
            }
            ::-webkit-scrollbar-thumb:hover {
                background: #666;
            }

            /* Alert styles */
            .alert-info {
                background-color: #375a7f;
                border-color: #375a7f;
                color: white;
            }

            /* Range slider styles */
            .rc-slider-rail {
                background-color: #444;
            }
            .rc-slider-track {
                background-color: #375a7f;
            }
            .rc-slider-handle {
                border-color: #375a7f;
                background-color: #375a7f;
            }
            .rc-slider-mark-text {
                color: #fff;
            }

            /* Border styles */
            .border-end {
                border-color: #444 !important;
            }
            
            /* Simulation-specific styles */
            .dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner td {
                text-align: right;
            }
            .dark-dropdown .Select-control {
                background-color: #2a2a2a !important;
                color: white !important;
                border-color: #404040 !important;
            }
            .dark-dropdown .Select-menu-outer {
                background-color: #2a2a2a !important;
                color: white !important;
                border-color: #404040 !important;
            }
            .dark-dropdown .Select-value-label {
                color: white !important;
            }
            .dark-dropdown .Select-option:hover {
                background-color: #404040 !important;
            }
            .dark-dropdown .Select.is-open > .Select-control {
                border-color: #0d6efd !important;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# Create the tab navigation
tabs = dbc.Tabs([
    dbc.Tab(label="מחשבון", tab_id="calculator", children=[
        html.Div(id="calculator-content", className="mt-4")
    ]),
    dbc.Tab(label="סטטיסטיקות", tab_id="stats", children=[
        html.Div(id="stats-content", className="mt-4")
    ]),
    dbc.Tab(label="סימולציה", tab_id="simulation", children=[
        html.Div(id="simulation-content", className="mt-4")
    ])
], id="tabs", active_tab="calculator")

# Main app layout
app.layout = dbc.Container([
    html.H1("מערכת ניהול וניתוח נתונים", className="text-center my-4"),
    tabs,
    # Add stores and other components needed by all apps
    dcc.Store(id='simulation-results-store'),
    dcc.Store(id='progress-state'),
    html.Div(id='_simulation-trigger', style={'display': 'none'})
], fluid=True)

# Register callbacks from individual apps
for callback in calculator_app.callback_map:
    if callback in app.callback_map:
        continue
    app.callback_map[callback] = calculator_app.callback_map[callback]

for callback in stats_app.callback_map:
    if callback in app.callback_map:
        continue
    app.callback_map[callback] = stats_app.callback_map[callback]

for callback in simulation_app.callback_map:
    if callback in app.callback_map:
        continue
    app.callback_map[callback] = simulation_app.callback_map[callback]

# Update tab content callback
@app.callback(
    [
        dependencies.Output("calculator-content", "children"),
        dependencies.Output("stats-content", "children"),
        dependencies.Output("simulation-content", "children")
    ],
    dependencies.Input("tabs", "active_tab")
)
def render_tab_content(active_tab):
    calculator_visible = [] if active_tab != "calculator" else [calculator_app.layout]
    stats_visible = [] if active_tab != "stats" else [stats_app.layout]
    simulation_visible = [] if active_tab != "simulation" else [simulation_app.layout]
    
    return calculator_visible, stats_visible, simulation_visible

if __name__ == '__main__':
    app.run_server(debug=True)
