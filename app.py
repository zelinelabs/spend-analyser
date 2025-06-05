from flask import Flask, render_template, request, redirect, session, flash, send_file
import pandas as pd
import os
import mysql.connector
import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend for macOS
import matplotlib.pyplot as plt

app = Flask(__name__)
app.secret_key = "supersecretkey"  # For session management
UPLOAD_FOLDER = "uploads"
STATIC_FOLDER = "static"
MERGED_FILE_PATH = os.path.join(STATIC_FOLDER, "merged_statement.csv")  # Path to save the merged CSV file

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(STATIC_FOLDER, exist_ok=True)

# MySQL configuration
db_config = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "user_auth",
}

# Connect to MySQL
def get_db_connection():
    return mysql.connector.connect(**db_config)

# Required columns for analysis
REQUIRED_COLUMNS = ["Date", "Transaction ID", "Amount", "Category", "Transaction Type", "Account Name (Sender)"]

# Route: Signup
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
            conn.commit()
            conn.close()
            flash("Signup successful! Please login.", "success")
            return redirect("/login")
        except mysql.connector.Error as e:
            flash(f"Error: {e}", "danger")
            return redirect("/signup")

    return render_template("signup.html")

# Route: Login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            flash("Login successful!", "success")
            return redirect("/")
        else:
            flash("Invalid credentials. Please try again.", "danger")

    return render_template("login.html")

# Route: Logout
@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect("/login")

# Route: Home (requires login)
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
    """Render the project diagram page."""
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

            # Validate if the required columns are present
            missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
            if missing_columns:
                flash(f"File {file.filename} is missing columns: {', '.join(missing_columns)}", "error")
                continue

            df['Source'] = file.filename  # Add source column for each file
            all_data.append(df)

    if not all_data:
        return render_template("index.html", error="No valid CSV files uploaded or missing required columns.")

    # Combine all valid data
    combined_data = pd.concat(all_data, ignore_index=True)

    # Save the merged data to a CSV file
    combined_data.to_csv(MERGED_FILE_PATH, index=False)

    # Ensure the Date column is in datetime format
    combined_data["Date"] = pd.to_datetime(combined_data["Date"], errors='coerce')
    combined_data = combined_data.dropna(subset=["Date"])  # Drop rows with invalid dates

    # Generate insights
    total_spending_path = plot_total_spending(combined_data)
    category_spending_path = plot_category_spending(combined_data)
    transactions_by_day_path = plot_transactions_by_day(combined_data)
    pie_chart_path = plot_transaction_pie(combined_data)
    transactions_by_category_path = plot_transactions_by_category(combined_data)
    spending_by_type_path = plot_spending_by_type(combined_data)
    monthly_spending_path = plot_monthly_spending_trend(combined_data)
    top_categories_path = plot_top_categories_by_spending(combined_data)

    # Calculate day with maximum transactions
    transactions_by_day = combined_data.groupby("Date")["Transaction ID"].count()
    max_day = transactions_by_day.idxmax()
    max_day_transactions = transactions_by_day.max()

    # Calculate account balances
    balances = calculate_account_balances(combined_data)

    return render_template(
        "dashboard.html",
        total_spending_path=f"/static/total_spending.png",
        category_spending_path=f"/static/category_spending.png",
        transactions_by_day_path=f"/static/transactions_by_day.png",
        pie_chart_path=f"/static/transaction_pie_chart.png",
        transactions_by_category_path=f"/static/transactions_by_category.png",
        spending_by_type_path=f"/static/spending_by_type.png",
        monthly_spending_path=f"/static/monthly_spending.png",
        top_categories_path=f"/static/top_categories.png",
        balances=balances,
        max_day=max_day,
        max_day_transactions=max_day_transactions,
    )


def calculate_account_balances(data):
    # Filter credits and debits
    credits = data[data["Transaction Type"] == "Credit"].groupby("Account Name (Sender)")["Amount"].sum()
    debits = data[data["Transaction Type"] == "Debit"].groupby("Account Name (Sender)")["Amount"].sum()

    # Merge and calculate net balance
    balances = pd.concat([credits, debits], axis=1, keys=["Credits", "Debits"])
    balances["Net Balance"] = balances["Credits"].fillna(0) - balances["Debits"].fillna(0)

    # Format the values to 2 decimal places
    balances = balances.fillna(0).round(2)

    return balances.reset_index().to_dict(orient="records")

@app.route("/account-balances")
def account_balances():
    # Load the previously calculated balances (or recalculate if needed)
    combined_data = pd.read_csv(MERGED_FILE_PATH)
    balances = calculate_account_balances(combined_data)

    return render_template("account_balances.html", balances=balances)

