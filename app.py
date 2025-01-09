import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from utils import run_simulation

# Add CSS for RTL support and styling with wider sidebar
st.markdown("""
<style>
    /* Global RTL settings */
    .stApp {
        direction: rtl;
    }
    
    /* Wider sidebar settings */
    section[data-testid="stSidebar"] {
        width: 600px !important;
        min-width: 600px !important;
        max-width: 600px !important;
        position: relative !important;
    }
    
    /* Additional sidebar width enforcement */
    .css-1d391kg, .css-1q7ecm2, [data-testid="stSidebarNav"],
    .css-pkbazv, .css-17eq0hr {
        width: 600px !important;
        min-width: 600px !important;
        max-width: 600px !important;
    }
    
    /* Ensure sidebar content width */
    .css-1d391kg > div, .css-1q7ecm2 > div {
        width: 600px !important;
    }
    
    /* RTL for main container with adjusted padding */
    .main .block-container {
        direction: rtl;
        padding-right: 420px !important;  /* Increased to account for wider sidebar */
        padding-left: 1rem !important;
        margin-right: 0 !important;
    }
    
    /* RTL for tables */
    .dataframe {
        text-align: right !important;
        direction: rtl !important;
    }
    
    th, td {
        text-align: right !important;
    }
    
    /* RTL for metrics */
    .css-1xarl3l {
        direction: rtl;
    }
    
    /* Custom menu styling for RTL */
    .stSelectbox > div[role='listbox'] {
        direction: rtl;
        text-align: right;
    }
    
    /* Force LTR for slider */
    .stSlider div[data-baseweb="slider"] {
        direction: ltr !important;
    }
    
    /* RTL for tabs */
    .stTabs {
        direction: rtl;
    }
    
    /* Bar chart direction */
    .recharts-wrapper {
        direction: rtl;
    }

    /* Fix overlapping issues */
    .element-container, .stMarkdown {
        width: 100% !important;
    }
</style>
""", unsafe_allow_html=True)

def create_menu(items, key, height=300, default_index=0):
    menu_styles = {
        "container": {
            "height": f"{height}px",
            "overflow-y": "scroll",
            "overflow-x": "hidden",
            "direction": "rtl",
            "transition": "all 0.1s ease-in-out",  # Add smooth transition
            "background-color": "#262730"
        },
        "nav": {
            "background-color": "#262730",
            "direction": "rtl",
            "transition": "all 0.1s ease-in-out"  # Add smooth transition
        },
        "nav-link": {
            "font-size": "14px",
            "text-align": "right",
            "margin": "0px",
            "padding": "5px",
            "border-radius": "0px",
            "transition": "all 0.1s ease-in-out"  # Add smooth transition
        }
    }
    
    return option_menu(
        "",  # Empty title
        options=items,
        default_index=default_index,
        menu_icon=None,
        icons=["hospital"] * len(items),
        styles=menu_styles,
        key=f"{key}_{default_index}"  # Include index in key to force refresh
    )

@st.cache_data
def load_data():
    data = {}
    for year in range(2020, 2025):
        df = pd.read_excel("data/acceptance_ratios.xlsx", sheet_name=str(year))
        data[str(year)] = df
    return data

def calculate_probability_for_top_n(hospitals, priorities, start_year, end_year, data):
    probs = []
    for year in range(start_year, end_year + 1):
        df = data[str(year)]
        year_probs = []
        
        for hospital, priority in zip(hospitals, priorities):
            rate = df[df['מוסד'] == hospital].iloc[0][priority]
            if pd.notna(rate):
                year_probs.append(rate)
        
        if year_probs:
            combined_prob = 1 - np.prod([1 - p for p in year_probs])
            probs.append(combined_prob)
    
    return np.mean(probs) if probs else 0

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
        if rates:  # Only include hospitals with valid rates
            avg_rate = np.mean(rates)
            if avg_rate > 0:  # Only include hospitals with non-zero rates
                stats[hospital] = avg_rate
    
    # Sort hospitals by acceptance rate in descending order
    sorted_stats = dict(sorted(stats.items(), key=lambda x: x[1], reverse=True))
    return sorted_stats

