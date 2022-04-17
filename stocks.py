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

from datetime import datetime
from datetime import date
from datetime import timedelta
import re
import logging

logging.basicConfig(filename='robinhood.log',
                            filemode='a',
                            format='%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                            datefmt='%d-%b-%y %H:%M',
                            level=logging.DEBUG)

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
    print(totp) #TODO OTP IMPORTANT LOGIN OTP PRINT THIS SHIT MF
    login = rh.login(config.username,config.password, mfa_code=totp)

class Trades:
         
    # Categories = ["Long", "Swing", "ETF", "Crypto"] 
    # The init method or constructor
    def __init__(self, ticker, shares, avg_price, date_bought, date_updated, category=None):
           
        # Instance Variable
        self.ticker = ticker #1)should ensure that every Trades object has ticker (non nullable, error out?)
        self.category = category
        self.shares = shares
        self.avg_price = avg_price
        self.date_bought = date_bought
        self.date_updated = date_updated
        self.update_position()
        self.update_stock_close()
        self.update_percent_gain()
        self.update_value_gain()           
       
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
    def update_position(self):   
        self.position = round(self.shares * self.avg_price, 2)

    # api call to get previous close for ticker
    def update_stock_close(self):
        close_price = rh.stocks.get_latest_price(self.ticker)
        if close_price[0]:
            self.stock_close = float(close_price[0])
        else:
            self.stock_close = None
            logging.info("Ticker no longer active: " + self.ticker)

    # calculate percentage diff  #2) should mess with keeping method static, and trying to use self
    # @staticmethod  
    def update_percent_gain(self):    
        prev_price = self.avg_price
        curr_price = self.stock_close
        if curr_price:
            self.percent_gain = round((curr_price - prev_price) / prev_price * 100, 2)

    # calculate curr profit
    # @staticmethod  
    def update_value_gain(self):   #3) static method: Traades.get_value_gain vs instance.get_value_gain 
        num_shares = self.shares
        prev_price = self.avg_price
        curr_price = self.stock_close
        if curr_price:
            self.value_gain = round((curr_price - prev_price) * num_shares, 2)

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=False, indent=4)

    @staticmethod
    def from_dict(source):
        return Trades(source['ticker'], source['shares'], source['avg_price'], source['date_bought'], 
            source['date_updated'], source['category'])

#check links:
# https://stackoverflow.com/questions/3768895/how-to-make-a-class-json-serializable
#  
# firestore: adding data => set doc_id as ticker

"""
1) update position, shares -> should trigger updates in avg_price & percent_gain
    can do that in set_shares method or manually call get_avg_price and get_percent_gain

a) these updates should be parsed from robinhood/ plaid: extract trade with shares, and money spent on those shares

b) selling should invovle profits table


2) prev_close should update on cronjob
3) check config.py for github token!

"""

#for profits: you can have partial sells 
#new:= ticker, profit
    #but in order to calculate that we need ticker, avg_price, shares_sold, price_sold, sold_date
#add to profit:= ticker, profit
    # requires same thing, with added previous profit
