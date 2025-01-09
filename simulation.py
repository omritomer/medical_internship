import dash
from dash import html, dcc, callback, Input, Output, State, ctx
import dash_bootstrap_components as dbc
import pandas as pd
import numpy as np
from utils import run_simulation
import traceback
from dash.exceptions import PreventUpdate
import time
from threading import Thread
from queue import Queue
import json

# Custom styles
CUSTOM_STYLES = {
    'body': {
        'direction': 'rtl',
        'textAlign': 'right',
        'backgroundColor': '#1a1a1a',
        'color': '#ffffff'
    },
    'list-group-item': {
        'backgroundColor': '#2a2a2a',
        'borderColor': '#404040',
        'color': '#ffffff',
        'cursor': 'pointer',
        'transition': 'all 0.2s ease'
    },
    'list-group-item-active': {
        'backgroundColor': '#0d6efd',
        'borderColor': '#0d6efd',
        'color': '#ffffff'
    },
    'list-group-item-hover': {
        'backgroundColor': '#3a3a3a'
    },
    'scrollable-list': {
        'height': '400px',
        'overflowY': 'auto',
        'scrollbarWidth': '8px',
        'scrollbarColor': '#555 #2a2a2a'
    },
    'table': {
        'color': '#ffffff'
    }
}

# Initialize queue for progress updates
progress_queue = Queue()
current_progress = {'value': 0}

# Initialize the Dash app with RTL support
app = dash.Dash(
    __name__, 
    external_stylesheets=[dbc.themes.DARKLY, dbc.icons.FONT_AWESOME],
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)