def get_default_hospital_order():
    """
    Calculate the default hospital order based on first priority requests across all years.
    Returns a list of hospital names sorted by total first priority requests.
    """
    # Load data for all years
    priority_totals = {}
    
    try:
        for year in range(2020, 2025):
            df = pd.read_excel("data/priority_numbers.xlsx", sheet_name=str(year))
            # First column is hospital names, second column is first priority counts
            for i, row in df.iterrows():
                hospital = row.iloc[0]  # Hospital name is first column
                first_priority_count = float(row.iloc[1])  # First priority count is second column
                if pd.notna(first_priority_count):
                    priority_totals[hospital] = priority_totals.get(hospital, 0) + first_priority_count
        
        # Sort hospitals by total first priority requests (descending)
        sorted_hospitals = sorted(priority_totals.items(), key=lambda x: (-x[1], x[0]))
        return [hospital for hospital, _ in sorted_hospitals]
        
    except Exception as e:
        st.error(f"Error in get_default_hospital_order: {str(e)}")
        raise e
    
def calculator_tab():
    st.title("מחשבון סיכויי קבלה לבתי חולים")
    
    if 'selected_hospitals' not in st.session_state:
        st.session_state.selected_hospitals = []
    
    data = load_data()
    start_year = st.session_state.start_year
    end_year = st.session_state.end_year
    
    if st.session_state.selected_hospitals:
        st.header("הסטטיסטיקות שלך")
        cols = st.columns(len(st.session_state.selected_hospitals))
        priorities = list(range(1, len(st.session_state.selected_hospitals) + 1))
        
        for i in range(len(st.session_state.selected_hospitals)):
            prob = calculate_probability_for_top_n(
                st.session_state.selected_hospitals[:i+1],
                priorities[:i+1],
                start_year,
                end_year,
                data
            )
            with cols[i]:
                st.metric(f"{i+1} בחירות ראשונות", f"{prob:.1%}")
        
        st.subheader("אחוזי קבלה היסטוריים")
        historical_data = []
        for year in range(start_year, end_year + 1):
            df = data[str(year)]
            year_data = {'שנה': year}
            
            for i, hospital in enumerate(st.session_state.selected_hospitals, 1):
                rate = df[df['מוסד'] == hospital].iloc[0][i]
                year_data[f'בחירה {i}: {hospital}'] = f"{rate:.1%}" if pd.notna(rate) else "לא זמין"
            
            historical_data.append(year_data)
        
        historical_df = pd.DataFrame(historical_data)
        st.dataframe(historical_df, hide_index=True, use_container_width=True)
    else:
        st.info("נא לבחור בתי חולים מהתפריט בצד ימין כדי לראות סטטיסטיקות")

