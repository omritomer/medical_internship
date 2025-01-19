import pandas as pd
import numpy as np
from typing import Dict, List
import random

def run_single_rsd(
    student_preferences: pd.DataFrame,
    hospital_capacities: Dict[str, int]
) -> Dict[int, str]:
    """
    Run a single iteration of Random Serial Dictatorship.
    
    Args:
        student_preferences: DataFrame where each row represents a student's ordered preferences,
                           index is student ID, and columns are preference ranks
        hospital_capacities: Dictionary mapping hospital names to their capacities
    
    Returns:
        Dictionary mapping student indices to their assigned hospitals
    """
    # Create copy of capacities to track remaining spots
    remaining_capacity = hospital_capacities.copy()
    
    # Create list of unassigned students
    student_indices = list(student_preferences.index)
    random.shuffle(student_indices)
    
    # Create assignments dictionary
    assignments = {}
    
    # Assign students in random order
    for student_idx in student_indices:
        # Get student's preferences (all columns contain preferences)
        student_prefs = student_preferences.loc[student_idx].tolist()
        
        # Find first available preferred hospital
        for hospital in student_prefs:
            if remaining_capacity[hospital] > 0:
                assignments[student_idx] = hospital
                remaining_capacity[hospital] -= 1
                break
                
    return assignments

def calculate_rsd_probabilities(
    student_preferences: pd.DataFrame,
    hospital_capacities: Dict[str, int],
    n_simulations: int = 500
) -> pd.DataFrame:
    """
    Calculate probabilities of each student being assigned to each hospital using RSD.
    
    Args:
        student_preferences: DataFrame where each row represents a student's ordered preferences,
                           index is student ID, and columns are preference ranks
        hospital_capacities: Dictionary mapping hospital names to their capacities
        n_simulations: Number of RSD simulations to run
    
    Returns:
        DataFrame with probabilities for each student-hospital pair
    """
    hospitals = list(hospital_capacities.keys())
    student_indices = list(student_preferences.index)
    
    # Initialize probability counts
    probability_counts = np.zeros((len(student_indices), len(hospitals)))
    
    # Run simulations
    for _ in range(n_simulations):
        assignments = run_single_rsd(student_preferences, hospital_capacities)
        
        # Update counts
        for student_idx, hospital in assignments.items():
            student_pos = student_indices.index(student_idx)
            hospital_idx = hospitals.index(hospital)
            probability_counts[student_pos][hospital_idx] += 1
    
    # Convert counts to probabilities
    probabilities = probability_counts / n_simulations
    
    # Create probability DataFrame
    probability_df = pd.DataFrame(
        probabilities,
        columns=hospitals,
        index=student_indices
    )
    
    return probability_df

def get_rank_probabilities(
    student_preferences: pd.DataFrame,
    probability_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Convert hospital probabilities to rank probabilities.
    
    Args:
        student_preferences: Original preferences DataFrame
        probability_df: DataFrame with hospital assignment probabilities
    
    Returns:
        DataFrame with probabilities of getting each rank
    """
    student_indices = list(student_preferences.index)
    n_ranks = len(student_preferences.columns)
    rank_probs = np.zeros((len(student_indices), n_ranks))
    
    # For each student
    for i, student_idx in enumerate(student_indices):
        # Get student's preferences and probabilities
        prefs = student_preferences.loc[student_idx].tolist()
        probs = probability_df.loc[student_idx]
        
        # For each rank
        for rank, hospital in enumerate(prefs):
            rank_probs[i][rank] = probs[hospital]
    
    # Create DataFrame
    rank_probability_df = pd.DataFrame(
        rank_probs,
        columns=[f"Rank_{i+1}" for i in range(n_ranks)],
        index=student_indices
    )
    
    return rank_probability_df
