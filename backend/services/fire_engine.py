import numpy as np
import logging
from typing import Dict, List, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class AssetBucket(BaseModel):
    name: str = "Assets"
    value: float = 0.0
    expected_return: float = 7.0
    type: str = "percent" # "percent" or "amount"

class FIREInput(BaseModel):
    current_age: int = 30
    target_retire_age: int = 50
    current_portfolio: float = 100000
    target_monthly_spend: float = 5000
    swr: float = 4.0 # Safe Withdrawal Rate %
    
    # Portfolio Bucket
    portfolio_mode: str = "Simple" # Simple or Granular
    expected_return: float = 7.0 # % annual (used in Simple mode)
    buckets: List[AssetBucket] = [] # Used in Granular mode
    
    # Contributions
    monthly_deposit: float = 2000
    contribution_step_up: float = 0.0 # % annual raise
    contribution_duration: int = 20 # years
    
    inflation_rate: float = 3.0 # % annual
    tax_rate: float = 15.0 # % flat tax on total or gains
    
    simulation_mode: str = "Direct" # "Direct" (Road to FIRE) or "Reverse" (Burn Rate)

class FIREEngine:
    def __init__(self, inputs: FIREInput):
        self.inputs = inputs
        
    def _get_annual_return(self):
        if self.inputs.portfolio_mode == "Granular" and self.inputs.buckets:
            total_val = sum(b.value for b in self.inputs.buckets if b.type == "amount")
            if total_val == 0:
                total_pct = sum(b.value for b in self.inputs.buckets if b.type == "percent")
                if total_pct > 0:
                    return sum((b.value / total_pct) * b.expected_return for b in self.inputs.buckets)
                return self.inputs.expected_return
            return sum((b.value / total_val) * b.expected_return for b in self.inputs.buckets if b.type == "amount")
        return self.inputs.expected_return

    def _run_single_sim(self, target_monthly_spend, monthly_dep_override=None):
        annual_return = self._get_annual_return()
        monthly_return = (1 + annual_return / 100) ** (1/12) - 1
        monthly_inflation = (1 + self.inputs.inflation_rate / 100) ** (1/12) - 1
        annual_step_up = self.inputs.contribution_step_up / 100
        
        swr_decimal = self.inputs.swr / 100
        fire_number_today = (target_monthly_spend * 12) / swr_decimal
        
        portfolio = self.inputs.current_portfolio
        if self.inputs.portfolio_mode == "Granular":
            amounts = [b.value for b in self.inputs.buckets if b.type == "amount"]
            if amounts: portfolio = sum(amounts)

        principal_cumulative = portfolio
        history = []
        
        # Month 0
        history.append({
            "month": 0,
            "age": float(self.inputs.current_age),
            "real_portfolio": round(portfolio, 2),
            "real_principal": round(portfolio, 2),
            "real_interest": 0.0
        })

        reached_fire_age = None
        current_monthly_deposit = monthly_dep_override if monthly_dep_override is not None else self.inputs.monthly_deposit
        
        # Simulation duration
        target_months = (self.inputs.target_retire_age - self.inputs.current_age) * 12
        max_view_months = max(target_months, 12 * 40) # At least 40 years view
        
        for month in range(1, max_view_months + 1):
            year = month // 12
            portfolio = portfolio * (1 + monthly_return)
            
            if year < self.inputs.contribution_duration:
                portfolio += current_monthly_deposit
                principal_cumulative += current_monthly_deposit
                if month % 12 == 0:
                    current_monthly_deposit *= (1 + annual_step_up)
            
            real_portfolio = portfolio / ((1 + monthly_inflation) ** month)
            real_principal = principal_cumulative / ((1 + monthly_inflation) ** month)
            
            history.append({
                "month": month,
                "age": round(self.inputs.current_age + (month / 12), 1),
                "real_portfolio": round(real_portfolio, 2),
                "real_principal": round(real_principal, 2),
                "real_interest": round(real_portfolio - real_principal, 2)
            })
            
            if reached_fire_age is None and real_portfolio >= fire_number_today:
                reached_fire_age = self.inputs.current_age + (month / 12)

        portfolio_at_retire = history[min(len(history)-1, target_months)]["real_portfolio"]

        return {
            "history": history,
            "reached_fire_age": round(reached_fire_age, 1) if reached_fire_age else None,
            "fire_number_today": fire_number_today,
            "portfolio_at_retire_real": portfolio_at_retire
        }

    def _calculate_runway(self, start_portfolio, target_monthly_spend, start_age):
        annual_return = self._get_annual_return()
        monthly_return = (1 + annual_return / 100) ** (1/12) - 1
        monthly_inflation = (1 + self.inputs.inflation_rate / 100) ** (1/12) - 1
        
        runway = []
        burn_portfolio = start_portfolio
        
        # Add initial state
        runway.append({
            "month": 0,
            "age": float(start_age),
            "real_portfolio": round(burn_portfolio, 2)
        })
        
        for month in range(1, 12 * 80):
            # Inflation adjusted spend from 'now'
            total_months_from_now = month
            if self.inputs.simulation_mode == "Direct":
                total_months_from_now += (self.inputs.target_retire_age - self.inputs.current_age) * 12
                
            inflated_spend = target_monthly_spend * ((1 + monthly_inflation) ** total_months_from_now)
            withdrawal_needed = inflated_spend / (1 - self.inputs.tax_rate / 100)
            
            growth = burn_portfolio * monthly_return
            burn_portfolio = burn_portfolio + growth - withdrawal_needed
            
            real_burn_portfolio = burn_portfolio / ((1 + monthly_inflation) ** total_months_from_now)
            
            runway.append({
                "month": month,
                "age": round(start_age + (month / 12), 1),
                "real_portfolio": round(real_burn_portfolio, 2)
            })
            
            if burn_portfolio <= 0: break
            if month > 12 * 60: break # Max 60 years runway view
            
        return runway

    def run_simulation(self):
        scenarios = {
            "Lean": self.inputs.target_monthly_spend * 0.7,
            "Standard": self.inputs.target_monthly_spend,
            "Fat": self.inputs.target_monthly_spend * 1.5
        }
        
        results = {}
        # Get actual current portfolio to ensure consistency
        current_portfolio = self.inputs.current_portfolio
        if self.inputs.portfolio_mode == "Granular":
            amounts = [b.value for b in self.inputs.buckets if b.type == "amount"]
            if amounts: current_portfolio = sum(amounts)

        for name, spend in scenarios.items():
            sim = self._run_single_sim(spend)
            
            # Calculate gap if not on track
            extra_needed = 0
            if sim["reached_fire_age"] is None or sim["reached_fire_age"] > self.inputs.target_retire_age:
                # Binary search for monthly deposit needed
                low = self.inputs.monthly_deposit
                high = self.inputs.monthly_deposit + 20000
                for _ in range(15):
                    mid = (low + high) / 2
                    test_sim = self._run_single_sim(spend, mid)
                    if test_sim["reached_fire_age"] and test_sim["reached_fire_age"] <= self.inputs.target_retire_age:
                        high = mid
                    else:
                        low = mid
                extra_needed = high - self.inputs.monthly_deposit

            runway = self._calculate_runway(
                sim["portfolio_at_retire_real"] if self.inputs.simulation_mode == "Direct" else current_portfolio,
                spend,
                self.inputs.target_retire_age if self.inputs.simulation_mode == "Direct" else self.inputs.current_age
            )

            results[name] = {
                "fire_number_real": round(sim["fire_number_today"], 2),
                "reached_fire_age": sim["reached_fire_age"],
                "on_track": sim["reached_fire_age"] <= self.inputs.target_retire_age if sim["reached_fire_age"] else False,
                "extra_monthly_needed": round(extra_needed, 0),
                "accumulation_history": sim["history"][::12],
                "runway_history": runway[::12],
                "depletion_age": runway[-1]["age"] if runway else (self.inputs.target_retire_age if self.inputs.simulation_mode == "Direct" else self.inputs.current_age),
                "portfolio_at_retire_real": round(sim["portfolio_at_retire_real"] if self.inputs.simulation_mode == "Direct" else current_portfolio, 2)
            }
            
        return {
            "scenarios": results,
            "annual_return_used": round(self._get_annual_return(), 2)
        }