def statistics_tab():
    st.title("סטטיסטיקת קבלה לפי עדיפות")
    
    data = load_data()
    start_year = st.session_state.start_year
    end_year = st.session_state.end_year
    all_hospitals = sorted(data['2020']['מוסד'].tolist())
    n_priorities = data['2020'].shape[1] - 1  # -1 for hospital name column
    
    # First graph - Priority selector and graph
    st.subheader("אחוזי קבלה של בתי החולים לפי עדיפות")
    priorities = list(range(1, n_priorities))
    selected_priority = st.selectbox(
        "בחר עדיפות",
        priorities,
        format_func=lambda x: f"עדיפות {x}"
    )
    
    # Get statistics for selected priority
    stats = get_hospital_stats_for_priority(data, selected_priority, start_year, end_year)
    
    # Create first bar chart
    if stats:
        fig1 = go.Figure(data=[
            go.Bar(
                x=list(stats.keys()),
                y=[rate * 100 for rate in stats.values()],
                text=[f"{rate*100:.1f}%" for rate in stats.values()],
                textposition='auto',
            )
        ])
        
        # Update layout for RTL support and styling
        fig1.update_layout(
            height=400,
            width=1200,
            bargap=0.2,
            margin=dict(t=20, b=20, l=20, r=20),
            plot_bgcolor='rgb(17, 17, 17)',
            paper_bgcolor='rgb(17, 17, 17)',
            xaxis=dict(
                title=dict(
                    text="בית חולים",
                    font=dict(color='white')
                ),
                tickangle=45,
                automargin=True,
                gridcolor='rgba(128, 128, 128, 0.2)',
                showgrid=False,
                tickfont=dict(color='white'),
            ),
            yaxis=dict(
                title=dict(
                    text="אחוז קבלה",
                    font=dict(color='white')
                ),
                tickformat='.1f',
                ticksuffix="%",
                range=[0, max(list(stats.values())) * 100 * 1.1],
                gridcolor='rgba(128, 128, 128, 0.2)',
                showgrid=True,
                tickfont=dict(color='white'),
            ),
        )
        
        fig1.update_traces(
            marker_color='rgb(220, 76, 100)',
            marker_line_width=0,
            opacity=0.9,
            textfont=dict(color='white'),
            textposition='auto',
        )
        
        st.plotly_chart(fig1, use_container_width=True)
    else:
        st.info("אין נתונים זמינים עבור העדיפות שנבחרה")
    
    # Second graph - Hospital selection and priorities comparison
    st.subheader("השוואת אחוזי קבלה לפי עדיפויות")
    
    # Add priority range slider above the graph
    priority_range = st.slider(
        "טווח עדיפויות להשוואה",
        min_value=1,
        max_value=n_priorities - 1,
        value=(1, min(10, n_priorities - 1)),
        key="priority_range_slider"
    )
    
    # Create three columns for hospital selection
    col1, col2, col3 = st.columns(3)
    selected_hospitals = []
    
    with col1:
        default_index = all_hospitals.index("רבין ק. בילינסון") + 1 if "רבין ק. בילינסון" in all_hospitals else 0
        hospital1 = st.selectbox("בית חולים 1", ["בחר בית חולים"] + all_hospitals, index=default_index, key="hosp1")
        if hospital1 != "בחר בית חולים":
            selected_hospitals.append(hospital1)
            
    with col2:
        hospital2 = st.selectbox("בית חולים 2", ["בחר בית חולים"] + all_hospitals, key="hosp2")
        if hospital2 != "בחר בית חולים":
            selected_hospitals.append(hospital2)
            
    with col3:
        hospital3 = st.selectbox("בית חולים 3", ["בחר בית חולים"] + all_hospitals, key="hosp3")
        if hospital3 != "בחר בית חולים":
            selected_hospitals.append(hospital3)
    
    if selected_hospitals:
        # Calculate average acceptance rates for selected priority range
        priorities_data = []
        min_priority, max_priority = priority_range
        
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
        
        # Create second bar chart
        fig2 = go.Figure()
        bar_width = 0.8 / len(selected_hospitals)
        colors = ['rgb(220, 76, 100)', 'rgb(65, 148, 136)', 'rgb(152, 78, 163)']
        
        for i, hosp_data in enumerate(priorities_data):
            fig2.add_trace(go.Bar(
                name=hosp_data['hospital'],
                x=[f"עדיפות {i}" for i in range(min_priority, max_priority + 1)],
                y=hosp_data['rates'],
                text=[f"{rate:.1f}%" for rate in hosp_data['rates']],
                textposition='auto',
                width=bar_width,
                offset=bar_width * (i - (len(selected_hospitals)-1)/2),
                marker_color=colors[i],
                textfont=dict(color='white'),
            ))
        
        fig2.update_layout(
            height=400,
            width=1200,
            bargap=0,
            barmode='overlay',
            plot_bgcolor='rgb(17, 17, 17)',
            paper_bgcolor='rgb(17, 17, 17)',
            margin=dict(t=20, b=20, l=20, r=20),
            xaxis=dict(
                title=dict(
                    text="עדיפות",
                    font=dict(color='white')
                ),
                tickfont=dict(color='white'),
            ),
            yaxis=dict(
                title=dict(
                    text="אחוז קבלה",
                    font=dict(color='white')
                ),
                tickformat='.1f',
                ticksuffix="%",
                range=[0, 100],
                gridcolor='rgba(128, 128, 128, 0.2)',
                showgrid=True,
                tickfont=dict(color='white'),
            ),
            showlegend=True,
            legend=dict(
                font=dict(color='white'),
                bgcolor='rgba(0,0,0,0)',
            )
        )
        
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("נא לבחור לפחות בית חולים אחד להשוואה")
    
    # Acceptance Numbers Section
    st.subheader("מספר המתקבלים לפי עדיפות")
    
    @st.cache_data
    def load_acceptance_numbers():
        numbers_data = {}
        try:
            for year in range(2020, 2025):
                df = pd.read_excel("data/acceptance_numbers.xlsx", sheet_name=str(year))
                numbers_data[str(year)] = df
        except Exception as e:
            st.error(f"Error loading acceptance numbers data: {e}")
        return numbers_data
    
    numbers_data = load_acceptance_numbers()
    
    if selected_hospitals and numbers_data:
        # Calculate acceptance numbers for selected priority range
        numbers_data_chart = []
        min_priority, max_priority = priority_range
        
        for hospital in selected_hospitals:
            hospital_numbers = []
            for priority in range(min_priority, max_priority + 1):
                numbers = []
                for year in range(start_year, end_year + 1):
                    df = numbers_data[str(year)]
                    try:
                        number = df[df['מוסד'] == hospital].iloc[0][priority]
                        if pd.notna(number):
                            numbers.append(number)
                    except:
                        continue
                avg_number = np.mean(numbers) if numbers else 0
                hospital_numbers.append(avg_number)
            numbers_data_chart.append({
                'hospital': hospital,
                'numbers': hospital_numbers
            })
        
        # Create acceptance numbers chart
        fig3 = go.Figure()
        bar_width = 0.8 / len(selected_hospitals)
        colors = ['rgb(220, 76, 100)', 'rgb(65, 148, 136)', 'rgb(152, 78, 163)']
        
        for i, hosp_data in enumerate(numbers_data_chart):
            fig3.add_trace(go.Bar(
                name=hosp_data['hospital'],
                x=[f"עדיפות {i}" for i in range(min_priority, max_priority + 1)],
                y=hosp_data['numbers'],
                text=[f"{int(num)}" for num in hosp_data['numbers']],
                textposition='auto',
                width=bar_width,
                offset=bar_width * (i - (len(selected_hospitals)-1)/2),
                marker_color=colors[i],
                textfont=dict(color='white'),
            ))
        
        fig3.update_layout(
            height=400,
            width=1200,
            bargap=0,
            barmode='overlay',
            plot_bgcolor='rgb(17, 17, 17)',
            paper_bgcolor='rgb(17, 17, 17)',
            margin=dict(t=20, b=20, l=20, r=20),
            xaxis=dict(
                title=dict(
                    text="עדיפות",
                    font=dict(color='white')
                ),
                tickfont=dict(color='white'),
            ),
            yaxis=dict(
                title=dict(
                    text="מספר מתקבלים",
                    font=dict(color='white')
                ),
                gridcolor='rgba(128, 128, 128, 0.2)',
                showgrid=True,
                tickfont=dict(color='white'),
            ),
            showlegend=True,
            legend=dict(
                font=dict(color='white'),
                bgcolor='rgba(0,0,0,0)',
            )
        )
        
        st.plotly_chart(fig3, use_container_width=True)

