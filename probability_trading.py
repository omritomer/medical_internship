import pandas as pd
import numpy as np
from pulp import *
from typing import Dict

def trade_probabilities(
    hospital_probs: pd.DataFrame,
    student_preferences: pd.DataFrame,
    hospital_capacities: Dict[str, int]
) -> pd.DataFrame:
    """
    Optimize probability assignments through trading.
    
    Args:
        hospital_probs: DataFrame with initial RSD probabilities where:
            - index: student IDs
            - columns: hospital names
            - values: probability of assignment
        student_preferences: DataFrame with same index as hospital_probs where:
            - Each row contains ordered list of hospital preferences
            - Column names are just numeric preference order
        hospital_capacities: Dict mapping hospital names to their capacities
    
    Returns:
        DataFrame with optimized probabilities
    """
    n_hospitals = len(hospital_capacities)
    hospitals = list(hospital_capacities.keys())
    
    # Calculate initial happiness for each student
    def calculate_happiness(probs: pd.DataFrame) -> Dict[int, float]:
        happiness = {}
        for student_idx in student_preferences.index:
            student_prefs = student_preferences.loc[student_idx].tolist()
            student_probs = probs.loc[student_idx]
            
            # Use squared weights as per paper
            student_happiness = sum(
                student_probs[hospital] * (n_hospitals - rank)**2
                for rank, hospital in enumerate(student_prefs)
            )
            happiness[student_idx] = student_happiness
        return happiness
    
    initial_happiness = calculate_happiness(hospital_probs)
    
    # Create optimization problem
    prob = LpProblem("InternshipTrading", LpMaximize)
    
    # Create variables for each student-hospital pair
    vars_dict = {
        (s, h): LpVariable(f"p_{s}_{h}", 0, 1)
        for s in student_preferences.index
        for h in hospitals
    }
    
    # Objective: Maximize total happiness across all students
    objective = []
    for s in student_preferences.index:
        student_prefs = student_preferences.loc[s].tolist()
        for rank, h in enumerate(student_prefs):
            weight = (n_hospitals - rank)**2
            objective.append(weight * vars_dict[(s, h)])
    
    prob += lpSum(objective)
    
    # Constraint 1: Individual rationality (no student worse off)
    for s in student_preferences.index:
        student_prefs = student_preferences.loc[s].tolist()
        happiness_expr = sum(
            vars_dict[(s, h)] * (n_hospitals - rank)**2
            for rank, h in enumerate(student_prefs)
        )
        prob += happiness_expr >= initial_happiness[s]
    
    # Constraint 2: Each student's probabilities sum to 1
    for s in student_preferences.index:
        prob += lpSum(vars_dict[(s, h)] for h in hospitals) == 1
    
    # Constraint 3: Hospital capacity constraints
    for h in hospitals:
        prob += lpSum(vars_dict[(s, h)] for s in student_preferences.index) <= hospital_capacities[h]
    
    # Solve the optimization problem
    prob.solve()
    
    if prob.status != 1:
        raise ValueError("Optimization failed to find a solution")
    
    # Extract solution into DataFrame
    solution = pd.DataFrame(
        0,
        index=student_preferences.index,
        columns=hospitals
    )
    
    for s in student_preferences.index:
        for h in hospitals:
            solution.loc[s, h] = value(vars_dict[(s, h)])
    
    return solution

def print_assignment_stats(
    probs: pd.DataFrame, 
    preferences: pd.DataFrame,
    label: str = ""
):
    """Print statistics about probability assignments"""
    if label:
        print(f"\n{label}:")
        
    n_students = len(preferences)
    
    # Calculate probability of getting kth choice
    for k in range(5):  # Show stats for top 5 choices
        total_prob = 0
        for student_idx in preferences.index:
            kth_choice = preferences.iloc[student_idx, k]
            prob = probs.loc[student_idx, kth_choice]
            total_prob += prob
            
        avg_prob = total_prob / n_students
        print(f"Average probability of getting choice {k+1}: {avg_prob:.3f}")
        