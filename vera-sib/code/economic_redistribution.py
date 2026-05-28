"""
Economic Redistribution — Phase 1 W2
Validate fairness-aware compensation
"""
import json
import numpy as np
import os

class RedistributionEngine:
    """Simulate fair redistribution under VERA constraints"""
    
    def __init__(self, gini_target=0.3):
        self.gini_target = gini_target
        self.total_pool = 10000  # $10k total compensation pool
    
    def redistribute(self, contributions, gini_limit=0.3):
        """
        Redistribute compensation based on contributions
        
        Constraint: Gini < gini_limit (fairness enforced)
        """
        
        # Normalize contributions to [0, 1]
        norm_contrib = contributions / np.sum(contributions)
        
        # Direct redistribution (proportional)
        compensation = norm_contrib * self.total_pool
        
        # Calculate resulting Gini
        gini = self.calculate_gini(compensation)
        
        # If Gini > limit, apply fairness constraint
        if gini > gini_limit:
            compensation = self.apply_fairness_cap(contributions, gini_limit)
        
        return compensation
    
    def calculate_gini(self, distribution):
        """Calculate Gini coefficient"""
        sorted_dist = np.sort(distribution)
        n = len(sorted_dist)
        
        if np.sum(sorted_dist) == 0:
            return 0
        
        gini = (2 * np.sum((n + 1 - np.arange(1, n + 1)) * sorted_dist)) / (n * np.sum(sorted_dist)) - (n + 1) / n
        return float(gini)
    
    def apply_fairness_cap(self, contributions, gini_limit):
        """Apply fairness constraint to reduce Gini"""
        
        # Cap top earners
        norm_contrib = contributions / np.sum(contributions)
        compensation = norm_contrib * self.total_pool
        
        # Enforce: no creator gets > 5% of total pool
        max_per_creator = self.total_pool * 0.05
        compensation = np.minimum(compensation, max_per_creator)
        
        # Redistribute excess to others
        excess = np.sum(com
