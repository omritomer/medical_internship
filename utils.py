import pandas as pd
import numpy as np


def generate_intern_priorities(df: pd.DataFrame) -> list[str]:
    """
    Generate a simulated intern's hospital priorities based on actual distribution data.
    
    Args:
        df (pd.DataFrame): DataFrame for a specific year with hospital names in first column
                          and priority columns 1-25
    
    Returns:
        List[str]: A list of 25 hospital names in priority order (first item is first priority)
    """
    # Get hospital names from first column
    hospital_names = df.iloc[:, 0].values
    
    # Extract just the priority columns (1-25)
    priority_cols = list(range(1, 26))
    df_priorities = df[priority_cols]
    
    # Convert raw counts to probabilities for each priority position
    prob_df = df_priorities.copy()
    
    for col in prob_df.columns:
        total = prob_df[col].sum()
        if total > 0:
            prob_df[col] = prob_df[col] / total
            
    priorities = []
    available_indices = list(range(len(df)))
    
    # Generate each priority 1-25
    for priority_position in range(len(df_priorities.columns)):
        if not available_indices:
            break
            
        current_probs = prob_df.iloc[available_indices, priority_position].values
        
        # Normalize probabilities
        if current_probs.sum() > 0:
            current_probs = current_probs / current_probs.sum()
            selected_idx = np.random.choice(len(available_indices), p=current_probs)
        else:
            selected_idx = np.random.randint(len(available_indices))
            
        hospital_idx = available_indices.pop(selected_idx)
        priorities.append(hospital_names[hospital_idx])
    
    # Add any remaining hospitals randomly
    while available_indices:
        selected_idx = np.random.randint(len(available_indices))
        hospital_idx = available_indices.pop(selected_idx)
        priorities.append(hospital_names[hospital_idx])
    
    return priorities


def generate_interns_data(df: pd.DataFrame, n_interns: int) -> pd.DataFrame:
    """
    Generate priorities for multiple interns based on a year's data.
    
    Args:
        df (pd.DataFrame): DataFrame for a specific year with hospital names in first column
                          and priority columns 1-25
        n_interns: Number of interns to generate
    
    Returns:
        pd.DataFrame: DataFrame where each row represents an intern's priorities
                     and columns are priority numbers
    """
    # Get hospital names and initialize data structures once
    hospital_names = df.iloc[:, 0].values
    n_hospitals = len(hospital_names)
    
    # Get priority columns (excluding the hospital names column)
    priority_cols = df.columns[1:].tolist()
    n_priorities = len(priority_cols)
    
    # Pre-calculate probability matrices
    prob_matrices = []
    df_priorities = df[priority_cols].fillna(0)  # Replace NaN with 0
    for col in df_priorities.columns:
        probs = df_priorities[col].values
        total = probs.sum()
        if total > 0:
            probs = np.nan_to_num(probs / total, 0)  # Replace NaN with 0 after division
        else:
            probs = np.ones(n_hospitals) / n_hospitals
        prob_matrices.append(probs)
    
    # Generate all interns at once
    all_priorities = []
    for _ in range(n_interns):  # Use the input parameter
        priorities = []
        available_indices = list(range(n_hospitals))
        
        # Generate each priority
        for priority_idx, base_probs in enumerate(prob_matrices):
            if not available_indices:
                break
                
            # Get and normalize probabilities for available hospitals
            current_probs = base_probs[available_indices]
            prob_sum = current_probs.sum()
            
            if prob_sum > 0:
                current_probs = current_probs / prob_sum
            else:
                current_probs = np.ones(len(available_indices)) / len(available_indices)
            
            selected_idx = np.random.choice(len(available_indices), p=current_probs)
            hospital_idx = available_indices.pop(selected_idx)
            priorities.append(hospital_names[hospital_idx])
        
        # Add any remaining hospitals randomly
        while available_indices:
            selected_idx = np.random.randint(len(available_indices))
            hospital_idx = available_indices.pop(selected_idx)
            priorities.append(hospital_names[hospital_idx])
            
        all_priorities.append(priorities)
    
    return pd.DataFrame(all_priorities, columns=priority_cols)


def get_hospital_capacities(acceptance_df: pd.DataFrame) -> dict:
    """
    Calculate total capacity for each hospital from acceptance numbers.
    
    Args:
        acceptance_df (pd.DataFrame): DataFrame with hospital names and their acceptance numbers
        
    Returns:
        dict: Dictionary mapping hospital names to their total capacity
    """
    hospital_capacities = {}
    for _, row in acceptance_df.iterrows():
        hospital = row.iloc[0]  # Hospital name in first column
        capacity = row.iloc[1:].sum()  # Sum all acceptance numbers
        hospital_capacities[hospital] = int(capacity)
    
    return hospital_capacities


def get_total_capacity(hospital_capacities: dict) -> int:
    """
    Calculate total capacity across all hospitals.
    
    Args:
        hospital_capacities (dict): Dictionary mapping hospital names to their capacity
        
    Returns:
        int: Total capacity across all hospitals
    """
    return sum(hospital_capacities.values())

