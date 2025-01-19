from dash import html, dcc, callback, Input, Output, State, ctx
import dash_bootstrap_components as dbc
import pandas as pd
import numpy as np
from api import run_simulation
import traceback
from dash.exceptions import PreventUpdate
import time
from threading import Thread
from queue import Queue
import json
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize queue for progress updates
progress_queue = Queue()
current_progress = {'value': 0}

# Custom styles
CUSTOM_STYLES = {
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

def init_simulation(priorities_data, acceptance_data):
    """Initialize the simulation component"""
    
    # Get initial hospital list
    initial_hospitals = get_default_hospital_order(priorities_data)

    # Create progress container
    progress_container = html.Div([
        create_circular_progress(),
        dcc.Store(id='progress-state')
    ], id="progress-container")

    # Layout
    layout = dbc.Container([
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

    return layout

def run_simulation_thread(priorities_data, acceptance_data, year, hospital_order, n_simulations, progress_queue):
    """Run simulation in a separate thread"""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Starting simulation thread: year={year}, n_simulations={n_simulations}")
        logger.info(f"Hospital order: {hospital_order}")
        
        def update_progress(value):
            logger.info(f"Progress update: {value*100:.1f}%")
            try:
                progress_queue.put(('progress', value * 100))
                logger.info("Progress successfully queued")
            except Exception as e:
                logger.error(f"Failed to queue progress: {str(e)}")
        
        logger.info("Running simulation...")
        results = run_simulation(
            priorities_data=priorities_data,
            acceptance_data=acceptance_data,
            year=year,
            intern_data=hospital_order,
            n_permutations=n_simulations,
            progress_callback=update_progress
        )
        
        logger.info("Simulation completed, converting results")
        logger.info(f"Results index: {results.index.tolist()}")
        
        # Convert results to a format that can be serialized
        results_dict = {
            'בית חולים': results.index.tolist(),
            'אחוז קבלה': results.values.round(1).astype(str) + '%'
        }
        
        logger.info("Sending results to queue")
        logger.info(f"Results dict: {results_dict}")
        progress_queue.put(('results', results_dict))
        logger.info("Results successfully queued")
        
    except Exception as e:
        logger.error(f"Error in simulation thread: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        progress_queue.put(('error', str(e)))

def create_progress_figure(progress):
    """Helper function to create the progress figure"""
    n_segments = 100
    values = []
    colors = []
    
    filled_segments = int(progress * n_segments / 100)
    
    for i in range(n_segments):
        values.append(100/n_segments)
        adjusted_i = (i - n_segments//4) % n_segments
        if adjusted_i < filled_segments:
            colors.append('#0d6efd')
        else:
            colors.append('#2a2a2a')
            
    return {
        'data': [{
            'type': 'pie',
            'values': values,
            'rotation': -90,
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

def safe_queue_put(queue, item):
    try:
        queue.put_nowait(item)
    except Exception as e:
        print(f"Error putting item in queue: {str(e)}")

def safe_queue_get(queue):
    try:
        return queue.get_nowait()
    except Exception as e:
        print(f"Error getting item from queue: {str(e)}")
        return None

def register_callbacks(app, priorities_data=None, acceptance_data=None):
    """Register all callbacks for the simulation component"""
    # Store data for use in callbacks
    if priorities_data is None or acceptance_data is None:
        raise ValueError("Both priorities_data and acceptance_data must be provided")

    from dash import Input, Output, State, ALL, ctx
    from dash.exceptions import PreventUpdate
    import pandas as pd
    from threading import Thread
    import dash_bootstrap_components as dbc
    import traceback

    
    @app.callback(
        Output('hospital-list-container', 'children'),
        [Input('move-up-btn', 'n_clicks'),
         Input('move-down-btn', 'n_clicks')],
        [State({'type': 'hospital-item', 'index': ALL}, 'children'),
         State({'type': 'hospital-item', 'index': ALL}, 'active')]
    )
    def update_hospital_order(up_clicks, down_clicks, hospitals, active):
        if not ctx.triggered_id:
            raise PreventUpdate
        
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

    @app.callback(
        [Output({'type': 'hospital-item', 'index': ALL}, 'active'),
         Output({'type': 'hospital-item', 'index': ALL}, 'style'),
         Output('move-up-btn', 'disabled'),
         Output('move-down-btn', 'disabled')],
        [Input({'type': 'hospital-item', 'index': ALL}, 'n_clicks')],
        [State({'type': 'hospital-item', 'index': ALL}, 'active')]
    )
    def update_selected_hospital(clicks, current_active):
        if not ctx.triggered_id or not any(click for click in clicks if click):
            raise PreventUpdate
        
        clicked_index = ctx.triggered_id['index']
        new_active = [False] * len(current_active)
        new_active[clicked_index] = True
        
        new_styles = [get_list_item_style(active) for active in new_active]
        
        return new_active, new_styles, clicked_index == 0, clicked_index == len(current_active) - 1

    @app.callback(
        [Output('progress-indicator', 'figure'),
         Output('progress-interval', 'disabled'),
         Output('simulation-results-store', 'data')],
        [Input('progress-interval', 'n_intervals'),
         Input('run-simulation-btn', 'n_clicks'),
         Input('stop-simulation-btn', 'n_clicks')],
        prevent_initial_call=True
    )
    def update_progress(n_intervals, run_clicks, stop_clicks):
        logger.info(f"Update progress callback triggered: intervals={n_intervals}, run_clicks={run_clicks}, stop_clicks={stop_clicks}")
        
        if ctx.triggered_id == 'stop-simulation-btn':
            logger.info("Stop button clicked")
            return create_progress_figure(0), True, None
        
        if ctx.triggered_id == 'run-simulation-btn':
            logger.info("Run button clicked")
            current_progress['value'] = 0
            return create_progress_figure(0), False, None
        
        # Check for new progress in queue
        logger.info("Checking queue for updates")
        try:
            while not progress_queue.empty():
                item = progress_queue.get_nowait()
                logger.info(f"Got queue item: {item}")
                
                if isinstance(item, tuple):
                    status, data = item
                    if status == 'results':
                        logger.info("Processing final results")
                        logger.info(f"Results data: {data}")
                        return create_progress_figure(100), True, data
                    elif status == 'error':
                        logger.error(f"Error in simulation: {data}")
                        return create_progress_figure(0), True, {'error': data}
                    elif status == 'progress':
                        logger.info(f"Progress update: {data}%")
                        current_progress['value'] = data
                else:
                    logger.info(f"Legacy progress update: {item}")
                    current_progress['value'] = item
                    
        except Exception as e:
            logger.error(f"Error processing queue item: {str(e)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
        
        logger.info(f"Returning current progress: {current_progress['value']}")
        return create_progress_figure(current_progress['value']), False, None

    @app.callback(
        Output('simulation-results', 'children'),
        Input('simulation-results-store', 'data'),
        prevent_initial_call=True
    )
    def update_results(data):
        logger.info("Update results callback triggered")
        logger.info(f"Received data: {data}")
        
        if not data:
            logger.info("No data received, preventing update")
            raise PreventUpdate
        
        if 'error' in data:
            logger.error(f"Error in results: {data['error']}")
            return html.Div([
                html.H4("שגיאה בהרצת הסימולציה:", className="text-danger"),
                html.Pre(data['error'])
            ], className="mt-4")
        
        try:
            logger.info("Creating DataFrame from results")
            df = pd.DataFrame({
                'בית חולים': data['בית חולים'],
                'אחוז קבלה': data['אחוז קבלה']
            })
            logger.info(f"DataFrame created successfully: {df.shape}")
            
            table = dbc.Table.from_dataframe(
                df,
                striped=True,
                bordered=True,
                hover=True,
                className="mt-4",
                style={'color': '#ffffff'}
            )
            logger.info("Table created successfully")
            return table
            
        except Exception as e:
            logger.error(f"Error creating results table: {str(e)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return html.Div([
                html.H4("שגיאה בהצגת התוצאות:", className="text-danger"),
                html.Pre(str(e))
            ], className="mt-4")

    @app.callback(
        [Output('run-simulation-btn', 'disabled'),
         Output('stop-simulation-btn', 'disabled')],
        [Input('run-simulation-btn', 'n_clicks'),
         Input('stop-simulation-btn', 'n_clicks'),
         Input('simulation-results-store', 'data')],
        prevent_initial_call=True
    )
    def toggle_buttons(run_clicks, stop_clicks, results):
        if not run_clicks:
            raise PreventUpdate
        
        if ctx.triggered_id == 'run-simulation-btn':
            return True, False
        elif ctx.triggered_id == 'stop-simulation-btn' or results is not None:
            return False, True
        
        return None, None

    @app.callback(
        Output('_simulation-trigger', 'children'),
        Input('run-simulation-btn', 'n_clicks'),
        [State('year-dropdown', 'value'),
         State('simulation-slider', 'value'),
         State({'type': 'hospital-item', 'index': ALL}, 'children')],
        prevent_initial_call=True
    )
    def start_simulation(run_clicks, year, n_simulations, hospitals):
        logger.info(f"Start simulation triggered: clicks={run_clicks}, year={year}, n_simulations={n_simulations}")
        
        if not run_clicks:
            logger.info("No run clicks, preventing update")
            raise PreventUpdate
        
        # Clear the queue
        logger.info("Clearing queue")
        while not progress_queue.empty():
            try:
                progress_queue.get_nowait()
            except:
                pass
        
        hospital_order = [h[h.find(". ") + 2:] for h in hospitals]
        logger.info(f"Hospital order: {hospital_order}")
        
        # Start simulation in a separate thread
        thread = Thread(
            target=run_simulation_thread,
            args=(priorities_data, acceptance_data, year, hospital_order, n_simulations, progress_queue)
        )
        thread.daemon = True
        thread.start()
        logger.info("Simulation thread started")
        
        return ''
