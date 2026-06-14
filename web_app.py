from flask import Flask, render_template, request, redirect, send_file
from expense import Expense
import calendar
import datetime
import os
import shutil
import csv

app = Flask(__name__)
expense_file_path = "expenses.csv"
income_file_path = "income.txt"
last_month_file = ".last_month.txt"
archive_folder = "archives"

os.makedirs(archive_folder, exist_ok=True)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Handle expense submission
        name = request.form.get("name")
        amount = request.form.get("amount")
        category = request.form.get("category")

        if name and amount and category:
            expense = Expense(name=name, amount=float(amount), category=category)
            save_expense_to_file(expense, expense_file_path)
        return redirect("/")

    # GET request: load data
    income = load_income()
    summary, total_spent, remaining_budget, daily_budget = summarise_expenses(expense_file_path, income)

    return render_template("index.html",
        categories=get_categories(),
        summary=summary,
        total_spent=total_spent,
        remaining_budget=remaining_budget,
        daily_budget=daily_budget,
                           
        income=income,
        current_budget=income  # used in template
    )

@app.route("/add_income", methods=["POST"])
def add_income():
    income = request.form.get("income")
    if income:
        save_income(float(income))
    return redirect("/")

@app.route("/download")
def download():
    if os.path.exists(expense_file_path):
        return send_file(expense_file_path, as_attachment=True)
    return "No expenses to download yet.", 404

def get_categories():
    return [
        "🍔 Food", 
        "🏡 Bills", 
        "🚐 Travel", 
        "🎉 Fun", 
        "✨ Misc",
        "🪡 Sewing",
        "🐍 Coding",
    ]

def save_expense_to_file(expense, path):
    check_and_archive_expenses(path)

    file_exists = os.path.exists(path)
    is_new_file = not file_exists or os.path.getsize(path) == 0

    with open(path, "a") as f:
        if is_new_file:
            f.write("Expense Name,Expense Amount,Expense Category\n")
        f.write(f"{expense.name},{expense.amount},{expense.category}\n")

def check_and_archive_expenses(path):
    now = datetime.datetime.now()
    current_month = now.strftime("%Y-%m")

    # Read last processed month
    if os.path.exists(last_month_file):
        with open(last_month_file, "r") as f:
            last_month = f.read().strip()
    else:
        last_month = ""

    # Archive if month has changed
    if last_month != current_month:
        # Move CSV and income file into archive
        if os.path.exists(path) and os.path.getsize(path) > 0:
            archive_name = os.path.join(archive_folder, f"expenses_{last_month if last_month else 'unknown'}.csv")
            shutil.move(path, archive_name)

        if os.path.exists(income_file_path):
            income_archive = os.path.join(archive_folder, f"income_{last_month if last_month else 'unknown'}.txt")
            shutil.move(income_file_path, income_archive)

        with open(last_month_file, "w") as f:
            f.write(current_month)

def save_income(amount):
    with open(income_file_path, "w") as f:
        f.write(str(amount))

def load_income():
    if os.path.exists(income_file_path):
        with open(income_file_path, "r") as f:
            try:
                return float(f.read().strip())
            except ValueError:
                return 0
    return 0

def summarise_expenses(path, budget):
    if not os.path.exists(path):
        return {}, 0, budget, budget  # no expenses yet

    expenses = []

    with open(path, "r", newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                name = row["Expense Name"]
                amount = float(row["Expense Amount"])
                category = row["Expense Category"]
                expenses.append(Expense(name=name, amount=amount, category=category))
            except (KeyError, ValueError):
                continue

    amount_by_category = {}
    for expense in expenses:
        amount_by_category[expense.category] = amount_by_category.get(expense.category, 0) + expense.amount

    total_spent = sum(e.amount for e in expenses)
    remaining_budget = budget - total_spent

    now = datetime.datetime.now()
    days_in_month = calendar.monthrange(now.year, now.month)[1]
    remaining_days = max(days_in_month - now.day, 1)
    daily_budget = remaining_budget / remaining_days

    return amount_by_category, total_spent, remaining_budget, daily_budget

if __name__ == "__main__":
    app.run(debug=True, port=5000)
