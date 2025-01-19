import pandas as pd

from dfa import simulate_single_intern_match
from rsd import calculate_rsd_probabilities
from probability_trading import trade_probabilities
from utils import get_hospital_capacities, get_total_capacity, generate_interns_data

def run_simulation(
    priorities_data: dict,
    acceptance_data: dict,
    year: str | int,
    intern_data: list,
    n_permutations: int = 1000,
    method: {'dfa', 'rsd'} = 'dfa',
    progress_callback=None
):
    """
    Run multiple simulations and calculate the percentage each hospital was drawn.
    
    Args:
        priorities_data (dict): Dictionary of priority DataFrames per year
        acceptance_data (dict): Dictionary of acceptance DataFrames per year
        year (int): Year to simulate
        intern_data (list): List of hospital names in order of preference
        n_permutations (int): Number of simulations to run
        progress_callback (callable): Optional callback function to report progress
        
    Returns:
        pd.Series: Percentages each hospital was drawn, sorted from highest to lowest
    """
    if isinstance(year, int):
        year = str(year)
    priorities_df = priorities_data[year]
    acceptance_df = acceptance_data[year]
    hospital_capacities = get_hospital_capacities(acceptance_df)
    total_capacity = get_total_capacity(hospital_capacities)
    
    # Get all possible hospitals from priorities_df
    all_hospitals = priorities_df.iloc[:, 0].values

    if method == 'dfa':
        # Run simulations
        hospitals_drew = []
        for i in range(n_permutations):
            hospitals_drew.append(simulate_single_intern_match(
                priorities_df,
                hospital_capacities,
                intern_data,
                total_capacity
            ))
            if progress_callback:
                progress_callback((i + 1) / n_permutations)

        # Calculate percentages
        draw_counts = pd.Series(hospitals_drew).value_counts()

        # Create series with all hospitals (including those never drawn)
        percentages = pd.Series(0.0, index=all_hospitals, name='Percentage')

        # Update percentages for hospitals that were drawn
        percentages[draw_counts.index] = (draw_counts / n_permutations) * 100

        # Sort from highest to lowest
        percentages = percentages.sort_values(ascending=False)
    
    elif method == 'rsd':
        intern_probabilities = []
        for i in range(n_permutations):
            simulated_interns = generate_interns_data(priorities_df, total_capacity - 1, seed=i)
            simulated_interns.index = simulated_interns.index + 1

            # Add the supplied intern's priorities as the last row
            preferences_df = pd.concat([
                pd.DataFrame([intern_data], 
                             columns=simulated_interns.columns),
                simulated_interns
            ])
            preferences_df.to_csv('interns_data_simulated.csv')
            hospital_probs = calculate_rsd_probabilities(
                preferences_df,
                hospital_capacities,
            )
        
            optimized_probabilities = trade_probabilities(hospital_probs, preferences_df, hospital_capacities)

            intern_probabilities.append(optimized_probabilities.iloc[0, :].sort_index())
            if progress_callback:
                progress_callback((i + 1) / n_permutations)
        percentages = 100 * pd.DataFrame(intern_probabilities).mean().sort_values(ascending=False)
    return percentages