def simulation_tab():
    st.title("סימולציית קבלה")
    
    # Add CSS to minimize flash effect
    st.markdown("""
        <style>
        /* Add fade transition to main container */
        .main .block-container {
            transition: opacity 0.1s ease-in-out;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Year selection
    year = st.selectbox(
        "בחר שנה",
        options=list(range(2020, 2025)),
        format_func=lambda x: str(x),
        index=4  # Set default to 2024 (index 4 since range starts from 2020)
    )
    
    # Number of permutations slider
    n_permutations = st.slider(
        "מספר סימולציות",
        min_value=10,
        max_value=10000,
        value=100,
        step=10
    )
    
    # Hospital priorities section
    st.subheader("סדר עדיפויות")
    
    # Initialize simulation_hospitals if not exists
    if 'sim_hospitals' not in st.session_state:
        try:
            st.session_state.sim_hospitals = get_default_hospital_order()
        except Exception as e:
            data = load_data()
            st.session_state.sim_hospitals = sorted(data['2020']['מוסד'].tolist())
    
    # Create columns for list and buttons
    col1, col2 = st.columns([4, 1])
    
    with col1:
        # Get current selection index
        current_index = 0
        if 'sim_selected' in st.session_state:
            try:
                current_index = st.session_state.sim_hospitals.index(st.session_state.sim_selected)
            except ValueError:
                pass
        
        # Create numbered list of hospitals
        options = [f"{i+1}. {h}" for i, h in enumerate(st.session_state.sim_hospitals)]
        selected = create_menu(options, "sim_ordered_list", height=400, default_index=current_index)
        
        if selected:
            st.session_state.sim_selected = selected[selected.find(". ") + 2:]
            
    with col2:
        st.write("")
        st.write("")
        # Move up button
        if st.button("↑", key="sim_up"):
            if 'sim_selected' in st.session_state:
                current_list = st.session_state.sim_hospitals.copy()
                current_idx = current_list.index(st.session_state.sim_selected)
                if current_idx > 0:
                    # Store the selected hospital
                    selected_hospital = st.session_state.sim_selected
                    # Swap
                    current_list[current_idx], current_list[current_idx-1] = \
                        current_list[current_idx-1], current_list[current_idx]
                    # Update the list
                    st.session_state.sim_hospitals = current_list
                    # Maintain selection
                    st.session_state.sim_selected = selected_hospital
                    st.rerun()
        
        # Move down button
        if st.button("↓", key="sim_down"):
            if 'sim_selected' in st.session_state:
                current_list = st.session_state.sim_hospitals.copy()
                current_idx = current_list.index(st.session_state.sim_selected)
                if current_idx < len(current_list) - 1:
                    # Store the selected hospital
                    selected_hospital = st.session_state.sim_selected
                    # Swap
                    current_list[current_idx], current_list[current_idx+1] = \
                        current_list[current_idx+1], current_list[current_idx]
                    # Update the list
                    st.session_state.sim_hospitals = current_list
                    # Maintain selection
                    st.session_state.sim_selected = selected_hospital
                    st.rerun()
        
        # Reset button
        if st.button("↺", key="sim_reset"):
            if 'sim_selected' in st.session_state:
                del st.session_state.sim_selected
            st.session_state.sim_hospitals = get_default_hospital_order()
            st.rerun()
    
    # Run simulation button and results
    if st.button("הפעל סימולציה", key="run_sim"):
        try:
            # Load required data
            priorities_data = {}
            acceptance_data = {}
            for y in range(2020, 2025):
                priorities_data[str(y)] = pd.read_excel("data/priority_numbers.xlsx", sheet_name=str(y))
                acceptance_data[str(y)] = pd.read_excel("data/acceptance_numbers.xlsx", sheet_name=str(y))
            
            # Create progress bar
            progress_bar = st.progress(0, text="מריץ סימולציה...")
            
            # Define progress callback
            def update_progress(progress):
                progress_bar.progress(progress, text=f"מריץ סימולציה... {int(progress * 100)}%")
            
            # Run simulation with progress tracking
            results = run_simulation(
                priorities_data=priorities_data,
                acceptance_data=acceptance_data,
                year=str(year),
                intern_data=st.session_state.sim_hospitals,
                n_permutations=n_permutations,
                progress_callback=update_progress
            )
            
            # Clear progress bar
            progress_bar.empty()
            
            # Display results
            st.subheader("תוצאות הסימולציה")
            
            # Create and format results DataFrame
            results_df = pd.DataFrame({
                'בית חולים': results.index,
                'אחוז קבלה': results.values
            })
            results_df = results_df[results_df['אחוז קבלה'] > 0]
            results_df['אחוז קבלה'] = results_df['אחוז קבלה'].apply(lambda x: f"{x:.1f}%")
            
            # Display results
            st.dataframe(results_df, hide_index=True, use_container_width=True)
            
        except Exception as e:
            st.error(f"Error running simulation: {str(e)}")
                              
def main():
    # Clear simulation hospitals state on startup
    if 'simulation_hospitals' in st.session_state:
        del st.session_state.simulation_hospitals
    
    # Initialize session state for selected hospitals if not exists
    if 'selected_hospitals' not in st.session_state:
        st.session_state.selected_hospitals = []
    
    # Load data
    data = load_data()
    all_hospitals = sorted(data['2020']['מוסד'].tolist())
    
    # Sidebar
    st.sidebar.subheader("טווח שנים")
    years = list(range(2020, 2025))
    if 'start_year' not in st.session_state:
        st.session_state.start_year = 2020
        st.session_state.end_year = 2024
    
    start_year, end_year = st.sidebar.select_slider(
        "בחר טווח שנים",
        options=years,
        value=(st.session_state.start_year, st.session_state.end_year),
        key="year_slider"
    )
    st.session_state.start_year = start_year
    st.session_state.end_year = end_year
    
    # Hospital selection for calculator and statistics
    st.sidebar.subheader("בחר בתי חולים")
    col1, col2, col3, col4 = st.sidebar.columns([3, 1, 3, 1])
    
    with col1:  # Available hospitals list
        st.markdown("### רשימת בתי חולים")
        available_hospitals = [h for h in all_hospitals if h not in st.session_state.selected_hospitals]
        if available_hospitals:
            selected_available = create_menu(available_hospitals, "available", default_index=0)
            if selected_available:
                st.session_state.selected_available = selected_available
        else:
            st.write("אין בתי חולים זמינים")
            if 'selected_available' in st.session_state:
                del st.session_state.selected_available

    with col2:  # Button column
        st.write("")
        st.write("")
        if st.button("←", help="הוסף לנבחרים"):
            if 'selected_available' in st.session_state:
                if st.session_state.selected_available not in st.session_state.selected_hospitals:
                    st.session_state.selected_hospitals.append(st.session_state.selected_available)
                del st.session_state.selected_available
                if 'selected_hospital' in st.session_state:
                    del st.session_state.selected_hospital
                st.rerun()
            
        if st.button("→", help="הסר מהנבחרים"):
            if 'selected_hospital' in st.session_state:
                idx = st.session_state.selected_hospitals.index(st.session_state.selected_hospital)
                st.session_state.selected_hospitals.pop(idx)
                del st.session_state.selected_hospital
                if 'selected_available' in st.session_state:
                    del st.session_state.selected_available
                st.rerun()

    with col3:  # Selected hospitals list
        st.markdown("### בתי חולים נבחרים")
        selected_options = [f"{i+1}. {h}" for i, h in enumerate(st.session_state.selected_hospitals)]
        if not selected_options:
            selected_options = ["לא נבחרו בתי חולים"]
        
        # Get current selection index
        current_index = 0
        if 'selected_hospital' in st.session_state and st.session_state.selected_hospitals:
            try:
                hospital_name = st.session_state.selected_hospital
                current_index = [h[h.find(". ") + 2:] for h in selected_options].index(hospital_name)
            except ValueError:
                pass
        
        selected = create_menu(selected_options, "selected", default_index=current_index)
        if selected and "לא נבחרו בתי חולים" not in selected:
            st.session_state.selected_hospital = selected[selected.find(". ") + 2:]
    
    with col4:  # Order buttons
        st.write("")
        st.write("")
        if st.button("↑", help="העבר למעלה"):
            if 'selected_hospital' in st.session_state:
                current_list = st.session_state.selected_hospitals.copy()
                current_idx = current_list.index(st.session_state.selected_hospital)
                if current_idx > 0:
                    # Store the selected hospital
                    selected_hospital = st.session_state.selected_hospital
                    # Swap
                    current_list[current_idx], current_list[current_idx-1] = \
                        current_list[current_idx-1], current_list[current_idx]
                    # Update the list
                    st.session_state.selected_hospitals = current_list
                    # Maintain selection
                    st.session_state.selected_hospital = selected_hospital
                    st.rerun()
            
        if st.button("↓", help="העבר למטה"):
            if 'selected_hospital' in st.session_state:
                current_list = st.session_state.selected_hospitals.copy()
                current_idx = current_list.index(st.session_state.selected_hospital)
                if current_idx < len(current_list) - 1:
                    # Store the selected hospital
                    selected_hospital = st.session_state.selected_hospital
                    # Swap
                    current_list[current_idx], current_list[current_idx+1] = \
                        current_list[current_idx+1], current_list[current_idx]
                    # Update the list
                    st.session_state.selected_hospitals = current_list
                    # Maintain selection
                    st.session_state.selected_hospital = selected_hospital
                    st.rerun()
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs(["מחשבון סיכויים", "סטטיסטיקות קבלה", "סימולציה"])
    
    with tab1:
        calculator_tab()
    
    with tab2:
        statistics_tab()
        
    with tab3:
        simulation_tab()
                
if __name__ == "__main__":
    main()