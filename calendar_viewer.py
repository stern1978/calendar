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
    Fetches the user's Google Calendar API credentials, 
    authorizing the user if necessary and storing the credentials locally.
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
    Fetches the list of calendar IDs from the user's account that are associated with a Gmail address.
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
    Fetches the upcoming events from a specified calendar starting from the given time.
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

@app.route('/')
def index():
    """
    Main route for the Flask app. Fetches calendar events and renders them in the template.
    """
    calendar_data = []
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('calendar', 'v3', http=http)

    calendar_ids = fetch_calendar_ids(service)
    
    now = datetime.utcnow().isoformat() + 'Z'  # Time in UTC format
    today_date = datetime.now().date()

    for calendar_id in calendar_ids:
        events = fetch_calendar_events(service, calendar_id, now)

        for event in events:
            summary = event.get('summary', 'No title')
            location = event.get('location', '')

            # Parse start time
            start_iso = event.get('start', {}).get('dateTime') or event.get('start', {}).get('date')
            if 'T' in start_iso:  # Event has a specific start time
                start_time_obj = datetime.strptime(start_iso[:19], '%Y-%m-%dT%H:%M:%S')
                start_time = start_time_obj.strftime('%I:%M %p')
                start_date = start_time_obj.strftime('%b %d')
                start_day = start_time_obj.strftime('%a')
            else:  # All day event
                start_time = 'All Day'
                start_date = datetime.strptime(start_iso, '%Y-%m-%d').strftime('%b %d')
                start_day = datetime.strptime(start_iso, '%Y-%m-%d').strftime('%a')

            # Days until the event
            event_date = datetime.strptime(start_iso[:10], '%Y-%m-%d').date()

            # Skip events that have already passed
            if event_date < today_date:
                continue

            days_until = (event_date - today_date).days

            if days_until == 0:
                start_date = 'Today'
            elif days_until == 1:
                start_date = 'Tomorrow'
            elif 1 < days_until < 8:
                start_date = start_day
            
            calendar_data.append([summary, location, start_time, start_date, days_until])

    return render_template('calendar.html', calendar=calendar_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8014, debug=True)
