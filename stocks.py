"""
Have 2 tables:
    -current trades (can keep track of current price) [ticker, category, total invested, date first bought, shares, avg price, previous close, percent gain]
        showcase on google studio
        to get yesterday close will have to run a cron job every evening w/ jarvis 
    -profits
        seperate table that updates with every sell (primary key is ticker) [ticker, profit]
"""

#First check if ticker exists in trades table
    #YES --> update table with position, shares, avg_price (see below)
    #NO --> create new entry
import json
import robin_stocks.robinhood as rh
import requests
import pyotp
import os 
import config

import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore


# {
#     'url': 'https://api.robinhood.com/positions/458876026/c755d776-0378-4d84-b6c8-d9f54306048e/',
#     'instrument': 'https://api.robinhood.com/instruments/c755d776-0378-4d84-b6c8-d9f54306048e/',
#     'instrument_id': 'c755d776-0378-4d84-b6c8-d9f54306048e',
#     'account': 'https://api.robinhood.com/accounts/458876026/',
#     'account_number': '458876026',
#     'average_buy_price': '135.5101',
#     'pending_average_buy_price': '135.5101',
#     'quantity': '0.29518100',
#     'intraday_average_buy_price': '0.0000',
#     'intraday_quantity': '0.00000000',
#     'shares_available_for_exercise': '0.29518100',
#     'shares_held_for_buys': '0.00000000',
#     'shares_held_for_sells': '0.00000000',
#     'shares_held_for_stock_grants': '0.00000000',
#     'shares_held_for_options_collateral': '0.00000000',
#     'shares_held_for_options_events': '0.00000000',
#     'shares_pending_from_options_events': '0.00000000',
#     'shares_available_for_closing_short_position': '0.00000000',
#     'ipo_allocated_quantity': '0.00000000',
#     'ipo_dsp_allocated_quantity': '0.00000000',
#     'avg_cost_affected': False,
#     'updated_at': '2021-10-04T19:52:00.676509Z',
#     'created_at': '2021-10-04T19:51:59.423720Z'
# }
# ticker = json.load
# position = average_buy_price * quantity [maybe use shares & average price && calculate position]
# date_bought = created_at
# date_updated = updated_at
# shares = quantity


#maybe should apply as a class method? @classmethod Trades.login()
def login():
    totp  = pyotp.TOTP(config.otp).now()
    login = rh.login(config.username,config.password, mfa_code=totp)

class Trades:
         
    # Categories = ["Long", "Swing", "ETF", "Crypto"] 
    # The init method or constructor
    def __init__(self, ticker, shares, avg_price, date_bought, date_updated):
           
        # Instance Variable
        self.ticker = ticker #1)should ensure that every Trades object has ticker (non nullable, error out?)
        self.category = None
        self.shares = shares
        self.avg_price = avg_price
        self.date_bought = date_bought
        self.date_updated = date_updated
        self.position= self.get_position() #do i need to pass in self?
        self.prev_close = self.get_prev_close()
        self.percent_gain = self.get_percent_gain()
        self.value_gain = self.get_value_gain()           
       
    # ticker cannot be changed once initialized    
    def get_ticker(self):    
        return self.ticker   
       
    # category set in firestore    
    def get_category(self):    
        return self.category

    # num_shares is fluid
    def set_shares(self, shares):
        self.shares = shares
          
    def get_shares(self):    
        return self.shares

    # position is fluid 
    def set_avg_price(self, avg_price):
        self.avg_price = avg_price
       
    def get_avg_price(self):    
        return self.avg_price   
       
    # date_bought is fixed    
    def get_date_bought(self):    
        return self.date_bought

    # date_updated can be changed
    def set_date_updated(self, date_updated):
        self.date_updated = date_updated

    def get_date_updated(self):    
        return self.date_updated

    # utility method for calculating avg_price   
    # @staticmethod
    def get_position(self):   
        return round(self.shares * self.avg_price, 2)

    def set_prev_close(self, prev_close):
        self.prev_close = prev_close

    # api call to get previous close for ticker
    def get_prev_close(self):
        close_price = rh.stocks.get_latest_price(self.ticker, includeExtendedHours=True)
        return float(close_price[0])

    # calculate percentage diff  #2) should mess with keeping method static, and trying to use self
    # @staticmethod  
    def get_percent_gain(self):    
        prev_price = self.avg_price
        curr_price = self.prev_close
        return round((curr_price - prev_price) / prev_price * 100, 2)

    # calculate curr profit
    # @staticmethod  
    def get_value_gain(self):   #3) static method: Traades.get_value_gain vs instance.get_value_gain 
        num_shares = self.shares
        prev_price = self.avg_price
        curr_price = self.prev_close
        return round((curr_price - prev_price) * num_shares, 2)

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=False, indent=4)

    @staticmethod
    def from_dict(source):
        return Trades(source['ticker'], source['shares'], source['avg_price'], source['date_bought'], source['date_updated'])

