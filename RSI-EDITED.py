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
    global initial_sl

    print(f"Current RSI: {rsi}")

    # if RSI less then 30 -> BUY
    if rsi < oversold_level:
        print("STATUS: Waiting for Stochastic Oscillator BUY signal...")
        SO_k, SO_d, SO_signal = stochastic_oscillator()
        if SO_signal == 'BUY':
            print("RSI signal: BUY")
            print(f"Stochastic_K: {SO_k}\nStochastic_D: {SO_d}")
            # set order type
            order_type = 'BUY'
            
            point = mt5.symbol_info(symbol).point
            price = mt5.symbol_info_tick(symbol).ask
            stop_loss = price - stop_loss_pips * point

            initial_sl = stop_loss
                
            rsi_oco.open_position(symbol, order_type, lot_size, stop_loss)

            

    # if RSI greater than 70 -> SELL
    elif rsi > overbought_level:
        print("STATUS: Waiting for Stochastic Oscillator SELL signal...")
        SO_k, SO_d, SO_signal = stochastic_oscillator()
        if SO_signal == 'SELL':
            print("RSI signal: SELL")
            print(f"Stochastic_K: {SO_k}\nStochastic_D: {SO_d}")
            # set order type
            order_type = 'SELL'


            point = mt5.symbol_info(symbol).point
            price = mt5.symbol_info_tick(symbol).bid
            stop_loss = price + stop_loss_pips * point

            initial_sl = stop_loss
            
            rsi_oco.open_position(symbol, order_type, lot_size, stop_loss)



    else:
        print("RSI signal: IDLE")


# bollinger bands indicator
def bollinger_bands():
    """
    Function to calculate the Bollinger Bands for a given dataframe and a specified number of periods and standard deviations.

    Parameters:
    data (DataFrame): Historical data
    n (int): Number of periods to calculate the Moving Average
    std (int): Number of standard deviations to calculate the Upper and Lower Bands

    Returns:
    upper_band (Series): Upper Bollinger Band of the specified number of periods and standard deviations
    lower_band (Series): Lower Bollinger Band of the specified number of periods and standard deviations
    """
    datacopy = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, start_bar, 21)
    data = pd.DataFrame(datacopy)
    std = 2
    n = 20
    ma = data['close'].rolling(n).mean()
    std_dev = data['close'].rolling(n).std()
    upper_band = ma + std_dev * std
    lower_band = ma - std_dev * std
    return upper_band, lower_band



'''
Your acceptable profit or loss per trade will depend on the time frame that 
you are using. With 1 minute scalping, 
you would probably be looking for a profit of around 5 pips per trade, 
whereas a 5-minute scalp could probably provide you with a realistic target of 10 pips per trade. 
'''


# Breakout strategy
def breakout_strategy(data, n, std):
    """
    Function to implement the Breakout Strategy for a given dataframe and a specified number of periods and standard deviations.

    Parameters:
    data (DataFrame): Historical data
    n (int): Number of periods to calculate the Moving Average and Bollinger Bands
    std (int): Number of standard deviations to calculate the Upper and Lower Bands

    Returns:
    signal (str): Signal for the Breakout Strategy, either BUY, SELL, or NEUTRAL
    """
    upper_band, lower_band = bollinger_bands(data, n, std)
    last_close = data['close'].iloc[-1]
    last_upper = upper_band.iloc[-1]
    last_lower = lower_band.iloc[-1]
    if last_close > last_upper:
        signal = 'BUY'
    elif last_close < last_lower:
        signal = 'SELL'
    else:
        signal = 'NEUTRAL'
    return signal

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
    bars = mt5.copy_rates_from_pos(symbol, timeframe, 0, 10)
    df = pd.DataFrame(bars)
    n = 5   # Number of periods to use for %K calculation
    d = 3   # Number of periods to use for %D calculation
    s = 3   # Slowing parameter
    overb = 90
    overs = 10
    
    
    # Calculate %K
    low_min = df['low'].rolling(n).min()
    high_max = df['high'].rolling(n).max()
    fast_k = (df['close'] - low_min) / (high_max - low_min) * 100
    slow_k = fast_k.rolling(s).mean()
    df['%K'] = slow_k

    # Calculate %D
    df['%D'] = df['%K'].rolling(d).mean()

    # Get current %K and %D levels
    k = df['%K'].iloc[-1]
    d = df['%D'].iloc[-1]
    
    # Determine the signal
    if k > overb and d > overb - 10: # and k > d
        return k, d, "SELL"

    elif k < overs and d < overs + 10:
        return k, d, "BUY"

    else:
        return k, d, "NEUTRAL"
    
# Trailing Logic
def check_trailing_profit():
    try:
        # Get opened positions
        op_pos = mt5.positions_get()
        df = pd.DataFrame(list(op_pos), columns=op_pos[0]._asdict().keys())
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.drop(['time', 'time_update', 'time_msc', 'time_update_msc', 'external_id', 'reason', 'magic', 'identifier'], axis=1, inplace=True)
        print(df)
    except:
        print("Error trailing, can't get position.")

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
    

    # Check current profit  # TREBA TESTIRAT ILI REVERT BACK
    if curr_profit > trailing_profit_trigger:
        if position_type == 0:
            print("Opened position is BUY")
            for lock_profit_value in lock_on_profits:
                if lock_profit_value > curr_profit:
                    break
                locked_sl = price_open + (lock_profit_value / 100000)
                if new_sl_for_buy > locked_sl:
                    rsi_oco.modify_position(symbol, ticket_id, locked_sl)
                
            if new_sl_for_buy > curr_sl:
                rsi_oco.modify_position(symbol, ticket_id, new_sl_for_buy)
                
        else:
            print("Opened position is SELL")
            for lock_profit_value in lock_on_profits:
                if lock_profit_value > curr_profit:
                    break
                locked_sl = price_open - (lock_profit_value / 100000)
                if new_sl_for_sell < locked_sl:
                    rsi_oco.modify_position(symbol, ticket_id, locked_sl)
                
            if new_sl_for_sell < curr_sl:
                rsi_oco.modify_position(symbol, ticket_id, new_sl_for_sell)
                
    else:
        if curr_sl != initial_sl:
            rsi_oco.modify_position(symbol, ticket_id, initial_sl)


#TODO: Popraviti trailing, kad je pocetak trejda i kad prvi put pomakne
#      stop loss kad je u profitu 1 dolar, treba napraviti da ako krene padat, da vrati na pocetni stop loss
#      cisto zbog malo fleksibilnosti, jer ovako ode malo u profit -> modificira stop loss -> krene padat ->
#      brzo se triggera stop loss jer je pomaknut. Znaci moramo imat neki maximum koji zelimo riskirat.


#TODO: Mozda ubaciti moving average (imas gotov code u chatGPTu)

#TODO: Ako je zadnji trejd loss, dodati neki cooldown ili neki dodatni indikator ili kalkulaciju za 
#      iduci trejd

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

    time.sleep(0.1)
    os.system('cls')