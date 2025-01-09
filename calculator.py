from dash import Dash, html, dcc, Input, Output, State, callback, callback_context, no_update, ALL
import dash_bootstrap_components as dbc
import pandas as pd
import numpy as np
from datetime import datetime
import openpyxl

# Initialize the Dash app with bootstrap DARKLY theme and RTL support
app = Dash(
    __name__, 
    external_stylesheets=[
        dbc.themes.DARKLY,
        'https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/css/bootstrap.rtl.min.css'
    ],
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}]
)

# Add custom CSS for listbox styling with dark theme
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
                background-color: #222;
                color: white;
            }
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
            .button-group {
                display: flex;
                gap: 8px;
                margin-top: 8px;
            }
            .move-button {
                padding: 4px 12px;
                min-width: 40px;
            }
            /* Dark theme table styles */
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
            .border-end {
                border-color: #444 !important;
            }
            /* Card styles */
            .card {
                background-color: #303030;
                border-color: #444;
            }
            .card-body {
                color: white;
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

# Load data function with error handling
def load_data():
    data = {}
    try:
        for year in range(2020, 2025):
            df = pd.read_excel(
                f"data/acceptance_ratios.xlsx", 
                sheet_name=str(year),
                engine='openpyxl'
            )
            data[str(year)] = df
        return data
    except Exception as e:
        print(f"Error loading data: {e}")
        return None

def calculate_probability_for_top_n(hospitals, priorities, start_year, end_year, data):
    if not data or not hospitals:
        return 0
    
    probs = []
    for year in range(start_year, end_year + 1):
        df = data.get(str(year))
        if df is None:
            continue
            
        year_probs = []
        for hospital, priority in zip(hospitals, priorities):
            try:
                rate = df[df['מוסד'] == hospital].iloc[0][priority]
                if pd.notna(rate):
                    year_probs.append(rate)
            except (IndexError, KeyError) as e:
                print(f"Error calculating probability for {hospital}: {e}")
                continue
        
        if year_probs:
            combined_prob = 1 - np.prod([1 - p for p in year_probs])
            probs.append(combined_prob)
    
    return np.mean(probs) if probs else 0

# Load the data
data = load_data()
if data:
    all_hospitals = sorted(data['2020']['מוסד'].tolist())
else:
    all_hospitals = []
    print("Failed to load hospital data")

def create_listbox(id, items, selected_index=None):
    return html.Div([
        *[
            html.Div(
                item,
                id={'type': f'{id}-item', 'index': i},
                className=f'listbox-item {"selected" if i == selected_index else ""}',
                n_clicks=0
            ) for i, item in enumerate(items)
        ]
    ], className='listbox', id=id)

# Layout
app.layout = html.Div([
    dbc.Container([
        dbc.Row([
            # Sidebar
            dbc.Col([
                html.H4("טווח שנים", className="mb-4"),
                dcc.RangeSlider(
                    id='year-range-slider',
                    min=2020,
                    max=2024,
                    step=1,
                    marks={i: str(i) for i in range(2020, 2025)},
                    value=[2020, 2024],
                    className="mb-4"
                ),
                html.Hr(style={'border-color': '#444'}),
                html.H4("בחר בתי חולים", className="mb-4"),
                dbc.Row([
                    # Available hospitals
                    dbc.Col([
                        html.H5("רשימת בתי חולים"),
                        create_listbox('available-hospitals', all_hospitals),
                        dbc.Button(
                            'הוסף →',
                            id='add-hospital',
                            color="danger",
                            className="mt-2 w-100"
                        )
                    ], width=6),
                    # Selected hospitals
                    dbc.Col([
                        html.H5("בתי חולים נבחרים"),
                        create_listbox('selected-hospitals', []),
                        html.Div([
                            dbc.Button(
                                '← הסר',
                                id='remove-hospital',
                                color="danger",
                                className="move-button"
                            ),
                            dbc.Button(
                                '↑',
                                id='move-up',
                                color="secondary",
                                className="move-button"
                            ),
                            dbc.Button(
                                '↓',
                                id='move-down',
                                color="secondary",
                                className="move-button"
                            )
                        ], className="button-group")
                    ], width=6)
                ])
            ], width=4, className="border-end"),
            
            # Main content
            dbc.Col([
                html.H2("מחשבון סיכויי קבלה לבתי חולים", className="mb-4"),

                html.Div(id='statistics-container', children=[
                    html.H4("הסטטיסטיקות שלך", className="mb-3"),
                    html.Div(id='probability-metrics', className="mb-4"),
                    html.Hr(style={'border-color': '#444'}),
                    html.H4("אחוזי קבלה היסטוריים", className="mb-3"),
                    html.Div(id='historical-table')
                ])
            ], width=8, className="ps-4")
        ])
    ], fluid=True)
], className="p-4", style={'background-color': '#222', 'min-height': '100vh'})

# Callbacks
@callback(
    [Output('available-hospitals', 'children'),
     Output('selected-hospitals', 'children')],
    [Input('add-hospital', 'n_clicks'),
     Input('remove-hospital', 'n_clicks'),
     Input('move-up', 'n_clicks'),
     Input('move-down', 'n_clicks'),
     Input({'type': 'available-hospitals-item', 'index': ALL}, 'n_clicks'),
     Input({'type': 'selected-hospitals-item', 'index': ALL}, 'n_clicks')],
    [State('available-hospitals', 'children'),
     State('selected-hospitals', 'children')],
    prevent_initial_call=True
)
def update_hospitals(add_clicks, remove_clicks, up_clicks, down_clicks, 
                    available_clicks, selected_clicks, available_items, selected_items):
    ctx = callback_context
    if not ctx.triggered:
        return no_update, no_update
    
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # Get current lists
    available_hospitals = [item['props']['children'] for item in available_items] if available_items else []
    selected_hospitals = [item['props']['children'].split('. ', 1)[-1] if '. ' in item['props']['children'] 
                         else item['props']['children'] for item in selected_items] if selected_items else []
    
    # Get selected indices and handle clicks
    if isinstance(triggered_id, dict):
        # Clear previous selections when clicking a new item
        available_selected = triggered_id['index'] if triggered_id['type'] == 'available-hospitals-item' else None
        selected_selected = triggered_id['index'] if triggered_id['type'] == 'selected-hospitals-item' else None
    else:
        # For other actions, get the currently selected items
        available_selected = next((i for i, clicks in enumerate(available_clicks or []) 
                                 if clicks and clicks > 0), None)
        selected_selected = next((i for i, clicks in enumerate(selected_clicks or []) 
                                if clicks and clicks > 0), None)
    
    try:
        new_selected_index = selected_selected
        
        if triggered_id == 'add-hospital' and available_selected is not None:
            hospital = available_hospitals[available_selected]
            if hospital not in selected_hospitals:
                selected_hospitals.append(hospital)
                available_hospitals.remove(hospital)
                new_selected_index = len(selected_hospitals) - 1
                available_selected = None  # Clear selection after adding
        
        elif triggered_id == 'remove-hospital' and selected_selected is not None:
            hospital = selected_hospitals[selected_selected]
            selected_hospitals.remove(hospital)
            if hospital not in available_hospitals:
                available_hospitals.append(hospital)
                available_hospitals.sort()
            new_selected_index = None
        
        elif triggered_id == 'move-up' and selected_selected is not None and selected_selected > 0:
            selected_hospitals[selected_selected], selected_hospitals[selected_selected-1] = \
                selected_hospitals[selected_selected-1], selected_hospitals[selected_selected]
            new_selected_index = selected_selected - 1
            
        elif triggered_id == 'move-down' and selected_selected is not None and selected_selected < len(selected_hospitals) - 1:
            selected_hospitals[selected_selected], selected_hospitals[selected_selected+1] = \
                selected_hospitals[selected_selected+1], selected_hospitals[selected_selected]
            new_selected_index = selected_selected + 1
        
        # Create new listbox items with preserved selection
        new_available = html.Div([
            html.Div(
                item,
                id={'type': 'available-hospitals-item', 'index': i},
                className=f'listbox-item {"selected" if i == available_selected else ""}',
                n_clicks=1 if i == available_selected else 0
            ) for i, item in enumerate(available_hospitals)
        ], className='listbox', id='available-hospitals')
        
        new_selected = html.Div([
            html.Div(
                f"{i+1}. {item}",
                id={'type': 'selected-hospitals-item', 'index': i},
                className=f'listbox-item {"selected" if i == new_selected_index else ""}',
                n_clicks=1 if i == new_selected_index else 0
            ) for i, item in enumerate(selected_hospitals)
        ], className='listbox', id='selected-hospitals')
        
        return new_available.children, new_selected.children
        
    except Exception as e:
        print(f"Error updating hospitals: {e}")
        return no_update, no_update
    
# The update_statistics callback
@callback(
    [Output('probability-metrics', 'children'),
     Output('historical-table', 'children')],
    [Input('selected-hospitals', 'children'),
     Input('year-range-slider', 'value')]
)
def update_statistics(selected_items, year_range):
    if not selected_items:
        return (
            html.Div(
                dbc.Alert("נא לבחור בתי חולים מהתפריט בצד שמאל", color="info"),
                className="text-center"
            ),
            html.Div()
        )
    
    try:
        # Strip the numbering from hospital names
        selected_hospitals = [item['props']['children'].split('. ', 1)[-1] if '. ' in item['props']['children']
                            else item['props']['children'] for item in selected_items]
        start_year, end_year = year_range
        
        # Calculate probabilities
        probability_cards = []
        for i in range(len(selected_hospitals)):
            prob = calculate_probability_for_top_n(
                selected_hospitals[:i+1],
                list(range(1, i+2)),
                start_year,
                end_year,
                data
            )
            card = dbc.Card(
                dbc.CardBody([
                    html.H5(f"{i+1} בחירות ראשונות", className="text-center"),
                    html.H3(
                        f"{prob:.1%}",
                        className="text-center text-danger mb-0"
                    )
                ]),
                className="mb-4 h-100"
            )
            probability_cards.append(dbc.Col(card, width=3))
        
        # Create historical data table
        historical_data = []
        for year in range(start_year, end_year + 1):
            df = data[str(year)]
            year_data = {'שנה': year}
            
            for i, hospital in enumerate(selected_hospitals, 1):
                rate = df[df['מוסד'] == hospital].iloc[0][i]
                year_data[f'בחירה {i}: {hospital}'] = (
                    f"{rate:.1%}" if pd.notna(rate) else "לא זמין"
                )
            
            historical_data.append(year_data)
        
        historical_df = pd.DataFrame(historical_data)
        table = dbc.Table.from_dataframe(
            historical_df, 
            striped=True, 
            bordered=True, 
            hover=True,
            className="text-center"
        )
        
        return dbc.Row(probability_cards), table
        
    except Exception as e:
        print(f"Error updating statistics: {e}")
        return (
            html.Div(
                dbc.Alert("אירעה שגיאה בחישוב הסטטיסטיקות", color="danger"),
                className="text-center"
            ),
            html.Div()
        )

if __name__ == '__main__':
    app.run_server(debug=True)