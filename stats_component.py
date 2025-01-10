from dash import html, dcc, Input, Output, State, callback
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime
import os

# Initialize the app without creating a new Dash instance
app = None

def get_top_hospitals(data, year='2024', n=3):
    """Get the n hospitals with lowest non-zero acceptance rates for first priority."""
    df = data[year]
    first_priority_rates = df.iloc[:, 1]
    
    hospital_rates = pd.DataFrame({
        'hospital': df['מוסד'],
        'rate': first_priority_rates
    })
    
    non_zero_rates = hospital_rates[hospital_rates['rate'] > 0]
    return non_zero_rates.nsmallest(n, 'rate')['hospital'].tolist()

def get_hospital_stats_for_priority(data, priority, start_year, end_year):
    """Calculate average acceptance rate for each hospital for a given priority."""
    stats = {}
    for hospital in data['2020']['מוסד'].unique():
        rates = []
        for year in range(start_year, end_year + 1):
            df = data[str(year)]
            rate = df[df['מוסד'] == hospital].iloc[0][priority]
            if pd.notna(rate):
                rates.append(rate)
        if rates:
            avg_rate = np.mean(rates)
            if avg_rate > 0:
                stats[hospital] = avg_rate
    
    sorted_stats = dict(sorted(stats.items(), key=lambda x: x[1], reverse=True))
    return sorted_stats

def init_stats(data_load_function):
    global data, all_hospitals, n_priorities, top_hospitals
    
    # Load data using the provided function
    data = data_load_function()
    all_hospitals = sorted(data['2020']['מוסד'].tolist())
    n_priorities = data['2020'].shape[1] - 1
    top_hospitals = get_top_hospitals(data)

    # Create layout
    layout = dbc.Container([
        # Title
        html.H1("סטטיסטיקת קבלה לפי עדיפות", className="text-center my-4"),
        
        # Year range selector
        dbc.Row([
            dbc.Col([
                html.H4("טווח שנים"),
                dcc.RangeSlider(
                    id='stats-year-range-slider',
                    min=2020,
                    max=2024,
                    value=[2020, 2024],
                    marks={str(year): str(year) for year in range(2020, 2025)},
                    step=1
                ),
            ], width=12)
        ], className="mb-4"),
        
        # Priority selector and first graph
        dbc.Row([
            dbc.Col([
                html.H4("אחוזי קבלה של בתי החולים לפי עדיפות"),
                dcc.Dropdown(
                    id='stats-priority-selector',
                    options=[{'label': f'עדיפות {i}', 'value': i} for i in range(1, n_priorities)],
                    value=1,
                    clearable=False,
                    className="mb-3"
                ),
                dcc.Graph(id='stats-acceptance-rate-graph')
            ], width=12)
        ], className="mb-4"),
        
        # Hospital comparison section
        dbc.Row([
            dbc.Col([
                html.H4("השוואת אחוזי קבלה לפי עדיפויות"),
                dbc.Row([
                    dbc.Col([
                        dcc.Dropdown(
                            id='stats-hospital-1',
                            options=[{'label': h, 'value': h} for h in all_hospitals],
                            value=top_hospitals[0] if top_hospitals else None,
                            placeholder="בחר בית חולים 1",
                            className="mb-2"
                        )
                    ], width=4),
                    dbc.Col([
                        dcc.Dropdown(
                            id='stats-hospital-2',
                            options=[{'label': h, 'value': h} for h in all_hospitals],
                            value=top_hospitals[1] if len(top_hospitals) > 1 else None,
                            placeholder="בחר בית חולים 2",
                            className="mb-2"
                        )
                    ], width=4),
                    dbc.Col([
                        dcc.Dropdown(
                            id='stats-hospital-3',
                            options=[{'label': h, 'value': h} for h in all_hospitals],
                            value=top_hospitals[2] if len(top_hospitals) > 2 else None,
                            placeholder="בחר בית חולים 3",
                            className="mb-2"
                        )
                    ], width=4)
                ]),
                html.H4("טווח עדיפויות"),
                dcc.RangeSlider(
                    id='stats-priority-range-slider',
                    min=1,
                    max=n_priorities - 1,
                    value=[1, n_priorities - 1],
                    marks={i: str(i) for i in range(1, n_priorities)},
                    step=1,
                    className="my-4"
                ),
                dcc.Graph(id='stats-hospital-comparison-graph'),
                dcc.Graph(id='stats-acceptance-numbers-graph')
            ], width=12)
        ])
    ], fluid=True, style={'direction': 'rtl'})

    return layout

# Callbacks
@callback(
    Output('stats-acceptance-rate-graph', 'figure'),
    [Input('stats-priority-selector', 'value'),
     Input('stats-year-range-slider', 'value')]
)
def update_acceptance_rate_graph(selected_priority, year_range):
    start_year, end_year = year_range
    stats = get_hospital_stats_for_priority(data, selected_priority, start_year, end_year)
    
    if not stats:
        empty_fig = go.Figure()
        empty_fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white')
        )
        return empty_fig
    
    fig = go.Figure(data=[
        go.Bar(
            x=list(stats.keys()),
            y=[rate * 100 for rate in stats.values()],
            text=[f"{rate*100:.1f}%" for rate in stats.values()],
            textposition='auto',
            marker_color='rgb(220, 76, 100)'
        )
    ])
    
    fig.update_layout(
        height=400,
        bargap=0.2,
        margin=dict(t=20, b=20, l=20, r=20),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(
            title="בית חולים",
            tickangle=45,
            automargin=True,
            color='white',
            gridcolor='rgba(128, 128, 128, 0.2)'
        ),
        yaxis=dict(
            title="אחוז קבלה",
            tickformat='.1f',
            ticksuffix="%",
            range=[0, max(list(stats.values())) * 100 * 1.1],
            gridcolor='rgba(128, 128, 128, 0.2)',
            showgrid=True,
            color='white'
        ),
        font=dict(color='white')
    )
    
    return fig

