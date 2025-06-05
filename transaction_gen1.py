import csv
import random
from datetime import datetime, timedelta

# List of sample Indian names
indian_names = [
    "Arjun", "Ananya", "Kabir", "Aarav", "Ishita", "Diya", "Neha", "Rohan", "Priya", "Vikram",
    "Sneha", "Akash", "Meera", "Siddharth", "Pooja", "Karthik", "Lakshmi", "Rajesh", "Aditi", "Nikhil"
]

# List of sample Indian company names
indian_companies = [
    "Reliance Industries", "Tata Consultancy Services", "Infosys", "HDFC Bank",
    "ICICI Bank", "Wipro", "Bharti Airtel", "Adani Enterprises", "Maruti Suzuki", "State Bank of India",
    "Larsen & Toubro", "Hindustan Unilever", "Bajaj Finserv", "Mahindra & Mahindra", "Axis Bank"
]

def generate_banking_transactions():
    # Take input for the number of months
    months = int(input("Enter the number of months for which to generate transactions: "))

    # Define possible categories and transaction types
    categories = ['Education', 'Entertainment', 'Food', 'Transport', 'Shopping', 'Healthcare', 'Utilities', 'Miscellaneous']
    transaction_types = ['Credit', 'Debit']

    # Calculate date range
    start_date = datetime.now() - timedelta(days=months * 30)
    end_date = datetime.now()

    transactions = []

    current_date = start_date
    while current_date <= end_date:
        # Generate a random number of transactions for the day
        daily_transactions = random.randint(1, 10)
        for _ in range(daily_transactions):
            # Randomly decide if the transaction involves a person or a company
            sender = random.choice(indian_names + indian_companies)
            receiver = random.choice(indian_names + indian_companies)
            transaction = {
                "Date": current_date.strftime("%Y-%m-%d"),
                "Time": current_date.strftime("%H:%M:%S"),
                "Transaction ID": f"T{random.randint(1000000, 9999999)}",
                "Account Number (Sender)": f"AC{random.randint(10000000, 99999999)}",
                "Account Name (Sender)": sender,
                "Account Number (Receiver)": f"AC{random.randint(10000000, 99999999)}",
                "Account Name (Receiver)": receiver,
                "Category": random.choice(categories),
                "Amount": round(random.uniform(100, 10000), 2),
                "Transaction Type": random.choice(transaction_types),
                "Description": "Auto-generated transaction details"
            }
            transactions.append(transaction)

        # Move to the next day
        current_date += timedelta(days=1)

    # Specify output file name
    output_file = "banking_transactions.csv"

    # Write transactions to a CSV file
    with open(output_file, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=transactions[0].keys())
        writer.writeheader()
        writer.writerows(transactions)

    print(f"Dummy transactions saved to '{output_file}'.")

# Run the function
generate_banking_transactions()