# Add RTL support to HTML template
app.index_string = '''
<!DOCTYPE html>
<html dir="rtl" lang="he">
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            body { 
                direction: rtl;
                text-align: right;
            }
            .Select-menu-outer {
                text-align: right;
            }
            .dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner td {
                text-align: right;
            }
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
            .dark-dropdown .Select-menu {
                background-color: #2a2a2a !important;
            }
            .dark-dropdown .Select-option {
                background-color: #2a2a2a !important;
                color: white !important;
            }
            .dark-dropdown .Select-option:hover {
                background-color: #404040 !important;
            }
            .dark-dropdown .Select-arrow {
                border-color: white transparent transparent !important;
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

def load_data():
    priorities_data = pd.read_excel("data/priority_numbers.xlsx", sheet_name=None)
    acceptance_data = pd.read_excel("data/acceptance_numbers.xlsx", sheet_name=None)
    return priorities_data, acceptance_data

def get_default_hospital_order(priorities_data):
    """Calculate the default hospital order based on first priority requests."""
    priority_totals = {}
    try:
        for year in range(2020, 2025):
            df = priorities_data.get(str(year)).copy()
            for i, row in df.iterrows():
                hospital = row.iloc[0]
                first_priority_count = float(row.iloc[1])
                if pd.notna(first_priority_count):
                    priority_totals[hospital] = priority_totals.get(hospital, 0) + first_priority_count
        
        sorted_hospitals = sorted(priority_totals.items(), key=lambda x: (-x[1], x[0]))
        return [hospital for hospital, _ in sorted_hospitals]
    except Exception as e:
        print(f"Error in get_default_hospital_order: {str(e)}")
        raise e

def get_list_item_style(is_active):
    """Combine base and active styles for list items"""
    style = CUSTOM_STYLES['list-group-item'].copy()
    if is_active:
        style.update(CUSTOM_STYLES['list-group-item-active'])
    return style

def create_circular_progress():
    """Create a circular progress indicator using Plotly"""
    return html.Div([
        dcc.Graph(
            id='progress-indicator',
            figure={
                'data': [{
                    'type': 'pie',
                    'values': [0, 100],
                    'hole': 0.7,
                    'marker': {
                        'colors': ['#0d6efd', '#2a2a2a']
                    },
                    'showlegend': False,
                    'hoverinfo': 'none',
                    'textinfo': 'none'
                }],
                'layout': {
                    'margin': dict(l=10, r=10, t=10, b=10),
                    'width': 120,
                    'height': 120,
                    'paper_bgcolor': 'rgba(0,0,0,0)',
                    'plot_bgcolor': 'rgba(0,0,0,0)',
                    'annotations': [{
                        'text': '0%',
                        'x': 0.5,
                        'y': 0.5,
                        'showarrow': False,
                        'font': {
                            'size': 20,
                            'color': 'white'
                        }
                    }]
                }
            },
            config={
                'displayModeBar': False,
                'staticPlot': True
            }
        ),
        dcc.Interval(
            id='progress-interval',
            interval=100,  # in milliseconds
            disabled=True
        ),
        dcc.Store(id='simulation-results-store'),
    ], style={'display': 'flex', 'justifyContent': 'center', 'marginTop': '1rem'})

# Load data
priorities_data, acceptance_data = load_data()

# Get initial hospital list
initial_hospitals = get_default_hospital_order(priorities_data)

# Create progress container
progress_container = html.Div([
    create_circular_progress(),
    dcc.Store(id='progress-state')
], id="progress-container")

# Layout
app.layout = dbc.Container([
    html.H1("סימולציית קבלה", className="my-4"),
    # Year and simulation controls
    dbc.Row([
        dbc.Col([
            html.Label("בחר שנה"),
            dcc.Dropdown(
                id='year-dropdown',
                options=[{'label': str(year), 'value': year} for year in range(2020, 2025)],
                value=2024,
                clearable=False,
                style={'textAlign': 'right'},
                className="mb-3 dark-dropdown",
            )
        ], width=6),
        dbc.Col([
            html.Label("מספר סימולציות"),
            dcc.Slider(
                id='simulation-slider',
                min=10,
                max=1000,
                value=100,
                step=10,
                marks={i: str(i) for i in [10, 100, 250, 500, 750, 1000]},
                className="mb-3"
            )
        ], width=6)
    ]),
    
    # Main content row
    dbc.Row([
        # Left side - Hospital list
        dbc.Col([
            html.H3("סדר עדיפויות", className="mt-4"),
            dbc.Row([
                # Hospital list
                dbc.Col([
                    html.Div(
                        id='hospital-list-container',
                        children=[
                            dbc.ListGroup([
                                dbc.ListGroupItem(
                                    f"{i+1}. {hospital}",
                                    id={'type': 'hospital-item', 'index': i},
                                    action=True,
                                    className="d-flex justify-content-between align-items-center",
                                    style=CUSTOM_STYLES['list-group-item']
                                ) for i, hospital in enumerate(initial_hospitals)
                            ], id='hospital-list')
                        ],
                        style=CUSTOM_STYLES['scrollable-list']
                    )
                ], width=9),
                # Controls column
                dbc.Col([
                    # Up/Down buttons
                    dbc.Button("↑", id="move-up-btn", className="mb-2 w-100", disabled=True),
                    dbc.Button("↓", id="move-down-btn", className="mb-2 w-100", disabled=True),
                    # Run and Stop simulation buttons
                    dbc.Button(
                        "הפעל סימולציה",
                        id="run-simulation-btn",
                        color="primary",
                        className="mt-4 w-100"
                    ),
                    dbc.Button(
                        "עצור סימולציה",
                        id="stop-simulation-btn",
                        color="danger",
                        className="mt-2 w-100",
                        disabled=True
                    ),
                    # Progress indicator
                    progress_container,
                ], width=3),
            ]),
        ], width=6),
        
        # Right side - Results
        dbc.Col([
            html.H3("תוצאות", className="mt-4"),
            html.Div(id="simulation-results")
        ], width=6)
    ]),
    html.Div(id='_simulation-trigger', style={'display': 'none'})
], fluid=True, style={'padding': '20px'})

def run_simulation_thread(year, hospital_order, n_simulations, progress_queue):
    """Run simulation in a separate thread"""
    try:
        def update_progress(value):
            progress_queue.put(value * 100)
            
        results = run_simulation(
            priorities_data=priorities_data,
            acceptance_data=acceptance_data,
            year=year,
            intern_data=hospital_order,
            n_permutations=n_simulations,
            progress_callback=update_progress
        )
        
        # Put the results in the queue
        progress_queue.put(('results', results))
        
    except Exception as e:
        progress_queue.put(('error', str(e)))

def create_progress_figure(progress):
    """Helper function to create the progress figure starting at 12 o'clock and filling clockwise"""
    # Create sequence of small segments
    n_segments = 100
    values = []
    colors = []
    
    # Calculate number of filled segments
    filled_segments = int(progress * n_segments / 100)
    
    for i in range(n_segments):
        values.append(100/n_segments)  # Equal sized segments
        # Calculate position with 12 o'clock start (rotate by -90 degrees = -25% of circle)
        adjusted_i = (i - n_segments//4) % n_segments
        if adjusted_i < filled_segments:
            colors.append('#0d6efd')  # Progress color
        else:
            colors.append('#2a2a2a')  # Background color
            
    return {
        'data': [{
            'type': 'pie',
            'values': values,
            'rotation': -90,  # Start at 12 o'clock
            'hole': 0.7,
            'direction': 'clockwise',
            'sort': False,
            'marker': {
                'colors': colors
            },
            'showlegend': False,
            'hoverinfo': 'none',
            'textinfo': 'none'
        }],
        'layout': {
            'margin': dict(l=10, r=10, t=10, b=10),
            'width': 120,
            'height': 120,
            'paper_bgcolor': 'rgba(0,0,0,0)',
            'plot_bgcolor': 'rgba(0,0,0,0)',
            'annotations': [{
                'text': f'{int(progress)}%',
                'x': 0.5,
                'y': 0.5,
                'showarrow': False,
                'font': {
                    'size': 20,
                    'color': 'white'
                }
            }]
        }
    }

# Callbacks
@callback(
    Output('hospital-list-container', 'children'),
    [Input('move-up-btn', 'n_clicks'),
     Input('move-down-btn', 'n_clicks')],
    [State({'type': 'hospital-item', 'index': dash.ALL}, 'children'),
     State({'type': 'hospital-item', 'index': dash.ALL}, 'active')]
)
def update_hospital_order(up_clicks, down_clicks, hospitals, active):
    if not ctx.triggered_id:
        raise dash.exceptions.PreventUpdate
    
    hospitals = [h[h.find(". ") + 2:] for h in hospitals]
    new_active = list(active)
    
    if True in active:
        current_idx = active.index(True)
        if ctx.triggered_id == 'move-up-btn' and current_idx > 0:
            hospitals[current_idx], hospitals[current_idx-1] = \
                hospitals[current_idx-1], hospitals[current_idx]
            new_active[current_idx], new_active[current_idx-1] = \
                False, True
        elif ctx.triggered_id == 'move-down-btn' and current_idx < len(hospitals) - 1:
            hospitals[current_idx], hospitals[current_idx+1] = \
                hospitals[current_idx+1], hospitals[current_idx]
            new_active[current_idx], new_active[current_idx+1] = \
                False, True
    
    return dbc.ListGroup([
        dbc.ListGroupItem(
            f"{i+1}. {hospital}",
            id={'type': 'hospital-item', 'index': i},
            action=True,
            active=new_active[i],
            className="d-flex justify-content-between align-items-center",
            style=get_list_item_style(new_active[i])
        ) for i, hospital in enumerate(hospitals)
    ])

@callback(
    [Output({'type': 'hospital-item', 'index': dash.ALL}, 'active'),
     Output({'type': 'hospital-item', 'index': dash.ALL}, 'style'),
     Output('move-up-btn', 'disabled'),
     Output('move-down-btn', 'disabled')],
    [Input({'type': 'hospital-item', 'index': dash.ALL}, 'n_clicks')],
    [State({'type': 'hospital-item', 'index': dash.ALL}, 'active')]
)
def update_selected_hospital(clicks, current_active):
    if not ctx.triggered_id or not any(click for click in clicks if click):
        raise dash.exceptions.PreventUpdate
    
    clicked_index = ctx.triggered_id['index']
    new_active = [False] * len(current_active)
    new_active[clicked_index] = True
    
    new_styles = [get_list_item_style(active) for active in new_active]
    
    return new_active, new_styles, clicked_index == 0, clicked_index == len(current_active) - 1

@callback(
    [Output('progress-indicator', 'figure'),
     Output('progress-interval', 'disabled'),
     Output('simulation-results-store', 'data')],
    [Input('progress-interval', 'n_intervals'),
     Input('run-simulation-btn', 'n_clicks'),
     Input('stop-simulation-btn', 'n_clicks')],
    prevent_initial_call=True
)
def update_progress(n_intervals, run_clicks, stop_clicks):
    if ctx.triggered_id == 'stop-simulation-btn':
        return create_progress_figure(0), True, None
    
    if ctx.triggered_id == 'run-simulation-btn':
        current_progress['value'] = 0
        return create_progress_figure(0), False, None
    
    # Check for new progress in queue
    while not progress_queue.empty():
        item = progress_queue.get()
        if isinstance(item, tuple):
            # This is a results or error message
            status, data = item
            if status == 'results':
                results_df = pd.DataFrame({
                    'בית חולים': data.index,
                    'אחוז קבלה': data.values.round(1).astype(str) + '%'
                })
                return create_progress_figure(100), True, results_df.to_dict('records')
            elif status == 'error':
                return create_progress_figure(0), True, {'error': data}
        else:
            # This is a progress update
            current_progress['value'] = item
    
    return create_progress_figure(current_progress['value']), False, dash.no_update

@callback(
    Output('simulation-results', 'children'),
    Input('simulation-results-store', 'data'),
    prevent_initial_call=True
)
def update_results(data):
    if not data:
        raise PreventUpdate
    
    if 'error' in data:
        return html.Div([
            html.H4("שגיאה בהרצת הסימולציה:", className="text-danger"),
            html.Pre(data['error'])
        ], className="mt-4")
    
    return dbc.Table.from_dataframe(
        pd.DataFrame(data),
        striped=True,
        bordered=True,
        hover=True,
        className="mt-4",
        style={'color': '#ffffff'}
    )

@callback(
    Output('run-simulation-btn', 'disabled'),
    Output('stop-simulation-btn', 'disabled'),
    Input('run-simulation-btn', 'n_clicks'),
    Input('stop-simulation-btn', 'n_clicks'),
    Input('simulation-results-store', 'data'),
    prevent_initial_call=True
)
def toggle_buttons(run_clicks, stop_clicks, results):
    if not run_clicks:
        raise PreventUpdate
    
    if ctx.triggered_id == 'run-simulation-btn':
        return True, False
    elif ctx.triggered_id == 'stop-simulation-btn' or results is not None:
        return False, True
    
    return dash.no_update, dash.no_update

@callback(
    Output('_simulation-trigger', 'children'),
    Input('run-simulation-btn', 'n_clicks'),
    [State('year-dropdown', 'value'),
     State('simulation-slider', 'value'),
     State({'type': 'hospital-item', 'index': dash.ALL}, 'children')],
    prevent_initial_call=True
)
def start_simulation(run_clicks, year, n_simulations, hospitals):
    if not run_clicks:
        raise PreventUpdate
    
    # Clear the queue
    while not progress_queue.empty():
        progress_queue.get()
    
    hospital_order = [h[h.find(". ") + 2:] for h in hospitals]
    
    # Start simulation in a separate thread
    thread = Thread(
        target=run_simulation_thread,
        args=(year, hospital_order, n_simulations, progress_queue)
    )
    thread.daemon = True  # Make thread daemon so it doesn't block program exit
    thread.start()
    
    return ''

if __name__ == '__main__':
    app.run_server(debug=True)