#check links:
# https://stackoverflow.com/questions/3768895/how-to-make-a-class-json-serializable
#  
# firestore: adding data => set doc_id as ticker

"""
1) update position, shares -> should trigger updates in avg_price & percent_gain
    can do that in set_shares method or manually call get_avg_price and get_percent_gain

a) these updates should be parsed from robinhood/ plaid: extract trade with shares, and money spent on those shares

b) selling should invovle profits table


2) prev_close should update on a cronjob


"""

#for profits: you can have partial sells 
#new:= ticker, profit
    #but in order to calculate that we need ticker, avg_price, shares_sold, price_sold, sold_date
#add to profit:= ticker, profit
    # requires same thing, with added previous profit
class Profits:
    def __init__(self, ticker, shares_sold, price_bought, price_sold, date_sold): 

        # Instance Variable
        self.ticker = ticker
        self.category = None
        self.profit = self.get_profit(shares_sold, price_bought, price_sold)
        self.date_sold = date_sold

    # ticker cannot be changed once initialized    
    def get_ticker(self):    
        return self.ticker  

    # category set in firestore    
    def get_category(self):    
        return self.category

    # calculate percentage diff  
    @staticmethod  
    def get_profit(shares_sold, price_bought, price_sold):
        return (price_sold - price_bought) * shares_sold

    # date_updated can be changed
    def set_date_sold(self, date_sold):
        self.date_sold = date_sold

    def get_date_sold(self):    
        return self.date_sold


# totp  = pyotp.TOTP("TW77P2ZDFTX5LDXL").now()
# login = rh.login('shaurya.sanghvi@gmail.com','RNaryan#99', mfa_code=totp)
# lst = rh.account.get_open_stock_positions(info=None)

# g = requests.get(response['instrument'])
# txt = g.text
# json.loads(g.txt)['symbol']
# tker = rh.stocks.get_symbol_by_url('https://api.robinhood.com/instruments/c755d776-0378-4d84-b6c8-d9f54306048e/')
# print(tker)

# login() #externalize to property file
# j=rh.stocks.get_latest_price('AMC',includeExtendedHours=True)
# print(j)
# print(j[0])
# print(float(j[0]))
# list_stock_positions = rh.account.get_open_stock_positions(info=None)
# list_tickers = []
# for pos in list_stock_positions:
#    resp = requests.get(pos['instrument'])
#    ticker = json.loads(resp.text)['symbol']
#    list_tickers.append(ticker)
# print(list_tickers)
# #403830
# # 166772 941932

# helper methhod for trade creatio in firestore
def help_create_trade(ticker):
    num_shares = round(float(pos['quantity']), 2)
    avg_price = round(float(pos['average_buy_price']), 2)
    date_bought = pos['created_at']
    date_updated = pos['updated_at']
    curr_trade = Trades(ticker, num_shares, avg_price, date_bought, date_updated)
    db.collection(u'trades').document(ticker).set(curr_trade.__dict__)

#one time run for setup
def initialize_open_positions():
    db = firestore.client()
    list_stock_positions = rh.account.get_open_stock_positions(info=None)
    counter = 0
    for pos in list_stock_positions:
       resp = requests.get(pos['instrument'])
       ticker = json.loads(resp.text)['symbol']
       help_create_trade(ticker)
       print("Added: " + ticker)
       counter += 1
    print(str(counter) + " positions added")
    