# Things i want to track: #total shares i've sold, avg buy/ avg sell?, total profit (percentage & value)
#date bought/ date sold? everything in trades table - things i don't need + things related to selling
class Profits:
    def __init__(self, ticker, date_bought, date_sold, shares_sold, avg_buy_price, avg_sell_price, position_open, category=None):
        # Instance Variable
        self.ticker = ticker
        self.category = category
        self.date_bought = date_bought
        self.date_sold = date_sold
        self.shares_sold = shares_sold
        self.avg_buy_price = avg_buy_price
        self.avg_sell_price = avg_sell_price
        self.position_open = position_open
        self.update_profit()
        self.update_profit_percentage()

    # ticker cannot be changed once initialized    
    def get_ticker(self):    
        return self.ticker  

    # category set in firestore    
    def get_category(self):    
        return self.category

    # category set in firestore    
    def get_date_bought(self):    
        return self.date_bought

    # date_updated can be changed
    def set_date_sold(self, date_sold):
        self.date_sold = date_sold

    def get_date_sold(self):    
        return self.date_sold

    def set_shares_sold(self, shares_sold):
        self.shares_sold = shares_sold

    def get_shares_sold(self):    
        return self.shares_sold

    def set_avg_buy_price(self, avg_buy_price):    
        self.avg_buy_price = avg_buy_price

    def get_avg_buy_price(self):    
        return self.avg_buy_price

    def set_avg_sell_price(self, avg_sell_price):
        self.avg_sell_price = avg_sell_price

    def get_avg_sell_price(self):    
        return self.avg_sell_price

    def get_position_open(self):    
        return self.position_open

    # calculate value diff  
    def update_profit(self):
        self.profit = (self.avg_sell_price - self.avg_buy_price) * self.shares_sold

    def update_profit_percentage(self):
        if self.avg_buy_price:
            self.profit_percentage = round((self.avg_sell_price - self.avg_buy_price) / self.avg_buy_price * 100, 2)
        else:
            self.profit_percentage = round((self.avg_sell_price - self.avg_buy_price) / 1 * 100, 2)
            logging.info("Free stock sold: " + self.ticker)

    @staticmethod
    def from_dict(source):
        return Profits(source['ticker'], source['date_bought'], source['date_sold'], source['shares_sold'], source['avg_buy_price'],
            source['avg_sell_price'], source['position_open'], source['category'])

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
# #403830
# # OTP 166772 941932



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
    list_open_positions = rh.account.get_open_stock_positions(info=None)
    print("Number of open positions: " + str(len(list_open_positions)))
    counter = 0
    for rh_pos in list_open_positions:
        resp = requests.get(rh_pos['instrument'])
        ticker = json.loads(resp.text)['symbol']
        #check if ticker exists in firestore
        doc_ref = db.collection(u'trades').document(ticker)
        doc = doc_ref.get()
        if doc.exists:
            #compare date_updated
            date_updated = rh_pos['updated_at']  
            fs_trade = Trades.from_dict(doc.to_dict())
            prev_date_updated = fs_trade.get_date_updated()
            #update position size
            if date_updated != prev_date_updated:
                fs_trade.set_date_updated(date_updated)
                num_shares = round(float(rh_pos['shares_available_for_exercise']), 2)
                avg_price = round(float(rh_pos['average_buy_price']), 2)
                fs_trade.set_shares(num_shares)
                fs_trade.set_avg_price(avg_price)
                #just calculates position based on shares * price
                fs_trade.update_position()
                counter += 1
                print(u'Updated position: ' + ticker)
            #update stock price
            fs_trade.update_stock_close()
            fs_trade.update_percent_gain()
            fs_trade.update_value_gain()
            doc_ref.update(fs_trade.__dict__)
        else:
            #create new trade
            num_shares = round(float(rh_pos['shares_available_for_exercise']), 2)
            avg_price = round(float(rh_pos['average_buy_price']), 2)
            date_bought = rh_pos['created_at']
            date_updated = rh_pos['updated_at']
            fs_trade = Trades(ticker, num_shares, avg_price, date_bought, date_updated)
            db.collection(u'trades').document(ticker).set(fs_trade.__dict__)
            counter += 1
            print(u'New position: ' + ticker)
    print(str(counter) + " updated positions")

#INTIALIZE ROBINHOOD & FIREBASE
login()
home_dir = os.path.expanduser('~/')
json_path = home_dir + "OneDrive/scratch/jarvis/firestore_key.json"
cred = credentials.Certificate(json_path)
firebase_admin.initialize_app(cred)

# list_open_positions = rh.account.get_open_stock_positions()
# print(len(list_open_positions))
# for pos in list_open_positions:
#     resp = requests.get(pos['instrument'])
#     ticker = json.loads(resp.text)['symbol']
#     print(ticker)
#     print(pos)

#SANDBOX
# print("Starting process")
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

