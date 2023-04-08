import MetaTrader5 as mt5
from config import *
import pandas as pd
import numpy as np
import rsi_oco
import time
import os
import ta

# Login details
account = int(51055781) # Demo
password = "afYNzNX6" # Demo
server = "ICMarketsSC-Demo" # Demo

############################################################################################

symbol = 'BTCUSD'
timeframe = mt5.TIMEFRAME_M1 # integer value representing minutes
start_bar = 0 # initial position of first bar (0 means the current bar, 1 means from the last candle's close price)
num_bars = 1440 # number of bars
lot_size = 1.0


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

authorize()

contract_size = mt5.symbol_info(symbol).trade_contract_size

point = mt5.symbol_info(symbol).point # BTC point = 0.01 .... EURUSD is 0.001
price_ask = mt5.symbol_info_tick(symbol).ask
price_bid = mt5.symbol_info_tick(symbol).bid
stop_loss_from_ask = price_ask + 1000 * point
stop_loss_from_bid = price_bid + 1000 * point

# STOP LOSS FOR EURUSD (FOREX) = 10 pips is $1
# STOP LOSS FOR BTC (CRYPTO?) = 1000 pips is $10 (10 x 100)

print("PRICE ASK: ", price_ask)
print("PRICE BID: ", price_bid)

print("SL ASK: ", stop_loss_from_ask)
print("SL BID: ", stop_loss_from_bid)
print("Contract Size: ", contract_size)
print("Point: ", point)
