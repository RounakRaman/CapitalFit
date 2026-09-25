"""
CapitalFit — Financial Sizing & Monetization Model
Replicates the exact calculations and formulas from NBU_Monetization.xlsx
(Opportunity_Sizing, Scenario_Analysis, and Build_Tradeoff).
"""

from typing import Dict, Any, List

class FinancialSizingModel:
    """
    Computes financial metrics, unit economics, net contribution, and ROI
    for CapitalFit (Angel One NBU Stage 1 LAS/MTF Headroom Agent).
    """

    def __init__(
        self,
        total_eligible_accounts: int = 550_000,
        rollout_coverage_pct: float = 70.0,
        avg_headroom_per_account: float = 61_727.0,  # yields ~203.7 Cr book at 0.86% conversion
        gross_interest_apr_pct: float = 12.0,
        cost_of_funds_pct: float = 7.25,
        ecl_pct: float = 0.50,
        year1_build_run_cost_cr: float = 1.20,
    ):
        self.total_eligible_accounts = total_eligible_accounts
        self.rollout_coverage_pct = rollout_coverage_pct
        self.avg_headroom_per_account = avg_headroom_per_account
        self.gross_interest_apr_pct = gross_interest_apr_pct
        self.cost_of_funds_pct = cost_of_funds_pct
        self.ecl_pct = ecl_pct
        self.year1_build_run_cost_cr = year1_build_run_cost_cr

    def calculate_metrics(self, conversion_rate_pct: float) -> Dict[str, Any]:
        """
        Calculates financial performance metrics for a given funded conversion rate.
        """
        # Exposed cohort
        exposed_accounts = int(self.total_eligible_accounts * (self.rollout_coverage_pct / 100.0))
        
        # Funded conversion
        funded_accounts = int(exposed_accounts * (conversion_rate_pct / 100.0))
        
        # Incremental LAS/MTF book (in Crores)
        incremental_book_inr = funded_accounts * self.avg_headroom_per_account
        incremental_book_cr = incremental_book_inr / 10_000_000.0
        
        # Gross interest revenue (in Crores)
        gross_interest_cr = incremental_book_cr * (self.gross_interest_apr_pct / 100.0)
        
        # Cost of funds (in Crores)
        cost_of_funds_cr = incremental_book_cr * (self.cost_of_funds_pct / 100.0)
        
        # Expected Credit Loss (ECL in Crores)
        ecl_cr = incremental_book_cr * (self.ecl_pct / 100.0)
        
        # Total direct variable costs
        total_variable_cost_cr = cost_of_funds_cr + ecl_cr
        
        # Net contribution after funding, ECL, and fixed build/run cost
        gross_margin_cr = gross_interest_cr - total_variable_cost_cr
        net_contribution_cr = gross_margin_cr - self.year1_build_run_cost_cr
        
        # Contribution ROI = Gross Margin / Build & Run Cost
        contribution_roi = gross_margin_cr / self.year1_build_run_cost_cr if self.year1_build_run_cost_cr > 0 else 0.0
        
        return {
            "exposed_accounts": exposed_accounts,
            "funded_accounts": funded_accounts,
            "conversion_rate_pct": round(conversion_rate_pct, 4),
            "incremental_book_cr": round(incremental_book_cr, 2),
            "gross_interest_cr": round(gross_interest_cr, 2),
            "cost_of_funds_cr": round(cost_of_funds_cr, 2),
            "ecl_cr": round(ecl_cr, 2),
            "total_variable_cost_cr": round(total_variable_cost_cr, 2),
            "year1_build_run_cost_cr": round(self.year1_build_run_cost_cr, 2),
            "gross_margin_cr": round(gross_margin_cr, 2),
            "net_contribution_cr": round(net_contribution_cr, 2),
            "contribution_roi": round(contribution_roi, 2),
            "clears_3x_roi_gate": contribution_roi >= 3.0,
        }

    def run_scenario_analysis(self) -> Dict[str, Dict[str, Any]]:
        """
        Runs predefined Worst, Base, and Best case scenarios matching NBU_Monetization.xlsx.
        """
        scenarios = {
            "worst_case": {"name": "Worst Case (0.50% Conv)", "conversion_pct": 0.50},
            "base_case": {"name": "Base Case (0.86% Conv)", "conversion_pct": 0.86},
            "best_case": {"name": "Best Case (1.50% Conv)", "conversion_pct": 1.50},
        }
        
        results = {}
        for key, sc in scenarios.items():
            results[key] = {
                "name": sc["name"],
                **self.calculate_metrics(sc["conversion_pct"]),
            }
        return results

    def generate_sensitivity_curve(
        self, start_conv: float = 0.2, end_conv: float = 2.0, steps: int = 19
    ) -> List[Dict[str, Any]]:
        """
        Generates data points for plotting conversion rate vs Net Contribution & ROI.
        """
        curve = []
        step_size = (end_conv - start_conv) / (steps - 1)
        for i in range(steps):
            c_rate = start_conv + i * step_size
            metrics = self.calculate_metrics(c_rate)
            curve.append(metrics)
        return curve