@callback(
    [Output('stats-hospital-comparison-graph', 'figure'),
     Output('stats-acceptance-numbers-graph', 'figure')],
    [Input('stats-hospital-1', 'value'),
     Input('stats-hospital-2', 'value'),
     Input('stats-hospital-3', 'value'),
     Input('stats-priority-range-slider', 'value'),
     Input('stats-year-range-slider', 'value')]
)
def update_comparison_graphs(hospital1, hospital2, hospital3, priority_range, year_range):
    selected_hospitals = [h for h in [hospital1, hospital2, hospital3] if h is not None]
    start_year, end_year = year_range
    min_priority, max_priority = priority_range
    
    if not selected_hospitals:
        empty_fig1 = go.Figure()
        empty_fig2 = go.Figure()

        for fig in [empty_fig1, empty_fig2]:
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white'),
                xaxis=dict(color='white', gridcolor='rgba(128, 128, 128, 0.2)'),
                yaxis=dict(color='white', gridcolor='rgba(128, 128, 128, 0.2)')
            )
    
        return empty_fig1, empty_fig2

    x_categories = [f"עדיפות {i}" for i in range(min_priority, max_priority + 1)]
    
    # Calculate rates data
    priorities_data = []
    for hospital in selected_hospitals:
        hospital_rates = []
        for priority in range(min_priority, max_priority + 1):
            rates = []
            for year in range(start_year, end_year + 1):
                df = data[str(year)]
                rate = df[df['מוסד'] == hospital].iloc[0][priority]
                if pd.notna(rate):
                    rates.append(rate)
            avg_rate = np.mean(rates) * 100 if rates else 0
            hospital_rates.append(avg_rate)
        priorities_data.append({
            'hospital': hospital,
            'rates': hospital_rates
        })
    
    # Create comparison figure
    fig_comparison = go.Figure()
    colors = ['rgb(220, 76, 100)', 'rgb(65, 148, 136)', 'rgb(152, 78, 163)']
    
    for i, hosp_data in enumerate(priorities_data):
        fig_comparison.add_trace(go.Bar(
            name=hosp_data['hospital'],
            x=x_categories,
            y=hosp_data['rates'],
            text=[f"{rate:.1f}%" for rate in hosp_data['rates']],
            textposition='auto',
            marker_color=colors[i],
        ))
    
    fig_comparison.update_layout(
        height=400,
        barmode='group',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=20, b=20, l=20, r=20),
        xaxis=dict(
            title="עדיפות",
            color='white',
            gridcolor='rgba(128, 128, 128, 0.2)'
        ),
        yaxis=dict(
            title="אחוז קבלה",
            tickformat='.1f',
            ticksuffix="%",
            range=[0, 100],
            gridcolor='rgba(128, 128, 128, 0.2)',
            showgrid=True,
            color='white'
        ),
        font=dict(color='white'),
        showlegend=True,
        legend=dict(
            bgcolor='rgba(0,0,0,0)',
            font=dict(color='white')
        )
    )
    
    # Create acceptance numbers figure
    fig_numbers = go.Figure()
    acceptance_numbers_data = {}
    
    try:
        for year in range(start_year, end_year + 1):
            df = pd.read_excel("data/acceptance_numbers.xlsx", sheet_name=str(year))
            acceptance_numbers_data[str(year)] = df
    except Exception as e:
        print(f"Error loading acceptance numbers: {e}")
        return fig_comparison, fig_numbers
    
    acceptance_data = []
    for hospital in selected_hospitals:
        hospital_numbers = []
        for priority in range(min_priority, max_priority + 1):
            numbers = []
            for year in range(start_year, end_year + 1):
                if str(year) in acceptance_numbers_data:
                    df = acceptance_numbers_data[str(year)]
                    try:
                        number = df[df['מוסד'] == hospital].iloc[0][priority]
                        if pd.notna(number):
                            numbers.append(number)
                    except:
                        continue
            avg_number = np.mean(numbers) if numbers else 0
            hospital_numbers.append(avg_number)
        acceptance_data.append({
            'hospital': hospital,
            'numbers': hospital_numbers
        })
    
    for i, hosp_data in enumerate(acceptance_data):
        fig_numbers.add_trace(go.Bar(
            name=hosp_data['hospital'],
            x=x_categories,
            y=hosp_data['numbers'],
            text=[f"{int(num)}" for num in hosp_data['numbers']],
            textposition='auto',
            marker_color=colors[i]
        ))
    
    fig_numbers.update_layout(
        height=400,
        barmode='group',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=20, b=20, l=20, r=20),
        xaxis=dict(
            title="עדיפות",
            color='white',
            gridcolor='rgba(128, 128, 128, 0.2)'
        ),
        yaxis=dict(
            title="מספר מתקבלים",
            color='white',
            gridcolor='rgba(128, 128, 128, 0.2)'
        ),
        font=dict(color='white'),
        showlegend=True,
        legend=dict(
            bgcolor='rgba(0,0,0,0)',
            font=dict(color='white')
        )
    )
    
    return fig_comparison, fig_numbers