# list_stock_positions = rh.orders.get_all_stock_orders()
# f = open("myfile.txt", "w")
# # this goes chronologically too!
# print("Number of stock orders " + str(len(list_stock_positions)))
# for pos in list_stock_positions:
#     resp = requests.get(pos['instrument'])
#     ticker = json.loads(resp.text)['symbol']
#     f.write(ticker)
#     f.write(str(pos))
# print("finished")

#one time run for setup
#handles buys & sells MASTER MEGACLASS method
def initialize_all_profit():
    logging.info("Running Initialize_Profits ..")
    db = firestore.client()
    list_stock_positions = rh.orders.get_all_stock_orders(info=None)
    buy_counter = 0
    sell_counter = 0
    for rh_pos in reversed(list_stock_positions):
        resp = requests.get(rh_pos['instrument'])
        ticker = json.loads(resp.text)['symbol']
        if rh_pos['state'] != 'filled':
            logging.info(("Skipping %s w/ id: %s" %(ticker, rh_pos['id'])))
            continue
        if rh_pos['side'] == 'buy':
            #check if ticker exists in firestore
            doc_ref = db.collection(u'temp_trades').document(ticker)
            doc = doc_ref.get()
            if doc.exists:
                #update buy for a ticker
                fs_trade = Trades.from_dict(doc.to_dict())
                date_updated = rh_pos['updated_at']
                fs_trade.set_date_updated(date_updated)
                #add bought shares to total
                new_shares = round(float(rh_pos['cumulative_quantity']), 2)
                old_shares = fs_trade.get_shares()
                num_shares = new_shares + old_shares
                #calculate new avg buy price
                new_avg_price = round(float(rh_pos['average_price']), 2)
                old_avg_price = fs_trade.get_avg_price()
                new_total_buy_price = new_avg_price * new_shares
                old_total_buy_price = old_avg_price * old_shares
                avg_buy_price = (new_total_buy_price + old_total_buy_price) / (num_shares)

                fs_trade.set_shares(num_shares)
                fs_trade.set_avg_price(avg_buy_price)
                #just calculates position based on shares * price
                fs_trade.update_position()
                buy_counter += 1
                print(u'Updated temp trade position: ' + ticker)
                logging.info("Updating buy for %s - shares: %s, avg_price: %s" 
                    %(ticker, str(new_shares), str(new_avg_price)))
                doc_ref.update(fs_trade.__dict__)
            else:
                #first buy for a ticker
                num_shares = round(float(rh_pos['cumulative_quantity']), 2)
                avg_buy_price = round(float(rh_pos['average_price']), 2)
                date_bought = rh_pos['created_at']
                date_updated = rh_pos['updated_at']
                #Get category from trade collection
                doc_trade_ref = db.collection(u'trades').document(ticker)
                doc_trade = doc_trade_ref.get()
                category = None
                #redundant check
                if doc_trade.exists:
                    open_position_fs = Trades.from_dict(doc_trade.to_dict())
                    category = open_position_fs.get_category()
                fs_trade = Trades(ticker, num_shares, avg_buy_price, date_bought, date_updated, category)
                db.collection(u'temp_trades').document(ticker).set(fs_trade.__dict__)
                buy_counter += 1
                print(u'New temp trade position: ' + ticker)
                logging.info("New buy for %s - shares: %s, avg_price: %s" 
                    %(ticker, str(num_shares), str(avg_buy_price)))
        if rh_pos['side'] == 'sell':
            #check if ticker exists in firestore
            doc_ref = db.collection(u'profits').document(ticker)
            doc = doc_ref.get()
            if doc.exists:
                #update profit for a ticker
                fs_profit = Profits.from_dict(doc.to_dict())
                date_sold = rh_pos['updated_at']
                fs_profit.set_date_sold(date_sold)
                #add sold shares to total
                new_shares_sold = round(float(rh_pos['cumulative_quantity']), 2)
                old_shares_sold = fs_profit.get_shares_sold()
                total_shares_sold = new_shares_sold + old_shares_sold
                #calculate new avg sell price
                new_avg_price = round(float(rh_pos['average_price']), 2)
                old_avg_price = fs_profit.get_avg_sell_price()
                new_total_sell_price = new_avg_price * new_shares_sold
                old_total_sell_price = old_avg_price * old_shares_sold
                avg_sell_price = (new_total_sell_price + old_total_sell_price) / (total_shares_sold)
                fs_profit.set_shares_sold(total_shares_sold)
                fs_profit.set_avg_sell_price(avg_sell_price)

                #get avg_buy price from trades collection & update num_shares_held
                doc_trade_ref = db.collection(u'temp_trades').document(ticker)
                doc_trade = doc_trade_ref.get()
                if doc_trade.exists:
                    open_position_fs = Trades.from_dict(doc_trade.to_dict())
                    avg_buy_price = open_position_fs.get_avg_price()
                    fs_profit.set_avg_buy_price(avg_buy_price)
                    #update trade positions with less num_shares
                    open_position_fs.set_date_updated(date_sold)
                    num_shares = open_position_fs.get_shares()
                    remaining_shares = num_shares - new_shares_sold
                    open_position_fs.set_shares(remaining_shares)
                    open_position_fs.update_position()
                    print(u'Updated temp trade position: ' + ticker)
                    doc_trade_ref.update(open_position_fs.__dict__)

                #update stock price
                fs_profit.update_profit()
                fs_profit.update_profit_percentage()
                doc_ref.update(fs_profit.__dict__)
                sell_counter += 1
                print(u'Updated profit position: ' + ticker)
                logging.info("Update: sold %s - shares: %s, avg_price: %s" 
                    %(ticker, str(new_shares_sold), str(new_avg_price)))
            else:
                #create new profit
                shares_sold = round(float(rh_pos['cumulative_quantity']), 2)
                avg_sell_price = round(float(rh_pos['average_price']), 2)
                date_sold = rh_pos['updated_at']

                #get avg_buy price from trades collection & update num_shares_held
                doc_trade_ref = db.collection(u'temp_trades').document(ticker)
                doc_trade = doc_trade_ref.get()
                avg_buy_price = 0
                date_bought = None
                position_open = True
                category = None
                if doc_trade.exists:
                    open_position_fs = Trades.from_dict(doc_trade.to_dict())
                    avg_buy_price = open_position_fs.get_avg_price()
                    date_bought = open_position_fs.get_date_bought()
                    category = open_position_fs.get_category()
                    position_open = True
                    #update trade positions with less num_shares
                    open_position_fs.set_date_updated(date_sold)
                    num_shares = open_position_fs.get_shares()
                    remaining_shares = num_shares - shares_sold
                    open_position_fs.set_shares(remaining_shares)
                    open_position_fs.update_position()
                    print(u'Updated temp trade position: ' + ticker)
                    doc_trade_ref.update(open_position_fs.__dict__)

                fs_profit = Profits(ticker, date_bought, date_sold, shares_sold, avg_buy_price, avg_sell_price, position_open, category)
                db.collection(u'profits').document(ticker).set(fs_profit.__dict__)
                sell_counter += 1
                print(u'New profit position: ' + ticker)
                logging.info("New: sold %s - shares: %s, avg_price: %s" 
                    %(ticker, str(shares_sold), str(avg_sell_price)))
    print(str(buy_counter) + " buys")
    logging.info("Number of buys: %s" %(str(buy_counter)))
    print(str(sell_counter) + " sells")
    logging.info("Number of sells: %s" %(str(sell_counter)))



