from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from pprint import pprint

scope =["https://spreadsheets.google.com/feeds",'https://www.googleapis.com/auth/spreadsheets',"https://www.googleapis.com/auth/drive.file","https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(r"C:\Users\shaur\OneDrive\scratch\jarvis\jarvis-creds.json", scope)
client = gspread.authorize(creds)

#Sanitize Input
def sanitize_input_string(prompt, *options):
    answer = ""
    while True:
        try:
            answer = str(input(prompt))
            if answer.isdigit():
            	print("Please give a string")
            	continue
        except ValueError:
            print("Please give a string")
            continue
        if options != () and answer not in options[0]:
            print(f"Please choose from the given options: {options[0]}")
            continue
        else:
            break
    return answer.lower()

def sanitize_input_number(prompt, *options):
    answer = ""
    while True:
        try:
            answer = float(input(prompt))
        except ValueError:
            print("Give a number")
            continue
        if options != () and answer not in options[0]:
            print(f"Please choose from the given options: {options[0]}")
            continue
        else:
        	break
    return answer

def vibe(scope, creds, client):
	num_today = datetime.now().timetuple().tm_yday
	row_num = num_today + 1
	#Questions
	mood = sanitize_input_number("How you feeling? (1-5) ", [1,2,3,4,5])
	emotion1 = sanitize_input_string("What's the primary emotion you felt today? ")
	emotion2 = sanitize_input_string("Any secondary emotion? ")
	energy = sanitize_input_string("Energy level: ", ["low", "mid", "high"])
	wake_up_time = sanitize_input_string("Time you woke up: ")
	knuckle_shuffle = sanitize_input_string("Did you do the ting ... ", ["yes", "no"])
	deuce = sanitize_input_string("Are you regular :| ", ["yes", "no"])
	convo = sanitize_input_string("Who'd you talk to today :) ")
	exercise = sanitize_input_string("Exercise done: ", ["running", "weights", "tennis", "none"])
	youtube = sanitize_input_number("How much time did you spend on youtube (mins)? ")
	mood = sanitize_input_number("Last one g ... how productive were you today ", [1,2,3])
	notes = sanitize_input_string("Anything you want to get off ur chest :)) ")

	sheet = client.open('Intel').worksheet('Mood')
	today = datetime.now().strftime("%m/%d/%Y")
	insert_row = [str(today), mood, emotion1, emotion2, energy, wake_up_time, knuckle_shuffle, 
	deuce, convo, exercise, youtube, mood, notes]
	sheet.update(f'A{row_num}:M{row_num}', [insert_row])
	print("Updated Mood Sheet \n")
