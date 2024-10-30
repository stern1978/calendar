#!/usr/bin/python3

from __future__ import print_function
import httplib2
import os
import time
from datetime import datetime, timedelta

import googleapiclient.discovery as discovery
from oauth2client import client, tools
from oauth2client.file import Storage

from flask import Flask, render_template

# Constants
SCOPES = 'https://www.googleapis.com/auth/calendar.readonly'
CLIENT_SECRET_FILE = 'client_secret_google_calendar.json'
APPLICATION_NAME = 'Google Calendar - Raw Python'

app = Flask(__name__)

def get_credentials():
    """
    Fetches the user's Google Calendar API credentials.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
        
    credential_path = os.path.join(credential_dir, 'calendar-python-quickstart.json')
    store = Storage(credential_path)
    credentials = store.get()

    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        credentials = tools.run_flow(flow, store)
    
    return credentials

def fetch_calendar_ids(service):
    """
    Fetches the list of calendar IDs.
    """
    calendar_ids = []
    page_token = None

    while True:
        try:
            calendar_list = service.calendarList().list(pageToken=page_token).execute()
            calendar_ids.extend([entry['id'] for entry in calendar_list['items'] if '@gmail.com' in entry['id']])
            page_token = calendar_list.get('nextPageToken')
            if not page_token:
                break
        except Exception as e:
            print(f"Error fetching calendar list: {e}")
            time.sleep(1)
    
    return calendar_ids

def fetch_calendar_events(service, calendar_id, start_time):
    """
    Fetches upcoming events.
    """
    events = []
    try:
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=start_time,
            singleEvents=True,
            maxResults=10,
            orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])
    except Exception as e:
        print(f"Error fetching events from calendar {calendar_id}: {e}")
    
    return events

def calculate_time_difference(event_datetime):
    """
    Calculates the time difference between now and the event date.
    """
    now = datetime.now()
    delta = event_datetime - now

    months = delta.days // 30
    days = delta.days % 30
    hours = delta.seconds // 3600

    return months, days, hours

@app.route('/')
def index():
    """
    Main route for the Flask app.
    """
    calendar_data = []
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('calendar', 'v3', http=http)

    calendar_ids = fetch_calendar_ids(service)
    
    now = datetime.now().isoformat() + 'Z'
    today_date = datetime.now().date()
    formatted_today = datetime.now().strftime('%b %d')

    for calendar_id in calendar_ids:
        events = fetch_calendar_events(service, calendar_id, now)

        for event in events:
            summary = event.get('summary', 'No title')
            location = event.get('location', '')

            start_iso = event.get('start', {}).get('dateTime') or event.get('start', {}).get('date')
            if 'T' in start_iso:
                start_time_obj = datetime.strptime(start_iso[:19], '%Y-%m-%dT%H:%M:%S')
                start_time = start_time_obj.strftime('%I:%M %p')
                event_datetime = start_time_obj
            else:
                start_time = 'All Day'
                event_datetime = datetime.strptime(start_iso, '%Y-%m-%d')

            if event_datetime.date() < today_date:
                continue

            months, days, hours = calculate_time_difference(event_datetime)

            calendar_data.append([
                summary, location, start_time, event_datetime.strftime('%b %d'), 
                days, months, hours
            ])

    return render_template('calendar.html', calendar=calendar_data, today=formatted_today)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8014, debug=True)
