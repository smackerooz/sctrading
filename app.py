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
SHARIAH_STOCKS = [
    "AAPL", "MSFT", "NVDA", "GOOGL",  # Tech Giants
    "AMZN", "TSLA", "META",           # Consumer/AI
    "LLY", "AMGN", "ADBE",            # Healthcare & Software
    "CRM", "AMD", "INTC",             # Semiconductors/SaaS
    "EOG", "SWKS", "BBY"              # Energy/Retail/Semi
]

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
    try:
        # 1. Fetch data
        data = yf.download(ticker, period="1d", interval="1m", progress=False)
        
        # 2. Check if we have enough data (Need at least 20 minutes)
        if data is None or len(data) < 20:
            return "HOLD"
        
        # 3. Use .iloc[-1] and force it to be a float to avoid "Series" errors
        # We access the 'Close' column and get the last value
        current_close = float(data['Close'].iloc[-1])
        sma_short = float(data['Close'].rolling(window=5).mean().iloc[-1])
        sma_long = float(data['Close'].rolling(window=20).mean().iloc[-1])
        
        # 4. AI Logic
        if sma_short > sma_long:
            return "BUY"
        elif sma_short < sma_long:
            return "SELL"
            
    except Exception as e:
        # If any error happens, just skip this stock and don't crash the app
        return "HOLD"
        
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

# Create a container for the live Signal Tracker
st.write("### 📡 Live Signal Tracker")
signal_table = st.empty() 

col1, col2 = st.columns(2)
with col1:
    st.write("### 📈 Current Positions")
    st.write(st.session_state.portfolio)

with col2:
    st.write("### 📜 Trade Log (CSV Data)")
    if os.path.exists(LOG_FILE):
        st.dataframe(pd.read_csv(LOG_FILE).tail(5))

# 5. LIVE LOOP
status_placeholder = st.empty()

while True:
    current_signals = [] # List to store data for the tracker table
    
    with status_placeholder.container():
        with st.status("🚀 AI Engine Active...", expanded=True) as status:
            for stock in SHARIAH_STOCKS:
                st.write(f"Analyzing {stock}...")
                
                # Modified ai_engine to return values for the table
                data = yf.download(stock, period="1d", interval="1m", progress=False)
                if not data.empty and len(data) >= 20:
                    s_ma = float(data['Close'].rolling(window=5).mean().iloc[-1])
                    l_ma = float(data['Close'].rolling(window=20).mean().iloc[-1])
                    diff = s_ma - l_ma
                    trend = "🟢 Bullish" if diff > 0 else "🔴 Bearish"
                    
                    current_signals.append({
                        "Ticker": stock, 
                        "5-min SMA": round(s_ma, 2), 
                        "20-min SMA": round(l_ma, 2), 
                        "Trend": trend
                    })
                    
                    # Logic to trigger trades
                    if s_ma > l_ma: execute_trade(stock, "BUY")
                    elif s_ma < l_ma: execute_trade(stock, "SELL")

            status.update(label="✅ Scan Complete. Resting...", state="complete", expanded=False)

    # Update the Signal Tracker table in the UI
    signal_table.table(pd.DataFrame(current_signals))
    
    time.sleep(60)
    st.rerun()
