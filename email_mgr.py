from __future__ import print_function
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def main():
    """Shows basic usage of the Gmail API.
    Lists the user's Gmail labels.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'jarvis_client.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('gmail', 'v1', credentials=creds)

    # Call the Gmail API
    # request a list of all the messages
    # can limit results with : maxResults=XX
    query = "newer_than:2d"
    senders_dict = {}
    result = service.users().messages().list(userId='me', q=query, labelIds=['UNREAD']).execute()
    messages = result.get('messages', [])

    if not messages or len(messages) == 0:
        print('No messages :)')
    else:
        print(f"You have {len(messages)} emails in shaurya.sanghvi@gmail.com")
        dashed_line = "-" * 60
        print(f"{dashed_line :^110}")
        #Iterate through message ids and get senders for each email
        for message in messages:
            # msg = service.users().messages().get(userId='me', id=message['id']).execute()
            # print(msg['snippet'] + "\n")
            messageheader= service.users().messages().get(userId='me', id=message['id'], format="full", metadataHeaders=None).execute()
            headers=messageheader["payload"]["headers"]
            sender= [i['value'] for i in headers if i["name"]=="From"][0]
            senders_dict[sender] = senders_dict.get(sender, 0) + 1
        #Format printing of sender dictionary (sorted [desc])
        print(f"{'Sender' :^90} {'Num Emails in last 2 days' :^10}")
        for k in sorted(senders_dict, key=senders_dict.get, reverse=True):
            print(f"{k[:90] :<90} {senders_dict[k] :>10}")
        print(f"{dashed_line :^110}")

    # print("Seconds taken: ", after_sorting - email_cnt) : getting senders for each email and sorting takes 5 seconds

    # same logic applied to gmail-deemed important messages
    import_query = "in:inbox is:important"
    important_emails = service.users().messages().list(userId='me', q=import_query, labelIds=['UNREAD']).execute()
    important_messages = important_emails.get('messages', [])

    if not important_messages or len(important_messages) == 0:
            print('No important messages :)')
    else:
        print(f"You have {len(important_messages)} important emails")
        print(f"{dashed_line :^110}")
        print(f"{'Sender' :^30} {'Subject' :^30} {'Snippet' :>30}")
        #Iterate through message ids and get senders for each email
        for message in important_messages:
            full_msg= service.users().messages().get(userId='me', id=message['id'], format="full", metadataHeaders=None).execute()
            imp_headers = full_msg["payload"]["headers"]
            sender = ""
            subject = ""
            for i in imp_headers:
                if i["name"] == "From":
                    sender = i['value']
                elif i["name"] == "Subject":
                    subject = i['value']
            snippet = full_msg['snippet']
            print(f"{sender[:30] :<30} {' ':^10} {subject[:30] :^30} {' ':^10} {snippet[:30] :>30}")
        print(f"{dashed_line :^110}")




if __name__ == '__main__':
    main()