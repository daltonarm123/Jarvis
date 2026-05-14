"""Finance tracking for Jarvis."""

import json
import os
from datetime import datetime
from typing import Dict, List


class FinanceTracker:
    """Tracks profits, expenses, and financial metrics."""

    def __init__(self, data_dir: str = "./data"):
        self.data_dir = data_dir
        self.transactions_file = os.path.join(data_dir, "transactions.json")
        self.metrics_file = os.path.join(data_dir, "metrics.json")
        os.makedirs(data_dir, exist_ok=True)
        self._load_data()

    def _load_data(self):
        """Load transaction and metrics data."""
        if os.path.exists(self.transactions_file):
            with open(self.transactions_file, 'r') as f:
                self.transactions = json.load(f)
        else:
            self.transactions = []

        if os.path.exists(self.metrics_file):
            with open(self.metrics_file, 'r') as f:
                self.metrics = json.load(f)
        else:
            self.metrics = {
                "total_profit": 0.0,
                "total_expenses": 0.0,
                "net_profit": 0.0,
                "monthly_profit": {},
                "revenue_sources": {},
                "expense_categories": {}
            }

    def _save_data(self):
        """Save data to files."""
        with open(self.transactions_file, 'w') as f:
            json.dump(self.transactions, f, indent=2)
        with open(self.metrics_file, 'w') as f:
            json.dump(self.metrics, f, indent=2)

    def record_transaction(self, amount: float, category: str, description: str,
                          transaction_type: str = "expense", source: str = "unknown"):
        """Record a financial transaction."""
        transaction = {
            "timestamp": datetime.now().isoformat(),
            "amount": amount,
            "category": category,
            "description": description,
            "type": transaction_type,  # "income" or "expense"
            "source": source
        }

        self.transactions.append(transaction)

        # Update metrics
        if transaction_type == "income":
            self.metrics["total_profit"] += amount
            if source not in self.metrics["revenue_sources"]:
                self.metrics["revenue_sources"][source] = 0
            self.metrics["revenue_sources"][source] += amount
        else:
            self.metrics["total_expenses"] += amount
            if category not in self.metrics["expense_categories"]:
                self.metrics["expense_categories"][category] = 0
            self.metrics["expense_categories"][category] += amount

        self.metrics["net_profit"] = self.metrics["total_profit"] - self.metrics["total_expenses"]

        # Monthly tracking
        month = datetime.now().strftime("%Y-%m")
        if month not in self.metrics["monthly_profit"]:
            self.metrics["monthly_profit"][month] = 0
        if transaction_type == "income":
            self.metrics["monthly_profit"][month] += amount
        else:
            self.metrics["monthly_profit"][month] -= amount

        self._save_data()

    def get_daily_report(self) -> Dict:
        """Get financial report for today."""
        today = datetime.now().date().isoformat()
        today_transactions = [
            t for t in self.transactions
            if t["timestamp"].startswith(today)
        ]

        return {
            "date": today,
            "transactions": today_transactions,
            "daily_profit": sum(t["amount"] for t in today_transactions if t["type"] == "income"),
            "daily_expenses": sum(t["amount"] for t in today_transactions if t["type"] == "expense"),
            "net_daily": sum(t["amount"] if t["type"] == "income" else -t["amount"] for t in today_transactions)
        }

    def get_summary(self) -> Dict:
        """Get overall financial summary."""
        return self.metrics.copy()