import pandas as pd
import return_codes as rc

import MetaTrader5 as mt5

# OPEN POSITION
def open_position(symbol, o_type, size, stop_distance = None):
    
    if o_type == "SELL":
        print(f"Current BID price: ${mt5.symbol_info_tick(symbol).bid}")
    else:
        print(f"Current ASK price: ${mt5.symbol_info_tick(symbol).ask}")
    

    if(o_type == "BUY"):
        order_type = mt5.ORDER_TYPE_BUY
        price = mt5.symbol_info_tick(symbol).ask
        if(stop_distance):
            sl = stop_distance
            
    if(o_type == "SELL"):
        order_type = mt5.ORDER_TYPE_SELL
        price = mt5.symbol_info_tick(symbol).bid
        if(stop_distance):
            sl = stop_distance


    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": float(size),
        "type": order_type,
        "price": price,
        "sl": sl, # uncomment to exclude from trade
        "tp": 0.0, 
        "magic": 234665,
        "comment": "RenoGPT_OpenTrade",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"Error: {result.retcode}")
        print(f"Description: {rc.errors[0][result.retcode]}")
        print("Check link for error: https://www.mql5.com/en/docs/constants/errorswarnings/enum_trade_return_codes")
    else:
        print ("Order successfully placed!")





# MODIFYING POSITION
def modify_position(symbol, ticket_ID, new_stop_loss):

    # Create the request
    modify_request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "position": ticket_ID,
        "symbol": symbol,
        "sl": new_stop_loss,
        "tp": 0.0,      
    }
    # Send order to MT5
    modify_result = mt5.order_send(modify_request)

    if modify_result.retcode == mt5.TRADE_RETCODE_DONE:
        print("Successfully modified positon!")
    
    else:
        print(f"Error modifying position: {modify_result.retcode}")
        print(f"Description: {rc.errors[0][modify_result.retcode]}")
        print("Check link for error: https://www.mql5.com/en/docs/constants/errorswarnings/enum_trade_return_codes")




# CLOSING POSITION
def positions_get(symbol=None):
    if(symbol is None):
        res = mt5.positions_get()

    else:
        res = mt5.positions_get(symbol = symbol)

    if(res is not None and res != ()):
        df = pd.DataFrame(list(res),columns=res[0]._asdict().keys())
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df
    
    return pd.DataFrame()


def close_position(deal_id):
    open_positions = positions_get()
    open_positions = open_positions[open_positions['ticket'] == deal_id]
    order_type  = open_positions["type"][0]
    symbol = open_positions['symbol'][0]
    volume = open_positions['volume'][0]

    if(order_type == mt5.ORDER_TYPE_BUY):
        order_type = mt5.ORDER_TYPE_SELL
        price = mt5.symbol_info_tick(symbol).bid
    else:
        order_type = mt5.ORDER_TYPE_BUY
        price = mt5.symbol_info_tick(symbol).ask
	
    close_request={
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": float(volume),
        "type": order_type,
        "position": deal_id,
        "price": price,
        "magic": 234665,
        "comment": "RenoGPT_CloseTrade",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(close_request)
    
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print("Failed to close order.")
        print(f"Error: {result.retcode}")
        print(f"Description: {rc.errors[0][result.retcode]}")
    else:
        print ("Order successfully closed!")


def close_positions_by_symbol(symbol):
    open_positions = positions_get(symbol)
    open_positions['ticket'].apply(lambda x: close_position(x))