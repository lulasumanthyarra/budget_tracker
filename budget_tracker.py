# Budget Tracker with Clean Emoji Dropdown Sorting and Custom Input

import sqlite3
import pandas as pd
from datetime import datetime
import streamlit as st
import plotly.express as px
import os

# Ensure the folder exists before connecting to the database
folder = "C:/Users/lulas/Google Drive/budget_tracker"
os.makedirs(folder, exist_ok=True)

# Define the database path inside the cloud-synced folder
db_path = os.path.join(folder, "budget_tracker.db")
conn = sqlite3.connect(db_path, check_same_thread=False)
c = conn.cursor()

# Create the table if it doesn't exist
c.execute('''
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    type TEXT,
    category TEXT,
    description TEXT,
    amount REAL,
    deleted INTEGER DEFAULT 0
)
''')
conn.commit()

# Add initial savings if not already present
c.execute("SELECT COUNT(*) FROM transactions WHERE description = 'Carried forward savings before current month'")
if c.fetchone()[0] == 0:
    c.execute('''
        INSERT INTO transactions (date, type, category, description, amount)
        VALUES (?, ?, ?, ?, ?)
    ''', ('2025-04-30', 'Income', 'Previous Savings', 'Carried forward savings before current month', 5000.00))

# Add month-to-date savings if not already present
c.execute("SELECT COUNT(*) FROM transactions WHERE description = 'Savings accumulated this month to date'")
if c.fetchone()[0] == 0:
    c.execute('''
        INSERT INTO transactions (date, type, category, description, amount)
        VALUES (?, ?, ?, ?, ?)
    ''', ('2025-05-01', 'Income', 'Month-to-date Savings', 'Savings accumulated this month to date', 1243.70))

conn.commit()

# Function to add entry
def add_transaction(date, trans_type, category, description, amount):
    c.execute('INSERT INTO transactions (date, type, category, description, amount) VALUES (?, ?, ?, ?, ?)',
              (date, trans_type, category, description, amount))
    conn.commit()

# Function to delete entry by ID
def delete_transaction(transaction_id):
    c.execute('DELETE FROM transactions WHERE id = ?', (transaction_id,))
    conn.commit()

# Function to get monthly summary
def get_monthly_summary(month=None):
    df = pd.read_sql_query("SELECT * FROM transactions", conn)
    df['date'] = pd.to_datetime(df['date'])
    if month:
        df = df[df['date'].dt.strftime('%Y-%m') == month]
    total_income = df[df['type'] == 'Income']['amount'].sum()
    total_expense = df[df['type'] == 'Expense']['amount'].sum()
    summary = df[df['type'] == 'Expense'].groupby('category')['amount'].sum().reset_index()
    return total_income, total_expense, summary, df

# Sorted category tuples (label, value)
income_tuples = sorted([
    ("💼 Bonus", "Bonus"),
    ("🎁 Gift", "Gift"),
    ("💻 Freelance", "Freelance"),
    ("📈 Investment Return", "Investment Return"),
    ("💰 Salary", "Salary"),
    ("📅 Daily earnings", "Daily earnings")
], key=lambda x: x[1])
income_labels = [x[0] for x in income_tuples] + ["➕ Other"]
income_lookup = {x[0]: x[1] for x in income_tuples}

expense_tuples = sorted([
    ("🛠️ Car Maintenance/Repairs", "Car Maintenance/Repairs"),
    ("🎮 Entertainment", "Entertainment"),
    ("⛽ Gas", "Gas"),
    ("🛒 Groceries", "Groceries"),
    ("🏥 Health", "Health"),
    ("🏠 Rent", "Rent"),
    ("🍽️ Restaurant", "Restaurant"),
    ("🛍️ Shopping", "Shopping"),
    ("📺 Subscriptions", "Subscriptions"),
    ("🚌 Transport", "Transport"),
    ("💡 Utilities", "Utilities")
], key=lambda x: x[1])
expense_labels = [x[0] for x in expense_tuples] + ["➖ Other"]
expense_lookup = {x[0]: x[1] for x in expense_tuples}

# Streamlit UI
st.set_page_config(page_title="💸 Budget Tracker", layout="wide")
st.title("💸 Daily Budget Tracker")
st.markdown("Keep track of your daily income and expenses with visual reports.")

