from datetime import datetime, timedelta

class ReportGenerator:
    def __init__(self, inventory_manager):
        self.inventory_manager = inventory_manager

    def generate_low_stock_report(self):
        low_stock_items = {
            code: details for code, details in 
            self.inventory_manager.inventory.items() 
            if details['quantity'] <= details['reorder_point']
        }
        return low_stock_items

    def generate_expenditure_report(self, expenses_file_path=None, start_date=None, end_date=None):
        """
        Generate a business expenditure report from expenses.json, with optional date range.
        Returns a dict with total and breakdown by category.
        """
        import json, os
        # Default path if not provided
        if not expenses_file_path:
            expenses_file_path = os.path.join(os.path.dirname(__file__), '../accounting_data/expenses.json')

        # Load expenses
        if not os.path.exists(expenses_file_path):
            return {'total_expenses': 0, 'expenses_by_category': {}}
        with open(expenses_file_path, 'r', encoding='utf-8') as f:
            try:
                expenses = json.load(f)
            except Exception:
                return {'total_expenses': 0, 'expenses_by_category': {}}

        # Filter by date range if provided
        filtered_expenses = []
        for expense in expenses:
            expense_date = expense.get('expense_date') or expense.get('date')
            if not expense_date:
                continue
            try:
                dt = datetime.strptime(expense_date[:10], '%Y-%m-%d')
            except Exception:
                continue
            if start_date and dt < start_date:
                continue
            if end_date and dt > end_date:
                continue
            filtered_expenses.append(expense)

        # Aggregate
        total = 0
        by_category = {}
        for exp in filtered_expenses:
            amount = float(exp.get('amount', 0))
            category = exp.get('category', 'Uncategorized')
            total += amount
            by_category[category] = by_category.get(category, 0) + amount
        return {'total_expenses': total, 'expenses_by_category': by_category}

    def generate_full_audit_report(self, expenses_file_path=None, start_date=None, end_date=None):
        """
        Executes all reporting modules and compiles them into a single comprehensive dictionary structure.
        """
        low_stock = self.generate_low_stock_report()
        expenditures = self.generate_expenditure_report(
            expenses_file_path=expenses_file_path, 
            start_date=start_date, 
            end_date=end_date
        )

        return {
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'low_stock_report': low_stock,
            'expenditure_report': expenditures
        }