#Weekly Run
def update_open_positions():
    db = firestore.client()
    list_stock_positions = rh.account.get_open_stock_positions(info=None)
    print("Number of open positions" + str(len(list_stock_positions)))
    counter = 0
    for pos in list_stock_positions:
        resp = requests.get(pos['instrument'])
        ticker = json.loads(resp.text)['symbol']
        #check if pos exists in firestore
        doc_ref = db.collection(u'trades').document(ticker)
        doc = doc_ref.get()
        if doc.exists:
            #compare date_updated
            date_updated = pos['updated_at']  
            curr_trade = Trades.from_dict(doc.to_dict())
            prev_date_updated = curr_trade.get_date_updated()
            dict_updates = {}
            #change in position
            if date_updated != prev_date_updated:
                dict_updates[u'date_updated'] = curr_trade.get_date_updated()
                dict_updates[u'shares'] = curr_trade.get_shares()
                dict_updates[u'avg_price'] = curr_trade.get_avg_price()
                dict_updates[u'position'] = curr_trade.get_position()
                counter += 1
            #update stock price
            last_week_close = curr_trade.get_prev_close()
            curr_trade.set_prev_close(last_week_close)
            percent_gain = curr_trade.get_percent_gain()
            value_gain = curr_trade.get_value_gain()
            dict_updates[u'prev_close'] = last_week_close
            dict_updates[u'percent_gain'] = percent_gain
            dict_updates[u'value_gain'] = value_gain
            doc_ref.update(dict_updates)
        else:
            #create new trade
            help_create_trade(ticker)
            counter += 1
            print(u'New position: ' + ticker)
    print(str(counter) + " updated positions")

#INTIALIZE ROBINHOOD & FIREBASE
login()
home_dir = os.path.expanduser('~/')
json_path = home_dir + "OneDrive/scratch/jarvis/firestore_key.json"
cred = credentials.Certificate(json_path)
firebase_admin.initialize_app(cred)


#SANDBOX
print("Starting process")
# update_open_positions()



# list_stock_positions = rh.account.get_all_positions(info=None)
# print("Number of open positions " + str(len(list_stock_positions)))
# for pos in list_stock_positions:
#     resp = requests.get(pos['instrument'])
#     ticker = json.loads(resp.text)['symbol']
#     print(ticker)
#     print(pos)

# dtrades = rh.account.get_day_trades(info=None)
# print(str(len(dtrades)))
# print(dtrades)
# print(type(dtrades))

# holdings = rh.account.build_holdings()
# print(holdings)
# print(type(holdings))
# resp = requests.get("https://api.robinhood.com/positions/458876026/50810c35-d215-4866-9758-0ada4ac79ffa")
# print(resp)

list_stock_positions = rh.orders.get_all_stock_orders()
print("Number of stock orders " + str(len(list_stock_positions)))
for pos in list_stock_positions:
    resp = requests.get(pos['instrument'])
    ticker = json.loads(resp.text)['symbol']
    print(ticker)
    print(pos)

# db.collection('persons').add({'name':'John', 'age':40})

# To join our Slack channel where you can discuss trading and coding, click the link https://join.slack.com/t/robin-stocks/shared_invite/zt-7up2htza-wNSil5YDa3zrAglFFSxRIA
# ask how to get recent trades (past week)


#robin_stocks.robinhood.account.get_day_trades(info=None) have to check
#dont want to load history of trades every time
#can filter based on ticker from email
#robin_stocks.robinhood.account.get_open_stock_positions(info=None) this will be helpful

#every week this script will sync w firestore (b/c ill have to give credentials every run)
#should update all open positions
#and should update buys and sells, now
    #buys can be two fold: buying a new stock 
    #buying more of a stock: dependent on type of info, if they give me overall position or recent addition

#2 steps: intialization & maintenance
# 1. intialization
# get all positions: robin_stocks.robinhood.account.get_all_positions(info=ticker)
# ticker, profit, sold_date
# - profit needs (price_sold - avg_price) * num_stock

# 2. maintenance 
# can use get_all_positions(b'AAPL') method with info set to ticker in question