import streamlit as st
import pandas as pd
import yfinance as yf
import time
from datetime import datetime
import pytz  # For Singapore Timezone
import os

# 1. SETUP & CONFIGURATION
INITIAL_BALANCE_SGD = 10000.0
USD_SGD_RATE = 1.35  
TRADE_LIMIT_USD = 100.0
CASH_BUFFER_SGD = 5000.0  # Protecting 50% of your capital
LOG_FILE = "trading_log.csv"
SGT = pytz.timezone('Asia/Singapore')

# The "Super 75" Shariah List
SHARIAH_STOCKS = [
    "AAPL", "MSFT", "NVDA", "GOOGL", "AVGO", "ASML", "AMD", "INTC", "ADBE", "CRM", 
    "TXN", "QCOM", "AMAT", "LRCX", "MU", "ADI", "KLAC", "SNOW", "PLTR", "PANW", 
    "FTNT", "ZS", "DDOG", "NET", "OKTA", "MDB", "TEAM", "WDAY", "NOW", "SHOP",
    "LLY", "JNJ", "AMGN", "VRTX", "REGN", "MRNA", "ISRG", "GILD", "TMO", "DHR", 
    "IDXX", "A", "BIIB", "BSX", "ZTS", "EW", "ALGN", "DXCM", "MTD", "RMD",
    "EOG", "SLB", "COP", "HAL", "HES", "XOM", "CVX", "UPS", "FDX", "CAT", 
    "DE", "HON", "LMT", "GD", "NOC", "TSLA", "LOW", "TJX", "COST", "AZO", 
    "ORLY", "NKE", "SBUX", "CMG", "EL"
]

# Initialize Session State
if 'balance' not in st.session_state:
    st.session_state.balance = INITIAL_BALANCE_SGD
    st.session_state.portfolio = {ticker: 0.0 for ticker in SHARIAH_STOCKS}
    st.session_state.entry_prices = {ticker: 0.0 for ticker in SHARIAH_STOCKS}
    if not os.path.exists(LOG_FILE):
        df = pd.DataFrame(columns=["Timestamp_SGT", "Stock", "Action", "Quantity", "Price_USD", "Balance_SGD"])
        df.to_csv(LOG_FILE, index=False)

# 2. EXECUTION LOGIC
def execute_trade(ticker, action, price_usd):
    price_sgd = price_usd * USD_SGD_RATE
    
    if action == "BUY":
        qty = TRADE_LIMIT_USD / price_usd
        st.session_state.balance -= (qty * price_sgd)
        st.session_state.portfolio[ticker] += qty
        st.session_state.entry_prices[ticker] = price_usd
        log_trade(ticker, "BUY", qty, price_usd)
        
    elif action == "SELL":
        qty = st.session_state.portfolio[ticker]
        st.session_state.balance += (qty * price_sgd)
        st.session_state.portfolio[ticker] = 0.0
        st.session_state.entry_prices[ticker] = 0.0
        log_trade(ticker, "SELL", qty, price_usd)

def log_trade(ticker, action, qty, price):
    now_sgt = datetime.now(SGT).strftime('%Y-%m-%d %H:%M:%S')
    new_entry = pd.DataFrame([[now_sgt, ticker, action, qty, price, st.session_state.balance]], 
                             columns=["Timestamp_SGT", "Stock", "Action", "Quantity", "Price_USD", "Balance_SGD"])
    new_entry.to_csv(LOG_FILE, mode='a', header=False, index=False)

# 3. DASHBOARD UI
st.set_page_config(page_title="AI Shariah Trader", layout="wide")
st.title("🌙 Shariah-Compliant AI Scalper (by Rooz)")

# Top Stats
c1, c2, c3 = st.columns(3)
c1.metric("Account Balance", f"${st.session_state.balance:,.2f} SGD")
active_trades = sum(1 for v in st.session_state.portfolio.values() if v > 0)
c2.metric("Active Positions", active_trades)
c3.write(f"🕒 **Current SGT:** {datetime.now(SGT).strftime('%H:%M:%S')}")

st.write("---")

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("📈 Current Holdings")
    holdings_data = [] # Fix for NameError
    for ticker, qty in st.session_state.portfolio.items():
        if qty > 0:
            entry = st.session_state.entry_prices.get(ticker, 0)
            holdings_data.append({"Stock": ticker, "Qty": round(qty, 4), "Entry ($)": entry})
    
    if holdings_data:
        st.table(pd.DataFrame(holdings_data))
    else:
        st.info("No active trades. Scanning for signals...")

with col_right:
    st.subheader("📜 Recent Logs (SGT)")
    if os.path.exists(LOG_FILE):
        try:
            # Memory fix: only read last 30 entries
            log_df = pd.read_csv(LOG_FILE).tail(30)
            st.dataframe(log_df.iloc[::-1], use_container_width=True)
        except:
            st.error("Log temporarily unavailable.")

st.write("---")
st.subheader("📡 Live Signal Tracker")
signal_table = st.empty()

# 4. LIVE TRADING LOOP
status_placeholder = st.empty()

while True:
    current_signals = []
    with status_placeholder.container():
        with st.status(f"🚀 Scanning 75 Stocks... (SGT: {datetime.now(SGT).strftime('%H:%M:%S')})", expanded=True) as status:
            for stock in SHARIAH_STOCKS:
                try:
                    data = yf.download(stock, period="1d", interval="1m", progress=False)
                    if isinstance(data.columns, pd.MultiIndex):
                        data.columns = data.columns.get_level_values(0)

                    if not data.empty and len(data) >= 20:
                        curr_p = float(data['Close'].iloc[-1])
                        s_ma = float(data['Close'].rolling(window=5).mean().iloc[-1])
                        l_ma = float(data['Close'].rolling(window=20).mean().iloc[-1])
                        
                        trend = "🟢 Bullish" if s_ma > l_ma else "🔴 Bearish"
                        current_signals.append({"Ticker": stock, "Price": round(curr_p, 2), "Trend": trend})

                        # --- LOGIC ---
                        # SELL if 2% Profit OR Trend Flip
                        if st.session_state.portfolio[stock] > 0:
                            entry_p = st.session_state.entry_prices[stock]
                            profit_pct = (curr_p - entry_p) / entry_p
                            
                            if profit_pct >= 0.02:
                                execute_trade(stock, "SELL", curr_p)
                                st.toast(f"💰 PROFIT: {stock} at +2%!", icon="✅")
                            elif s_ma < l_ma:
                                execute_trade(stock, "SELL", curr_p)
                                st.toast(f"📉 Trend Exit: {stock}", icon="⚠️")

                        # BUY if Bullish + above Cash Buffer
                        elif s_ma > l_ma and st.session_state.balance > CASH_BUFFER_SGD:
                            if st.session_state.portfolio[stock] == 0:
                                execute_trade(stock, "BUY", curr_p)
                                st.toast(f"🚀 Buying {stock}", icon="📈")
                except:
                    continue
            status.update(label="✅ Scan Complete.", state="complete", expanded=False)

    if current_signals:
        signal_table.dataframe(pd.DataFrame(current_signals), height=300, use_container_width=True)
    
    time.sleep(10)
    st.rerun()
