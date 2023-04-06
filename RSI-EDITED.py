import MetaTrader5 as mt5
from config import *
import pandas as pd
import numpy as np
import rsi_oco
import time
import os
import ta

############################################################################################

# AUTHORIZE
def authorize():
    if not mt5.initialize(login=account, password = password, server = server):
        print("Initialize() failed, error code =", mt5.last_error())
        quit()
    authorized = mt5.login(account, password = password, server = server)

    if authorized:
        print("\n - STATUS = [SUCCESS] > [Connected to MT5 Client]")
        check_symbol_activity()
    else:
        print(f"\n - STATUS = [FAILED] > Failed to connect at account #{account}.\nError code: {mt5.last_error()}")

# CHECK IF SYMBOL IS VISIBLE
def check_symbol_activity():
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        print(symbol, "symbol not found")
            

    if not symbol_info.visible:
        print(symbol, "is not visible, trying to switch on")
        if not mt5.symbol_select(symbol, True):
            print(f"symbol_select({symbol}) failed, please find it manually, exiting...")
            mt5.shutdown()
    else:
        print(symbol, "symbol found!")

############################################################################################

# Trading Logic
def logic(rsi):

    print(f"Current RSI: {rsi}")

    # if RSI less then 30 -> BUY
    if rsi < oversold_level:
        print("STATUS: Waiting for Stochastic Oscillator BUY signal...")
        SO_value, SO_signal = stochastic_oscillator()
        print(f"SO Signal: {SO_signal}\nSO Value: {SO_value:.3f}")
        if SO_signal == 'BUY':
            print("RSI signal: BUY")
            print(f"Stochastic signal: {SO_signal}\nStochastic value: {SO_value}")
            # set order type
            order_type = 'BUY'
            
            point = mt5.symbol_info(symbol).point
            price = mt5.symbol_info_tick(symbol).ask
            stop_loss = price - stop_loss_pips * point
                
            rsi_oco.open_position(symbol, order_type, lot_size, stop_loss)

            

    # if RSI greater than 70 -> SELL
    elif rsi > overbought_level:
        print("STATUS: Waiting for Stochastic Oscillator SELL signal...")
        SO_value, SO_signal = stochastic_oscillator()
        print(f"SO Signal: {SO_signal}\nSO Value: {SO_value:.3f}")
        if SO_signal == 'SELL':
            print("RSI signal: SELL")
            print(f"Stochastic signal: {SO_signal}\nStochastic value: {SO_value}")
            # set order type
            order_type = 'SELL'

            if opened_positions < max_open_positions:
                point = mt5.symbol_info(symbol).point
                price = mt5.symbol_info_tick(symbol).bid
                stop_loss = price + stop_loss_pips * point
                
                rsi_oco.open_position(symbol, order_type, lot_size, stop_loss)
            
            else:
                print(f"Max positions reached!")
                


    else:
        print("RSI signal: IDLE")



# Calculate RSI
def calculate_rsi():
    rates = mt5.copy_rates_from_pos(symbol, timeframe, start_bar, num_bars)
    df = pd.DataFrame(rates)
    df['change'] = df['close'].diff()
    df['gain'] = np.where(df['change'] > 0, df['change'], 0)
    df['loss'] = np.where(df['change'] < 0, abs(df['change']), 0)
    ewm_gain = df['gain'].ewm(span=rsi_period).mean()
    ewm_loss = df['loss'].ewm(span=rsi_period).mean()
    relative_strength = ewm_gain / ewm_loss
    rsi = 100 - (100 / (1 + relative_strength))

    return rsi.iloc[-1]

