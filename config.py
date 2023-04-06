import MetaTrader5 as mt5

# Login details
account = int(51055781) # Demo
password = "afYNzNX6" # Demo
server = "ICMarketsSC-Demo" # Demo

############################################################################################

symbol = 'EURUSD'
timeframe = mt5.TIMEFRAME_M1 # integer value representing minutes
start_bar = 0 # initial position of first bar (0 means the current bar, 1 means from the last candle's close price)
num_bars = 1440 # number of bars
lot_size = 1.0

max_open_positions = 1 # max number positions to open

stop_loss_pips = 10
trailing_profit_trigger = 1 # USD

overbought_level = 90
oversold_level = 10

rsi_period = 5