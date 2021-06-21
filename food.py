from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from pprint import pprint
import pickle
import mood
import housing
import threading
import queue
import time
import email_mgr

#uses service account
scope =["https://spreadsheets.google.com/feeds",'https://www.googleapis.com/auth/spreadsheets',"https://www.googleapis.com/auth/drive.file","https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(r"C:\Users\shaur\OneDrive\scratch\jarvis\jarvis-creds.json", scope)
client = gspread.authorize(creds)

def get_pricing_dict():
    with open(r"C:\Users\shaur\OneDrive\scratch\jarvis\food_pricing.pickle", 'rb') as handle:
        food_pricing = pickle.load(handle)
    return food_pricing

def update_pricing_dict(food_pricing):
    with open(r"C:\Users\shaur\OneDrive\scratch\jarvis\food_pricing.pickle", 'wb') as handle:
        pickle.dump(food_pricing, handle, protocol=pickle.HIGHEST_PROTOCOL)

#Sanitize Input
def sanitize_input_meal(prompt):
    meal = ""
    while True:
        try:
            value = str(input(prompt))
        except ValueError:
            print("Bruh give me a string")
            continue
        break
    return value

def sanitize_input_price(prompt):
    price = ""
    while True:
        try:
            price = float(input(prompt))
        except ValueError:
            print("Give a number")
            continue
        break
    return price

def sanitize_input_update_pickle(prompt):
    check = None
    while True:
        try:
            check = str(input(prompt)).lower()
        except ValueError:
            print("Its a yes or no answer fam")
            continue
        if check == 'yes' or check == 'no':
            break
        else:
            print("Its a yes or no answer fam")
            continue
    return check
    
def ask_dining(scope, creds, client):
    num_today = datetime.now().timetuple().tm_yday
    row_num = num_today + 1
    food_pricing = get_pricing_dict()
    lunch = sanitize_input_meal("Yooo what'd u have for lunch today? ").lower()
    lprice = 0
    if food_pricing.get(lunch) != None:
        print("Loading from db ...")
        lprice = food_pricing.get(lunch)
    else:
        lprice = sanitize_input_price("How much did that cost? ")
        if lprice > 0:
            check = sanitize_input_update_pickle("Seems like a new place .. would you like to update the db? ")
            if check == 'yes':
                food_pricing[lunch] = lprice
                update_pricing_dict(food_pricing)
                print("Aight, updated the db!")

    dinner = sanitize_input_meal("Aaaand what was dinner? ").lower()
    dprice = 0
    if food_pricing.get(dinner) != None:
        print("Loading from db ...")
        dprice = food_pricing.get(dinner)
    else:
        dprice = sanitize_input_price("Cost? ")
        if dprice > 0:
            check = sanitize_input_update_pickle("Seems like a new place .. would you like to update the db? ")
            if check == 'yes':
                food_pricing[dinner] = dprice
                update_pricing_dict(food_pricing)
                print("Aight, updated the db!")

    sheet = client.open("Intel").sheet1
    today = datetime.now().strftime("%m/%d/%Y")
    insert_row = [str(today), lunch, lprice, dinner, dprice]
    sheet.update(f'A{row_num}:E{row_num}', [insert_row])
    print("Updated Food Sheet \n")

#Food Logging
ask_dining(scope, creds, client)
time.sleep(1)

#Initiate Housing Scraping
que = queue.Queue()
try:
    x = threading.Thread(target=lambda q: q.put(housing.execute()), args=(que,))
    scrape_boolean = housing.sanitize_input_string("U want me to scrape chesapeake-point bookings? ", ["yes", "no"])
except Exception as e:
    print("Error: \n")
    raise e
if scrape_boolean == "yes":
    x.start()
    print("Commecing Web Crawling .. \n")
else:
    scrape_boolean = False
time.sleep(1)

#Mood Journal
print("Now transitioning to vibe check ... \n")
mood.vibe(scope, creds, client)
time.sleep(1)

#Get Scraping Results
if scrape_boolean:
    try:
        availability_dict = que.get(False)
        print("Now printing Web Crawling results .. ")
        if availability_dict :
            pass
        for i in sorted (availability_dict):
            print((i, availability_dict[i]), end ="\n")
        if availability_dict["Plan 2A"] == "(0) Available" and availability_dict["Plan 2B"] == "(0) Available":
            print("sadge: ¯\\_(:/)_/¯ \n")
        else: 
            print("AYOOO: (｡◕‿◕｡) \n")
    except Exception as e:
        print("Error in getting chesapeake-point bookings.. try checking yourself at prometheusapartments.com")
    
#Email Manager
print("Checking emails ... \n")
email_mgr.main()