@app.route("/download")
def download_merged_statement():
    """Route to download the merged CSV file."""
    if os.path.exists(MERGED_FILE_PATH):
        return send_file(MERGED_FILE_PATH, as_attachment=True)
    else:
        flash("No merged statement available for download.", "error")
        return render_template("dashboard.html")


def plot_total_spending(data):
    total_spending = data.groupby("Account Name (Sender)")["Amount"].sum()
    path = os.path.join(STATIC_FOLDER, "total_spending.png")
    plt.figure(figsize=(10, 5))
    total_spending.plot(kind="bar", title="Total Spending per Account")
    plt.ylabel("Total Amount")
    plt.tight_layout()
    plt.savefig(path)
    plt.close()
    return path


def plot_category_spending(data):
    category_spending = data.groupby(["Category", "Account Name (Sender)"])["Amount"].sum().unstack()
    path = os.path.join(STATIC_FOLDER, "category_spending.png")
    plt.figure(figsize=(12, 6))
    ax = category_spending.plot(kind="bar", stacked=True, figsize=(12, 6), title="Category Spending per Account")
    plt.ylabel("Total Amount")
    plt.xlabel("Category")
    plt.xticks(rotation=45, ha="right")
    plt.legend(title="Account Name", bbox_to_anchor=(1.05, 1), loc='upper left', fontsize='small')
    plt.tight_layout()
    plt.savefig(path, bbox_inches="tight")
    plt.close()
    return path


def plot_transactions_by_day(data):
    """Plot transactions by day for all sources separately."""
    transactions_by_day = data.groupby([data["Date"].dt.date, "Source"])["Transaction ID"].count().unstack()

    path = os.path.join(STATIC_FOLDER, "transactions_by_day.png")
    plt.figure(figsize=(12, 6))

    for source in transactions_by_day.columns:
        plt.plot(transactions_by_day.index, transactions_by_day[source], label=source)

    plt.title("Transactions by Day (Per Source)")
    plt.xlabel("Date")
    plt.ylabel("Number of Transactions")
    plt.legend(title="Source", bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()

    plt.savefig(path, bbox_inches="tight")
    plt.close()
    return path


# Additional plotting functions
def plot_transaction_pie(data):
    transaction_counts = data["Source"].value_counts()
    path = os.path.join(STATIC_FOLDER, "transaction_pie_chart.png")
    plt.figure(figsize=(8, 8))
    transaction_counts.plot(kind="pie", autopct='%1.1f%%', startangle=90, title="Transaction Distribution by Source")
    plt.ylabel("")
    plt.tight_layout()
    plt.savefig(path)
    plt.close()
    return path


def plot_transactions_by_category(data):
    transactions_by_category = data["Category"].value_counts()
    path = os.path.join(STATIC_FOLDER, "transactions_by_category.png")
    plt.figure(figsize=(10, 5))
    transactions_by_category.plot(kind="bar", color="skyblue", title="Transactions by Category")
    plt.xlabel("Category")
    plt.ylabel("Number of Transactions")
    plt.tight_layout()
    plt.savefig(path)
    plt.close()
    return path


def plot_spending_by_type(data):
    spending_by_type = data.groupby("Transaction Type")["Amount"].sum()
    path = os.path.join(STATIC_FOLDER, "spending_by_type.png")
    plt.figure(figsize=(8, 5))
    spending_by_type.plot(kind="bar", color="orange", title="Spending by Transaction Type")
    plt.xlabel("Transaction Type")
    plt.ylabel("Total Spending")
    plt.tight_layout()
    plt.savefig(path)
    plt.close()
    return path


def plot_monthly_spending_trend(data):
    data['YearMonth'] = data['Date'].dt.to_period('M')
    monthly_spending = data.groupby("YearMonth")["Amount"].sum()
    path = os.path.join(STATIC_FOLDER, "monthly_spending.png")
    plt.figure(figsize=(10, 5))
    monthly_spending.plot(kind="line", title="Monthly Spending Trend", color="blue", marker="o")
    plt.xlabel("Month")
    plt.ylabel("Total Spending")
    plt.tight_layout()
    plt.savefig(path)
    plt.close()
    return path


def plot_top_categories_by_spending(data):
    top_categories = data.groupby("Category")["Amount"].sum().nlargest(5)
    path = os.path.join(STATIC_FOLDER, "top_categories.png")
    plt.figure(figsize=(10, 5))
    top_categories.plot(kind="bar", color="purple", title="Top 5 Categories by Spending")
    plt.xlabel("Category")
    plt.ylabel("Total Spending")
    plt.tight_layout()
    plt.savefig(path)
    plt.close()
    return path


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


if __name__ == "__main__":
    app.run(debug=True)