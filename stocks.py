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

from datetime import datetime, date, timedelta
import re
import logging
import sys

logging.basicConfig(filename=config.log_file,
                            filemode='a',
                            format='%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                            datefmt='%d-%b-%y %H:%M',
                            level=logging.INFO)

class User:
    def __init__(self):
        self.username = config.username
        self.password = config.password
        self.otp = config.otp
        self.path_to_fs_key = config.path_to_fs_key
    def login(self):
        #For Website Login
        totp  = pyotp.TOTP(self.otp).now()
        # print(totp)
        login = rh.login(self.username, self.password, mfa_code=totp)
        logging.info("Logging into %s RH account" %self.username)
    def verify_credentials(self):
        home_dir = os.path.expanduser('~/')
        json_path = home_dir + self.path_to_fs_key
        cred = credentials.Certificate(json_path)
        firebase_admin.initialize_app(cred)
        logging.info("Setup firebase connection ..")


class Trades:
    # Categories = ["Growth", "Swing", "ETF", "Crypto"] 
    # The init method or constructor
    def __init__(self, ticker, shares, avg_price, date_bought, date_updated, category=None):
           
        ticker_changes = {'THCB': 'MVST', 'ALUS': 'FREY', 'CREE': 'WOLF'}
        # Instance Variable
        if ticker in ticker_changes:
            self.ticker = ticker_changes.get(ticker)
        else:
            self.ticker = ticker 
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
            logging.warning("Ticker no longer active: " + self.ticker)

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
            logging.warning("Free stock sold: " + self.ticker)

    @staticmethod
    def from_dict(source):
        return Profits(source['ticker'], source['date_bought'], source['date_sold'], source['shares_sold'], source['avg_buy_price'],
            source['avg_sell_price'], source['position_open'], source['category'])

#one time run for setup
def initialize_open_positions():
    #Ensure trades collection is deleted
    logging.info("Running Initialize_Open_Positions ..")
    db = firestore.client()
    fs_generator = db.collection(u'trades').list_documents(page_size=5)
    collection_size = sum(1 for x in fs_generator)
    if collection_size:
        logging.error("Collection is not empty")
        return

    list_stock_positions = rh.account.get_open_stock_positions(info=None)
    counter = 0
    logging.info("%s open positions" %len(list_stock_positions))
    for pos in list_stock_positions:
        resp = requests.get(pos['instrument'])
        ticker = json.loads(resp.text)['symbol']
        logging.info(u'Adding position for: ' + ticker)
        
        num_shares = round(float(pos['shares_available_for_exercise']), 2)
        avg_price = round(float(pos['average_buy_price']), 2)
        date_bought = pos['created_at']
        date_updated = pos['updated_at']
        fs_trade = Trades(ticker, num_shares, avg_price, date_bought, date_updated)
        db.collection(u'trades').document(ticker).set(fs_trade.__dict__)
        logging.info(u'New position: ' + ticker)
        counter += 1
    logging.info(str(counter) + " positions added")

#setup buys & sells Master Megaclass method
def initialize_all_profit():
    #Ensure profits & temp_trades collection is deleted
    logging.info("Running Initialize_Profits ..")
    db = firestore.client()
    fs_generator = db.collection(u'profits').list_documents(page_size=5)
    fs_generator_temp = db.collection(u'temp_trades').list_documents(page_size=5)
    collection_size = sum(1 for x in fs_generator)
    collection_size_temp = sum(1 for x in fs_generator_temp)
    if collection_size or collection_size_temp:
        logging.error("Collection is not empty")
        return

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
                    logging.info(u'Updated temp trade position: ' + ticker)
                    doc_trade_ref.update(open_position_fs.__dict__)

                #update stock price
                fs_profit.update_profit()
                fs_profit.update_profit_percentage()
                doc_ref.update(fs_profit.__dict__)
                sell_counter += 1
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
                    logging.info(u'Updated temp trade position: ' + ticker)
                    doc_trade_ref.update(open_position_fs.__dict__)

                fs_profit = Profits(ticker, date_bought, date_sold, shares_sold, avg_buy_price, avg_sell_price, position_open, category)
                db.collection(u'profits').document(ticker).set(fs_profit.__dict__)
                sell_counter += 1
                logging.info("New: sold %s - shares: %s, avg_price: %s" 
                    %(ticker, str(shares_sold), str(avg_sell_price)))
    logging.info("Number of buys: %s" %(str(buy_counter)))
    logging.info("Number of sells: %s" %(str(sell_counter)))

    
#Weekly Run
def update_open_positions():
    db = firestore.client()
    list_open_positions = rh.account.get_open_stock_positions(info=None)
    logging.info("Number of open positions: " + str(len(list_open_positions)))
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
                logging.info(u'Updated position: ' + ticker)
            #update stock price
            fs_trade.update_stock_close()
            fs_trade.update_percent_gain()
            fs_trade.update_value_gain()
            doc_ref.update(fs_trade.__dict__)
        else:
            #create new trade
            num_shares = round(float(rh_pos['shares_available_for_exercise']), 2)
            if not num_shares:
                logging.info("No shares bought for " + ticker)
                continue
            avg_price = round(float(rh_pos['average_buy_price']), 2)
            date_bought = rh_pos['created_at']
            date_updated = rh_pos['updated_at']
            fs_trade = Trades(ticker, num_shares, avg_price, date_bought, date_updated)
            db.collection(u'trades').document(ticker).set(fs_trade.__dict__)
            counter += 1
            logging.info(u'New position: ' + ticker)
    logging.info(str(counter) + " updated positions")

#Weekly Run
def update_profits():
    logging.info("Updating profits ..")
    db = firestore.client()
    #Don't need to list all open stock orders, get latest 10
    list_stock_positions = rh.orders.get_all_stock_orders()[:10]
    counter = 0
    for rh_pos in list_stock_positions:
        if rh_pos['side'] != 'sell' or rh_pos['state'] != 'filled':
            continue

        #check if this update has happened in the past week (don't want to double count profits from prev weeks)
        today = date.today()
        last_week = today - timedelta(days=6)
        date_sold = rh_pos['updated_at']
        #parse updated_time
        x = re.search("[^T]*", date_sold)
        date_sold_formatted = datetime.strptime(x[0], '%Y-%m-%d')
        if date_sold_formatted.date() < last_week:
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
                logging.info(u'Updated profit position: ' + ticker)
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
            logging.info(u'New profit position: ' + ticker)
    logging.info(str(counter) + " updated profit positions")



new_user = User()
new_user.login()
new_user.verify_credentials()
operation = ""
if len(sys.argv) > 1:
    operation = sys.argv[1]
if operation == "positions":
    update_open_positions()
elif operation == "profits":
    update_profits()
logging.info("Finished script")

## initialize_open_positions()
## initialize_all_profit()