# #Weekly Run
def update_profits():
    db = firestore.client()
    #Don't need to list all open stock orders, get latest 10, will get next batch if needed
    list_stock_positions = rh.orders.get_all_stock_orders()[:10]
    counter = 0
    for rh_pos in list_stock_positions:
        if rh_pos['side'] != 'sell' or rh_pos['state'] != 'filled':
            continue

        #check if this update has happened in the past week (don't want to double count profits from prev weeks)
        today = date.today()
        last_week = today - datetime.timedelta(days=6)
        date_sold = rh_pos['updated_at']
        #parse updated_time
        x = re.search("[^T]*", date_sold)
        date_sold_formatted = datetime.strptime(x, '%Y-%m-%d')
        if date_sold_formatted < last_week:
            continue

        #Processing
        resp = requests.get(rh_pos['instrument'])
        ticker = json.loads(resp.text)['symbol']
        #check if ticker exists in firestore
        doc_ref = db.collection(u'profits').document(ticker)
        doc = doc_ref.get()
        if doc.exists:
            #compare date_sold
            fs_profit = Profits.from_dict(doc.to_dict())
            prev_date_sold = fs_profit.get_date_sold()
            #update profit
            if date_sold != prev_date_sold:
                fs_profit.set_date_sold(date_sold)
                recent_shares_sold = round(float(rh_pos['cumulative_quantity']), 2)
                total_shares_sold = recent_shares_sold
                #If shares were prev sold, increment total_sold
                if fs_profit.get_shares_sold():
                    total_shares_sold = fs_profit.get_shares_sold() + recent_shares_sold
                fs_profit.set_shares_sold(total_shares_sold)
                #avg_sell_price = total_price / total_shares
                recent_avg_sell_price = round(float(rh_pos['average_price']), 2)
                #these checks are redundant but just in case
                avg_sell_price = recent_avg_sell_price
                if fs_profit.get_avg_sell_price() and fs_profit.get_shares_sold():
                    total_old_sell_price = fs_profit.get_avg_sell_price() * fs_profit.get_shares_sold()
                    total_new_sell_price = recent_avg_sell_price * recent_shares_sold
                    avg_sell_price = (total_old_sell_price + total_new_sell_price) / (fs_profit.get_shares_sold() + recent_shares_sold)
                fs_profit.set_avg_sell_price(avg_sell_price)

                doc_trade_ref = db.collection(u'trades').document(ticker)
                doc_trade = doc_trade_ref.get()
                #redundant check
                if doc_trade.exists:
                    open_position_fs = Trades.from_dict(doc_trade.to_dict())
                    avg_buy_price = open_position_fs.get_avg_price()
                    fs_profit.set_avg_buy_price(avg_buy_price)

                counter += 1
                print(u'Updated profit position: ' + ticker)
            #update profit
            fs_profit.update_profit()
            fs_profit.update_profit_percentage()
            doc_ref.update(fs_profit.__dict__)
        else:
            #create new profit
            shares_sold = round(float(rh_pos['cumulative_quantity']), 2)
            avg_sell_price = round(float(rh_pos['average_price']), 2)
            # date_bought = rh_pos['created_at']
            # date_updated = rh_pos['updated_at']
            doc_trade_ref = db.collection(u'trades').document(ticker)
            doc_trade = doc_trade_ref.get()
            avg_buy_price = 0
            date_bought = None
            position_open = True
            category = None
            #redundant check
            if doc_trade.exists:
                open_position_fs = Trades.from_dict(doc_trade.to_dict())
                avg_buy_price = open_position_fs.get_avg_price()
                date_bought = open_position_fs.get_date_bought()
                category = open_position_fs.get_category()
                position_open = True
            fs_profit = Profits(ticker, date_bought, date_sold, shares_sold, avg_buy_price, avg_sell_price, position_open, category=None)
            db.collection(u'profits').document(ticker).set(fs_profit.__dict__)
            counter += 1
            print(u'New profit position: ' + ticker)
    print(str(counter) + " updated positions")

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
# - all sell orders compile list
# - figure out logic on how to maintain (what should profits table know?)

# 2. maintenance 
# can use get_all_positions(b'AAPL') method with info set to ticker in question

logging.info("Initiating Profit MegaRun ..")
initialize_all_profit()
logging.info("Finished Profit MegaRun")
