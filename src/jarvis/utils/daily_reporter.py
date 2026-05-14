"""Daily reporting system for Jarvis."""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List
from jarvis.utils.finance_tracker import FinanceTracker


class DailyReporter:
    """Handles daily reports and activity tracking."""

    def __init__(self, log_dir: str = "./logs", data_dir: str = "./data"):
        self.log_dir = log_dir
        self.data_dir = data_dir
        self.activities_file = os.path.join(data_dir, "daily_activities.json")
        self.finance_tracker = FinanceTracker(data_dir)
        os.makedirs(log_dir, exist_ok=True)
        os.makedirs(data_dir, exist_ok=True)
        self._load_activities()

    def _load_activities(self):
        """Load daily activities."""
        if os.path.exists(self.activities_file):
            with open(self.activities_file, 'r') as f:
                self.activities = json.load(f)
        else:
            self.activities = {}

    def _save_activities(self):
        """Save activities to file."""
        with open(self.activities_file, 'w') as f:
            json.dump(self.activities, f, indent=2)

    def log_activity(self, agent_name: str, activity: str, details: Dict = None):
        """Log an activity performed by an agent."""
        today = datetime.now().date().isoformat()
        if today not in self.activities:
            self.activities[today] = {}

        if agent_name not in self.activities[today]:
            self.activities[today][agent_name] = []

        activity_entry = {
            "timestamp": datetime.now().isoformat(),
            "activity": activity,
            "details": details or {}
        }

        self.activities[today][agent_name].append(activity_entry)
        self._save_activities()

    def get_yesterday_report(self) -> Dict:
        """Get report of yesterday's activities."""
        yesterday = (datetime.now() - timedelta(days=1)).date().isoformat()

        activities = self.activities.get(yesterday, {})
        finance_report = self.finance_tracker.get_daily_report()

        return {
            "date": yesterday,
            "activities": activities,
            "finance": finance_report,
            "summary": self._generate_summary(activities, finance_report)
        }

    def get_today_plan(self) -> Dict:
        """Generate plan for today's activities."""
        # This would be more sophisticated in a real implementation
        # For now, return a basic plan
        return {
            "date": datetime.now().date().isoformat(),
            "planned_activities": {
                "Content Creator": ["Generate 2 video ideas", "Create 1 script"],
                "E-commerce Agent": ["Analyze market trends", "Generate business ideas"],
                "Marketing Agent": ["Create social media posts", "Analyze campaign performance"],
                "Social Poster": ["Post to 3 platforms", "Engage with audience"],
                "Video Editor": ["Edit pending videos", "Optimize for platform"],
                "Stream Clipper": ["Monitor streams", "Create shorts"]
            },
            "goals": [
                "Increase engagement by 15%",
                "Generate $50+ in revenue",
                "Create 2 pieces of content"
            ]
        }

    def _generate_summary(self, activities: Dict, finance: Dict) -> str:
        """Generate a human-readable summary."""
        summary_parts = []

        # Activity summary
        total_activities = sum(len(agent_acts) for agent_acts in activities.values())
        summary_parts.append(f"Completed {total_activities} activities across {len(activities)} agents.")

        # Finance summary
        net_daily = finance.get("net_daily", 0)
        if net_daily > 0:
            summary_parts.append(f"Generated ${net_daily:.2f} in profit.")
        elif net_daily < 0:
            summary_parts.append(f"Spent ${abs(net_daily):.2f} on operations.")
        else:
            summary_parts.append("No financial activity.")

        return " ".join(summary_parts)