"""
Refactored UserReport — Single Responsibility Principle.

Original problem:
    class UserReport mixed three unrelated responsibilities:
    1. business logic   → calculate_stats (avg age, total salary)
    2. presentation     → format_as_html, format_as_csv
    3. delivery         → send_email

    Any change to stats formulas, output formats, or email logic
    would touch the same class, bloating it and risking regressions
    in unrelated concerns. A class should have only one reason to
    change.

Solution:
    Split into two focused classes:

    UserStats     — "calculates things"
        Responsibility: data computation only. Changes only when
        stats formulas change.

    ReportPresenter — "shows and sends things"
        Responsibility: formatting + delivery. Changes only when
        output formats or notification channels change.

    This way, adding a JSON format won't risk breaking stats logic,
    and changing salary calculation won't break the email sender.
"""


class UserStats:
    """Computes statistics from user data."""
    
    def __init__(self, users):
        self.users = users
    
    def calculate_stats(self):
        total_age = sum(u["age"] for u in self.users)
        total_salary = sum(u["salary"] for u in self.users)
        count = len(self.users)
        return {
            "avg_age": total_age / count if count else 0,
            "total_salary": total_salary,
            "count": count,
        }


class ReportPresenter:
    """Formats stats into reports and sends them via email."""
    
    @staticmethod
    def format_as_html(stats):
        rows = "".join(
            f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in stats.items()
        )
        return f"<table>{rows}</table>"
    
    @staticmethod
    def format_as_csv(stats):
        header = ",".join(stats.keys())
        values = ",".join(str(v) for v in stats.values())
        return f"{header}\n{values}"
    
    @staticmethod
    def send_email(report, recipient):
        print(f"Sending report to {recipient}:\n{report}")


if __name__ == "__main__":
    users = [
        {"age": 25, "salary": 50000},
        {"age": 30, "salary": 70000},
        {"age": 35, "salary": 90000},
    ]

    stats_calc = UserStats(users)
    stats = stats_calc.calculate_stats()

    html = ReportPresenter.format_as_html(stats)
    csv = ReportPresenter.format_as_csv(stats)

    print("=== HTML ===")
    print(html)
    print("\n=== CSV ===")
    print(csv)
    print()
    ReportPresenter.send_email(html, "manager@example.com")
