import gspread
from google.oauth2.service_account import Credentials

def get_google_sheet(sheet_name, worksheet_name):
    creds = Credentials.from_service_account_file('referralsearchapp-66acbc64e9b3.json', scopes=[
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
])
    client = gspread.authorize(creds)
    sheet = client.open(sheet_name).worksheet(worksheet_name)
    return sheet.get_all_records()