def match_interns_to_hospitals(interns_data: pd.DataFrame, hospital_capacities: dict) -> pd.DataFrame:
    """
    Implement deferred acceptance algorithm to match interns to hospitals.
    Each intern proposes to their top choice, with random order of proposals in each round.
    
    Args:
        interns_data (pd.DataFrame): DataFrame where each row is an intern's ordered hospital preferences
        hospital_capacities (dict): Dictionary mapping hospital names to their capacity
        
    Returns:
        pd.DataFrame: DataFrame with columns ['Hospital', 'Priority'] showing the final matches,
                     indexed by intern number
    """
    hospital_capacities = hospital_capacities.copy()
    
    # Initialize data structures
    unmatched_interns = set(interns_data.index)
    current_matches = {hospital: [] for hospital in hospital_capacities}  # hospital -> list of interns
    intern_current_priority = {i: 0 for i in unmatched_interns}  # intern -> current priority trying
    intern_hospitals = {}  # Final matches
    intern_priorities = {}  # Final priorities
    
    # Keep going until all interns are matched or have exhausted their preferences
    while unmatched_interns:
        # Randomize order of unmatched interns for this round
        unmatched_list = list(unmatched_interns)
        np.random.shuffle(unmatched_list)
        new_unmatched = set()
        
        for intern in unmatched_list:
            # Get intern's next preferred hospital
            priority = intern_current_priority[intern]
            if priority >= interns_data.shape[1]:
                continue
                
            hospital = interns_data.iloc[intern, priority]
            intern_current_priority[intern] += 1
            
            # Add intern to hospital's candidates
            current_matches[hospital].append((intern, priority))
            
            # If hospital is over capacity, randomly select among equal priority interns
            if len(current_matches[hospital]) > hospital_capacities[hospital]:
                # Group by priority
                priority_groups = {}
                for intern_id, prio in current_matches[hospital]:
                    if prio not in priority_groups:
                        priority_groups[prio] = []
                    priority_groups[prio].append(intern_id)
                
                # Select interns starting from lowest priority number
                accepted = []
                remaining_capacity = hospital_capacities[hospital]
                
                for priority in sorted(priority_groups.keys()):
                    interns_at_priority = priority_groups[priority]
                    # If we can take all interns at this priority, do so
                    if len(interns_at_priority) <= remaining_capacity:
                        accepted.extend((intern_id, priority) for intern_id in interns_at_priority)
                        remaining_capacity -= len(interns_at_priority)
                    # Otherwise, randomly select among them
                    else:
                        selected_interns = np.random.choice(
                            interns_at_priority, 
                            size=remaining_capacity, 
                            replace=False
                        )
                        accepted.extend((intern_id, priority) for intern_id in selected_interns)
                        # Add unselected interns to rejected
                        unselected = set(interns_at_priority) - set(selected_interns)
                        new_unmatched.update(unselected)
                        remaining_capacity = 0
                    
                    if remaining_capacity == 0:
                        break
                
                current_matches[hospital] = accepted
                # Add all remaining higher priority interns to new_unmatched
                for p in sorted(priority_groups.keys()):
                    if p > priority:
                        new_unmatched.update(priority_groups[p])
            
        unmatched_interns = new_unmatched
    
    # Convert current matches to final format
    for hospital, matches in current_matches.items():
        for intern, priority in matches:
            intern_hospitals[intern] = hospital
            intern_priorities[intern] = priority + 1  # Convert to 1-based priority
    
    return pd.DataFrame({
        'Hospital': intern_hospitals,
        'Priority': intern_priorities
    }).sort_index()

def simulate_single_intern_match(year_df: pd.DataFrame, 
                               hospital_capacities: dict,
                               intern_priorities: list,
                               total_capacity: int) -> str:
    """
    Simulate matching process for a specific intern among simulated peers.
    
    Args:
        year_df (pd.DataFrame): DataFrame for a specific year with hospital data
        hospital_capacities (dict): Dictionary mapping hospitals to their capacities
        intern_priorities (list): List of hospital names in order of preference
        
    Returns:
        str: The hospital assigned to the supplied intern
    """
    # Generate other interns data with leave_one=True
    simulated_interns = generate_interns_data(year_df, total_capacity - 1)
    simulated_interns.index = simulated_interns.index + 1
    
    # Add the supplied intern's priorities as the last row
    all_interns = pd.concat([
        pd.DataFrame([intern_priorities], 
                     columns=simulated_interns.columns),
        simulated_interns
    ])
    
    # Run matching algorithm
    matches = match_interns_to_hospitals(all_interns, hospital_capacities)
    
    # Get the hospital for the last intern (our supplied one)
    assigned_hospital = matches.loc[0, 'Hospital']
    
    return assigned_hospital


def run_simulation(
    priorities_data: dict,
    acceptance_data: dict,
    year: str | int,
    intern_data: list,
    n_permutations: int = 1000,
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
    
    return percentages