# Calculate Stochasti Oscillator
def stochastic_oscillator():
    bars = mt5.copy_rates_from_pos(symbol, timeframe, start_bar, num_bars)
    df = pd.DataFrame(bars)
    close = df['close']
    high = df['high']
    low = df['low']
    n = 14
    dd = 3

    # Calculate %K
    k = []
    for i in range(n-1, len(close)):
        c = close[i]
        h = max(high[i-n+1:i+1])
        l = min(low[i-n+1:i+1])
        k.append((c - l) / (h - l))
        
    # Calculate %D
    d = []
    for i in range(dd-1, len(k)):
        d.append(sum(k[i-dd+1:i+1]) / dd)
        
    # Get the most recent %K and %D values
    k = k[-1]
    d = d[-1]
    
    # Determine the signal
    if k > d:
        if k - d < 0.08:
            return k - d, "BUY"
        else:
            return k - d, "NEUTRAL"
    elif k < d:
        if k - d > -0.08:
            return k - d, "SELL"
        else:
            return k - d, "NEUTRAL"
    else:
        return k - d, "NEUTRAL"
    
# Trailing Logic
def check_trailing_profit():
    # Get opened positions
    op_pos = mt5.positions_get()
    df = pd.DataFrame(list(op_pos), columns=op_pos[0]._asdict().keys())
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.drop(['time', 'time_update', 'time_msc', 'time_update_msc', 'external_id', 'reason', 'magic', 'identifier'], axis=1, inplace=True)
    print(df)

    # Price when position was opened
    price_open = df['price_open'][0]

    # Points
    pt = mt5.symbol_info(symbol).point

    # BID and ASK prices
    curr_price_ask = mt5.symbol_info_tick(symbol).ask
    curr_price_bid = mt5.symbol_info_tick(symbol).bid

    # Stop Loss definitions
    new_sl_for_buy = curr_price_ask - stop_loss_pips * pt
    new_sl_for_sell = curr_price_bid + stop_loss_pips * pt

    # Position type: 0 = BUY , 1 = SELL
    position_type = df['type'][0]

    # Current sl, profit, and Ticket ID
    curr_sl = float(df['sl'][0])
    curr_profit = df['profit'][0] # Float
    ticket_id = int(df['ticket'][0])   # Int
    

    # Check current profit
    if curr_profit > trailing_profit_trigger:
        if position_type == 0:
            print("Opened position is BUY")
            if new_sl_for_buy > curr_sl:
                rsi_oco.modify_position(symbol, ticket_id, new_sl_for_buy)

            # else:
            #     if curr_price_ask > price_open:
            #         rsi_oco.modify_position(symbol, ticket_id, new_sl_for_buy - (stop_loss_pips / 2))

        else:
            print("Opened position is SELL")
            if new_sl_for_sell < curr_sl:
                rsi_oco.modify_position(symbol, ticket_id, new_sl_for_sell)
#TODO: Popraviti trailing, kad je pocetak trejda i kad prvi put pomakne
#      stop loss kad je u profitu 1 dolar, treba napraviti da ako krene padat, da vrati na pocetni stop loss
#      cisto zbog malo fleksibilnosti, jer ovako ode malo u profit -> modificira stop loss -> krene padat ->
#      brzo se triggera stop loss jer je pomaknut. Znaci moramo imat neki maximum koji zelimo riskirat.


#TODO: Mozda ubaciti moving average (imas gotov code u chatGPTu)

authorize() # Authorize MT5


# Main Loop
while True:
    rsi = calculate_rsi()
    print("Stochastic:", stochastic_oscillator())

    # Number of opened positions
    opened_positions = mt5.positions_total()
    print(f"Current opened positions: {opened_positions}")

    if opened_positions < max_open_positions:
        logic(rsi)
        
    else:
        check_trailing_profit()


    if opened_positions != 0:
        positions = mt5.positions_get(symbol = symbol)
        for pos in range(0, opened_positions):
            try:
                df = pd.DataFrame(list(positions), columns=positions[pos]._asdict().keys())
                print(f"\n#{pos + 1}\nTicket ID: {df['ticket'][pos]}\nSymbol: {df['symbol'][pos]}\nProfit: {mt5.account_info()._asdict()['currency']} {df['profit'][pos]:.2f}\n")
            except:
                print("error...")
        try:
            print(f"Positions profit: {mt5.account_info()._asdict()['currency']} {df['profit'].sum():.2f}\nProfits including all fees: {mt5.account_info()._asdict()['currency']} {mt5.account_info()._asdict()['profit']:.2f}")
        except:
                print("error...")

    time.sleep(0.01)
    os.system('cls')