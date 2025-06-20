from flask import Flask, render_template, request, redirect, session, flash, send_file
import pandas as pd
import os
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

app = Flask(__name__)
app.secret_key = "supersecretkey"
UPLOAD_FOLDER = "uploads"
STATIC_FOLDER = "static"
MERGED_FILE_PATH = os.path.join(STATIC_FOLDER, "merged_statement.csv")
USERS_FILE = "users.json"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(STATIC_FOLDER, exist_ok=True)

REQUIRED_COLUMNS = ["Date", "Transaction ID", "Amount", "Category", "Transaction Type", "Account Name (Sender)"]

# Helper functions for user authentication
def load_users():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

# Route: Signup
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        users = load_users()

        if any(u["username"] == username for u in users):
            flash("Username already exists.", "danger")
            return redirect("/signup")

        new_id = max([u["id"] for u in users], default=0) + 1
        users.append({"id": new_id, "username": username, "password": password})
        save_users(users)

        flash("Signup successful! Please login.", "success")
        return redirect("/login")

    return render_template("signup.html")

# Route: Login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        users = load_users()

        user = next((u for u in users if u["username"] == username and u["password"] == password), None)
        if user:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            flash("Login successful!", "success")
            return redirect("/")
        else:
            flash("Invalid credentials.", "danger")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect("/login")

@app.route("/")
def index():
    if "user_id" not in session:
        flash("Please login to access the dashboard.", "warning")
        return redirect("/login")
    return render_template("index.html", username=session["username"])

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/project-diagram")
def project_diagram():
    return render_template("projectdig.html")

@app.route("/upload", methods=["POST"])
def upload_files():
    files = request.files.getlist("files[]")
    all_data = []

    for file in files:
        if file.filename.endswith(".csv"):
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
            file.save(filepath)
            df = pd.read_csv(filepath)

            missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
            if missing:
                flash(f"{file.filename} missing: {', '.join(missing)}", "danger")
                continue

            df["Source"] = file.filename
            all_data.append(df)

    if not all_data:
        return render_template("index.html", error="No valid files uploaded.")

    data = pd.concat(all_data, ignore_index=True)
    data.to_csv(MERGED_FILE_PATH, index=False)

    data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
    data = data.dropna(subset=["Date"])

    # Generate plots
    plot_total_spending(data)
    plot_category_spending(data)
    plot_transactions_by_day(data)
    plot_transaction_pie(data)
    plot_transactions_by_category(data)
    plot_spending_by_type(data)
    plot_monthly_spending_trend(data)
    plot_top_categories_by_spending(data)

    # Max transaction day
    tx_by_day = data.groupby("Date")["Transaction ID"].count()
    max_day = tx_by_day.idxmax()
    max_count = tx_by_day.max()

    balances = calculate_account_balances(data)

    return render_template("dashboard.html",
        total_spending_path="/static/total_spending.png",
        category_spending_path="/static/category_spending.png",
        transactions_by_day_path="/static/transactions_by_day.png",
        pie_chart_path="/static/transaction_pie_chart.png",
        transactions_by_category_path="/static/transactions_by_category.png",
        spending_by_type_path="/static/spending_by_type.png",
        monthly_spending_path="/static/monthly_spending.png",
        top_categories_path="/static/top_categories.png",
        balances=balances,
        max_day=max_day,
        max_day_transactions=max_count
    )

def calculate_account_balances(data):
    credits = data[data["Transaction Type"] == "Credit"].groupby("Account Name (Sender)")["Amount"].sum()
    debits = data[data["Transaction Type"] == "Debit"].groupby("Account Name (Sender)")["Amount"].sum()

    balances = pd.concat([credits, debits], axis=1, keys=["Credits", "Debits"])
    balances["Net Balance"] = balances["Credits"].fillna(0) - balances["Debits"].fillna(0)
    return balances.fillna(0).round(2).reset_index().to_dict(orient="records")

@app.route("/account-balances")
def account_balances():
    if not os.path.exists(MERGED_FILE_PATH):
        flash("No merged data found.", "danger")
        return redirect("/")
    df = pd.read_csv(MERGED_FILE_PATH)
    balances = calculate_account_balances(df)
    return render_template("account_balances.html", balances=balances)

@app.route("/download")
def download_merged_statement():
    if os.path.exists(MERGED_FILE_PATH):
        return send_file(MERGED_FILE_PATH, as_attachment=True)
    flash("No merged statement available.", "danger")
    return redirect("/")

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

# Plotting functions (same as before)
def plot_total_spending(data):
    path = os.path.join(STATIC_FOLDER, "total_spending.png")
    data.groupby("Account Name (Sender)")["Amount"].sum().plot(kind="bar", figsize=(10, 5), title="Total Spending")
    plt.ylabel("Amount")
    plt.tight_layout(); plt.savefig(path); plt.close()

def plot_category_spending(data):
    path = os.path.join(STATIC_FOLDER, "category_spending.png")
    df = data.groupby(["Category", "Account Name (Sender)"])["Amount"].sum().unstack()
    df.plot(kind="bar", stacked=True, figsize=(12, 6), title="Category Spending")
    plt.ylabel("Amount")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout(); plt.savefig(path); plt.close()

def plot_transactions_by_day(data):
    path = os.path.join(STATIC_FOLDER, "transactions_by_day.png")
    df = data.groupby([data["Date"].dt.date, "Source"])["Transaction ID"].count().unstack()
    df.plot(figsize=(12, 6), title="Transactions by Day")
    plt.xlabel("Date"); plt.ylabel("Count")
    plt.tight_layout(); plt.savefig(path); plt.close()

def plot_transaction_pie(data):
    path = os.path.join(STATIC_FOLDER, "transaction_pie_chart.png")
    data["Source"].value_counts().plot(kind="pie", autopct="%1.1f%%", title="Transactions by Source", figsize=(8, 8))
    plt.ylabel("")
    plt.tight_layout(); plt.savefig(path); plt.close()

def plot_transactions_by_category(data):
    path = os.path.join(STATIC_FOLDER, "transactions_by_category.png")
    data["Category"].value_counts().plot(kind="bar", color="skyblue", title="Transactions by Category", figsize=(10, 5))
    plt.xlabel("Category"); plt.ylabel("Count")
    plt.tight_layout(); plt.savefig(path); plt.close()

def plot_spending_by_type(data):
    path = os.path.join(STATIC_FOLDER, "spending_by_type.png")
    data.groupby("Transaction Type")["Amount"].sum().plot(kind="bar", color="orange", title="Spending by Type", figsize=(8, 5))
    plt.ylabel("Amount")
    plt.tight_layout(); plt.savefig(path); plt.close()

def plot_monthly_spending_trend(data):
    path = os.path.join(STATIC_FOLDER, "monthly_spending.png")
    data["YearMonth"] = data["Date"].dt.to_period("M")
    data.groupby("YearMonth")["Amount"].sum().plot(kind="line", marker="o", title="Monthly Trend", figsize=(10, 5))
    plt.ylabel("Amount")
    plt.tight_layout(); plt.savefig(path); plt.close()

def plot_top_categories_by_spending(data):
    path = os.path.join(STATIC_FOLDER, "top_categories.png")
    data.groupby("Category")["Amount"].sum().nlargest(5).plot(kind="bar", color="purple", title="Top 5 Categories", figsize=(10, 5))
    plt.ylabel("Amount")
    plt.tight_layout(); plt.savefig(path); plt.close()

if __name__ == "__main__":
    app.run(debug=True)