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
    plan_until_age: int = 90 # New field
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
        
        # Dynamic Goal calculation: 
        # The goal is the portfolio value needed at retirement age 
        # to survive until plan_until_age with inflation.
        # This is a present value of an annuity problem with growing payments.
        plan_months = (self.inputs.plan_until_age - self.inputs.target_retire_age) * 12
        # Use target_months (accumulation duration) to find future inflated spend at start of retirement
        accumulation_months = (self.inputs.target_retire_age - self.inputs.current_age) * 12
        
        # Rule of thumb goal (for comparison/legacy)
        swr_decimal = max(0.001, self.inputs.swr) / 100
        fire_number_today = (target_monthly_spend * 12) / swr_decimal
        
        portfolio = self.inputs.current_portfolio
        if self.inputs.portfolio_mode == "Granular":
            amounts = [b.value for b in self.inputs.buckets if b.type == "amount"]
            if amounts: portfolio = sum(amounts)

        principal_cumulative = portfolio
        combined_history = []
        
        # Month 0
        combined_history.append({
            "month": 0, "age": float(self.inputs.current_age), "real_portfolio": round(portfolio, 2),
            "real_principal": round(portfolio, 2), "real_interest": 0.0, "phase": "accumulation"
        })

        reached_fire_age = None
        current_monthly_deposit = monthly_dep_override if monthly_dep_override is not None else self.inputs.monthly_deposit
        
        # 1. Accumulation Phase
        for month in range(1, accumulation_months + 1):
            year = month // 12
            portfolio = portfolio * (1 + monthly_return)
            if year < self.inputs.contribution_duration:
                portfolio += current_monthly_deposit
                principal_cumulative += current_monthly_deposit
                if month % 12 == 0:
                    current_monthly_deposit *= (1 + annual_step_up)
            
            real_portfolio = portfolio / ((1 + monthly_inflation) ** month)
            real_principal = principal_cumulative / ((1 + monthly_inflation) ** month)
            
            combined_history.append({
                "month": month, "age": round(self.inputs.current_age + (month / 12), 1),
                "real_portfolio": round(real_portfolio, 2), "real_principal": round(real_principal, 2),
                "real_interest": round(real_portfolio - real_principal, 2),
                "phase": "accumulation"
            })
            if reached_fire_age is None and real_portfolio >= fire_number_today:
                reached_fire_age = self.inputs.current_age + (month / 12)

        portfolio_at_retire = portfolio
        real_portfolio_at_retire = combined_history[-1]["real_portfolio"]

        # 2. Withdrawal Phase
        burn_portfolio = portfolio_at_retire
        start_age = self.inputs.target_retire_age
        withdrawal_history = []
        
        # Add withdrawal phase until death_age (default 90) or depletion
        withdrawal_months = (self.inputs.plan_until_age - self.inputs.target_retire_age) * 12
        for month in range(1, withdrawal_months + 1):
            total_months_from_now = month + accumulation_months
            inflated_spend = target_monthly_spend * ((1 + monthly_inflation) ** total_months_from_now)
            withdrawal_needed = inflated_spend / (1 - self.inputs.tax_rate / 100)
            
            growth = burn_portfolio * monthly_return
            burn_portfolio = burn_portfolio + growth - withdrawal_needed
            
            age = round(start_age + (month / 12), 1)
            real_burn_portfolio = burn_portfolio / ((1 + monthly_inflation) ** total_months_from_now)
            
            record = {
                "month": total_months_from_now, "age": age,
                "real_portfolio": round(real_burn_portfolio, 2),
                "phase": "withdrawal"
            }
            combined_history.append(record)
            withdrawal_history.append(record)
            if burn_portfolio <= 0: break

        return {
            "accumulation_history": [h for h in combined_history if h["phase"] == "accumulation"],
            "runway_history": [h for h in combined_history if h["phase"] == "withdrawal"],
            "full_history": combined_history,
            "reached_fire_age": round(reached_fire_age, 1) if reached_fire_age else None,
            "fire_number_real": round(fire_number_today, 2),
            "portfolio_at_retire_real": round(real_portfolio_at_retire, 2),
            "depletion_age": combined_history[-1]["age"] if len(combined_history) > 1 else start_age,
            "is_depleted": burn_portfolio <= 0,
            "on_track": (reached_fire_age is not None) and (reached_fire_age <= self.inputs.target_retire_age)
        }

    def run_simulation(self):
        scenarios = {}
        target_monthly_spend = self.inputs.target_monthly_spend
        
        types = [("Lean", 0.7), ("Standard", 1.0), ("Fat", 1.5)]
        for name, mult in types:
            spend = target_monthly_spend * mult
            if self.inputs.simulation_mode == "Reverse":
                sim = self._run_reverse_sim(spend)
            else:
                sim = self._run_single_sim(spend)
                
                # Extra monthly needed
                if not sim["on_track"]:
                    low = self.inputs.monthly_deposit
                    high = self.inputs.monthly_deposit + 20000
                    for _ in range(15):
                        mid = (low + high) / 2
                        test_sim = self._run_single_sim(spend, mid)
                        if test_sim["on_track"]: high = mid
                        else: low = mid
                    sim["extra_monthly_needed"] = round(high - self.inputs.monthly_deposit, 0)
                else:
                    sim["extra_monthly_needed"] = 0
            
            # Subsample for UI performance (yearly points)
            sim["accumulation_history"] = sim["accumulation_history"][::12]
            sim["runway_history"] = sim["runway_history"][::12]
            sim["full_history"] = sim["full_history"][::12]
            scenarios[name] = sim

        return {
            "scenarios": scenarios,
            "annual_return_used": round(self._get_annual_return(), 2)
        }

    def _run_reverse_sim(self, target_monthly_spend):
        annual_return = self._get_annual_return()
        monthly_return = (1 + annual_return / 100) ** (1/12) - 1
        monthly_inflation = (1 + self.inputs.inflation_rate / 100) ** (1/12) - 1
        
        portfolio = self.inputs.current_portfolio
        if self.inputs.portfolio_mode == "Granular":
            amounts = [b.value for b in self.inputs.buckets if b.type == "amount"]
            if amounts: portfolio = sum(amounts)

        history = []
        burn_portfolio = portfolio
        start_age = self.inputs.current_age
        
        history.append({
            "month": 0, "age": float(start_age), "real_portfolio": round(portfolio, 2)
        })

        for month in range(1, 12 * 100):
            inflated_spend = target_monthly_spend * ((1 + monthly_inflation) ** month)
            withdrawal_needed = inflated_spend / (1 - self.inputs.tax_rate / 100)
            
            growth = burn_portfolio * monthly_return
            burn_portfolio = burn_portfolio + growth - withdrawal_needed
            
            age = round(start_age + (month / 12), 1)
            real_burn_portfolio = burn_portfolio / ((1 + monthly_inflation) ** month)
            history.append({
                "month": month, "age": age,
                "real_portfolio": round(real_burn_portfolio, 2)
            })
            if burn_portfolio <= 0: break
            if age >= 100: break

        return {
            "accumulation_history": [],
            "runway_history": history,
            "reached_fire_age": None,
            "fire_number_real": (target_monthly_spend * 12) / (self.inputs.swr / 100),
            "portfolio_at_retire_real": round(portfolio, 2),
            "depletion_age": history[-1]["age"] if len(history) > 1 else start_age,
            "is_depleted": burn_portfolio <= 0,
            "on_track": True
        }

    def run_simulation(self):
        scenarios = {}
        target_monthly_spend = self.inputs.target_monthly_spend
        
        types = [("Lean", 0.7), ("Standard", 1.0), ("Fat", 1.5)]
        for name, mult in types:
            spend = target_monthly_spend * mult
            if self.inputs.simulation_mode == "Reverse":
                sim = self._run_reverse_sim(spend)
            else:
                sim = self._run_single_sim(spend)
                
                # Extra monthly needed
                if not sim["on_track"]:
                    low = self.inputs.monthly_deposit
                    high = self.inputs.monthly_deposit + 20000
                    for _ in range(15):
                        mid = (low + high) / 2
                        test_sim = self._run_single_sim(spend, mid)
                        if test_sim["on_track"]: high = mid
                        else: low = mid
                    sim["extra_monthly_needed"] = round(high - self.inputs.monthly_deposit, 0)
                else:
                    sim["extra_monthly_needed"] = 0
            
            sim["accumulation_history"] = sim["accumulation_history"][::12]
            sim["runway_history"] = sim["runway_history"][::12]
            scenarios[name] = sim

        return {
            "scenarios": scenarios,
            "annual_return_used": round(self._get_annual_return(), 2)
        }