with st.sidebar:
    st.header("➕ Add Transaction")
    date = st.date_input("📅 Date of Transaction", datetime.today())
    trans_type = st.selectbox("🔁 Transaction Type", ["Select an option", "Income", "Expense"])

    category = ""
    if trans_type == "Income":
        selected_label = st.selectbox("🏷️ Category", income_labels)
        if selected_label == "➕ Other":
            category = st.text_input("Enter Custom Income Category")
        else:
            category = income_lookup.get(selected_label, "")
    elif trans_type == "Expense":
        selected_label = st.selectbox("🏷️ Category", expense_labels)
        if selected_label == "➖ Other":
            category = st.text_input("Enter Custom Expense Category")
        else:
            category = expense_lookup.get(selected_label, "")

    description = st.text_input("📝 Description", placeholder="e.g., Walmart shopping or Salary for May")
    amount = st.number_input("💵 Amount (USD)", min_value=0.01, step=0.01, placeholder="Enter amount in dollars")
    if st.button("Add Transaction"):
        if trans_type != "Select an option" and category.strip() and description.strip() and amount > 0:
            add_transaction(date.strftime('%Y-%m-%d'), trans_type, category.strip(), description.strip(), amount)
            st.success("✅ Transaction added!")
        else:
            st.error("All fields are required, and amount must be greater than 0.")

    # 🔙 Delete Transactions
    st.header("🗑️ Delete Transaction")
    delete_df = pd.read_sql_query("SELECT id, date, type, category, description, amount FROM transactions ORDER BY date DESC", conn)
    if not delete_df.empty:
        delete_df['label'] = delete_df.apply(lambda row: f"{row['date']} - {row['type']} - {row['category']} - ${row['amount']:.2f} ({row['description']})", axis=1)
        selected_type = st.selectbox("Select Transaction Type", ["Select an option"] + sorted(delete_df['type'].unique()))
        if selected_type != "Select an option":
            filtered_by_type = delete_df[delete_df['type'] == selected_type]
            selected_category = st.selectbox("Select Category", ["Select an option"] + sorted(filtered_by_type['category'].unique()))
            if selected_category != "Select an option":
                final_df = filtered_by_type[filtered_by_type['category'] == selected_category]
                final_df['label'] = final_df.apply(lambda row: f"{row['date']} - ${row['amount']:.2f} ({row['description']})", axis=1)
                delete_selection = st.selectbox("Select Transaction to Delete", final_df['label'].tolist())
                selected_id = final_df[final_df['label'] == delete_selection]['id'].values[0]
                if st.button("Confirm Delete"):
                    delete_transaction(int(selected_id))
                    st.success("Transaction deleted successfully.")

    # 🔄 Reset Transactions
    st.header("♻️ Reset Transactions by Date")
    reset_date = st.date_input("Select a date to reset (delete all transactions)", datetime.today())
    if st.button("Reset All for Selected Date"):
        c.execute("DELETE FROM transactions WHERE date = ?", (reset_date.strftime('%Y-%m-%d'),))
        conn.commit()
        st.success(f"All transactions on {reset_date.strftime('%Y-%m-%d')} deleted.")

# 💰 Display Persistent Savings
st.markdown("---")
st.subheader("💰 Savings")

monthly = datetime.today().strftime('%Y-%m')
income_all, expense_all, _, _ = get_monthly_summary()
income, expense, category_summary, filtered_df = get_monthly_summary(monthly)
if not filtered_df.empty:
    total_income = filtered_df[filtered_df['type'] == 'Income']['amount'].sum()
    total_expense = filtered_df[filtered_df['type'] == 'Expense']['amount'].sum()
    savings = total_income - total_expense
    st.metric(label="Current Savings", value=f"${income_all - expense_all:,.2f}")

    # 📅 Daily Report
    current_month = datetime.today().strftime('%Y-%m')
    filtered_df = filtered_df[filtered_df['date'].dt.strftime('%Y-%m') == current_month]

    daily_summary = filtered_df.groupby(filtered_df['date'].dt.strftime('%Y-%m-%d (%a)')).agg({
        'amount': [
            lambda x: x[filtered_df.loc[x.index, 'type'] == 'Income'].sum(),
            lambda x: x[filtered_df.loc[x.index, 'type'] == 'Expense'].sum()
        ]
    })
    daily_summary.columns = ['Income', 'Expense']
    daily_summary['Balance'] = daily_summary['Income'] - daily_summary['Expense']
    daily_summary = daily_summary.reset_index()
    daily_summary.columns = ["Date", "Income", "Expense", "Balance"]
    daily_summary = daily_summary[(daily_summary['Income'] > 0) | (daily_summary['Expense'] > 0)]

    st.markdown("### 💵 Summary for the Month")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Income", f"${income:.2f}")
    col2.metric("Total Expenses", f"${expense:.2f}")
    col3.metric("Balance", f"${income - expense:.2f}")

    st.markdown("### 🧾 Daily Breakdown")
    st.dataframe(daily_summary.sort_values(by='Date', ascending=False), use_container_width=True)

    # 📆 Weekly Report
    st.markdown("### 📆 Weekly Report")
    filtered_df['week'] = pd.to_datetime(filtered_df['date']).dt.to_period('W').apply(
        lambda r: f"{r.start_time.strftime('%Y-%m-%d (%a)')} - {r.end_time.strftime('%Y-%m-%d (%a)')}")
    weekly_summary = filtered_df.groupby('week').apply(
        lambda x: pd.Series({
            'Income': x[x['type'] == 'Income']['amount'].sum(),
            'Expense': x[x['type'] == 'Expense']['amount'].sum(),
            'Balance': x[x['type'] == 'Income']['amount'].sum() - x[x['type'] == 'Expense']['amount'].sum()
        })
    ).reset_index()
    weekly_summary.columns = ['Week', 'Income', 'Expense', 'Balance']
    weekly_summary = weekly_summary[(weekly_summary['Income'] > 0) | (weekly_summary['Expense'] > 0)]
    st.dataframe(weekly_summary.sort_values(by='Week', ascending=False), use_container_width=True)

    # 📊 Daily Income and Expense Chart
    st.markdown("### 📊 Daily Income and Expense Chart")
    fig = px.bar(
        daily_summary,
        x='Date',
        y=['Income', 'Expense'],
        barmode='group',
        title='Daily Income and Expenses',
        labels={'value': 'Amount (USD)', 'variable': 'Transaction Type'},
        height=400
    )
    fig.update_traces(marker_line_width=0.5, width=0.2)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No transaction data available for this month.")
