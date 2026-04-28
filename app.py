import streamlit as st
import pandas as pd
import yfinance as yf
import time
from datetime import datetime
import os

# 1. SETUP & CONFIGURATION
INITIAL_BALANCE_SGD = 10000.0
USD_SGD_RATE = 1.35  # Approximate rate for simulation
TRADE_LIMIT_USD = 100.0
LOG_FILE = "trading_log.csv"

# Shariah-Compliant US Stock List (Sample for simulation)
SHARIAH_STOCKS = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "TSLA", "ADBE", "CRM"]

# Initialize Session State for persistence
if 'balance' not in st.session_state:
    st.session_state.balance = INITIAL_BALANCE_SGD
    st.session_state.portfolio = {ticker: 0 for ticker in SHARIAH_STOCKS}
    # Create log file if not exists
    if not os.path.exists(LOG_FILE):
        df = pd.DataFrame(columns=["Timestamp", "Stock", "Action", "Quantity", "Price_USD", "Balance_SGD"])
        df.to_csv(LOG_FILE, index=False)

# 2. AI TRADING ALGORITHM (Simple Moving Average Crossover)
def ai_decision_engine(ticker):
    # Fetch 1-minute interval data
    data = yf.download(ticker, period="1d", interval="1m", progress=False)
    
    # Safety Check: Ensure we have at least 20 rows of data to calculate the SMA
    if len(data) < 20: 
        return "HOLD"
    
    # Calculate Moving Averages
    sma_short = data['Close'].rolling(window=5).mean().iloc[-1]
    sma_long = data['Close'].rolling(window=20).mean().iloc[-1]
    
    # Final Safety Check: Ensure the calculation resulted in actual numbers
    import pandas as pd
    if pd.isna(sma_short) or pd.isna(sma_long):
        return "HOLD"
    
    # The AI Logic (SMA Crossover)
    if sma_short > sma_long:
        return "BUY"
    elif sma_short < sma_long:
        return "SELL"
        
    return "HOLD"
# 3. EXECUTION LOGIC
def execute_trade(ticker, action):
    price_usd = yf.Ticker(ticker).fast_info['last_price']
    price_sgd = price_usd * USD_SGD_RATE
    
    if action == "BUY" and st.session_state.balance >= (TRADE_LIMIT_USD * USD_SGD_RATE):
        qty = TRADE_LIMIT_USD / price_usd
        st.session_state.balance -= (qty * price_sgd)
        st.session_state.portfolio[ticker] += qty
        log_trade(ticker, "BUY", qty, price_usd)
        
    elif action == "SELL" and st.session_state.portfolio[ticker] > 0:
        qty = st.session_state.portfolio[ticker]
        st.session_state.balance += (qty * price_sgd)
        st.session_state.portfolio[ticker] = 0
        log_trade(ticker, "SELL", qty, price_usd)

def log_trade(ticker, action, qty, price):
    new_entry = pd.DataFrame([[datetime.now(), ticker, action, qty, price, st.session_state.balance]], 
                             columns=["Timestamp", "Stock", "Action", "Quantity", "Price_USD", "Balance_SGD"])
    new_entry.to_csv(LOG_FILE, mode='a', header=False, index=False)

# 4. DASHBOARD UI
st.title("🌙 Shariah-Compliant AI Trader")
st.subheader(f"Account Balance: ${st.session_state.balance:,.2f} SGD")

col1, col2 = st.columns(2)
with col1:
    st.write("### Current Positions")
    st.write(st.session_state.portfolio)

with col2:
    st.write("### Recent Activity")
    if os.path.exists(LOG_FILE):
        st.dataframe(pd.read_csv(LOG_FILE).tail(5))

# 5. LIVE LOOP (Simulated 1-minute update)
st.info("The simulation updates every 60 seconds. Keep this tab open.")
while True:
    for stock in SHARIAH_STOCKS:
        decision = ai_decision_engine(stock)
        if decision != "HOLD":
            execute_trade(stock, decision)
    
    time.sleep(60)
    st.rerun()
