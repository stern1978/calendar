#!/usr/bin/python3

from __future__ import print_function
import httplib2
import os
import time
from datetime import datetime, timedelta
from calendar import monthrange

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
    now = datetime.now()
    delta = event_datetime - now

    if delta.total_seconds() <= 0:
        return "Now", 0, 0, 0  # Special flag indicating the event is happening now

    months = 0
    days = delta.days
    hours = delta.seconds // 3600
    minutes = (delta.seconds % 3600) // 60

    current_date = now
    while days >= monthrange(current_date.year, current_date.month)[1]:
        days_in_month = monthrange(current_date.year, current_date.month)[1]
        months += 1
        days -= days_in_month
        current_date = (current_date.replace(year=current_date.year + 1, month=1) if current_date.month == 12 
                        else current_date.replace(month=current_date.month + 1))

    return months, days, hours, minutes

def fetch_event_end_time(event):
    """
    Fetches the end time of an event.
    """
    end_iso = event.get('end', {}).get('dateTime') or event.get('end', {}).get('date')
    if 'T' in end_iso:
        end_time_obj = datetime.strptime(end_iso[:19], '%Y-%m-%dT%H:%M:%S')
    else:
        end_time_obj = datetime.strptime(end_iso, '%Y-%m-%d')
    
    return end_time_obj

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

            end_time_obj = fetch_event_end_time(event)  # Get the end time

            # Remove past events
            if end_time_obj < datetime.now():
                try:
                    service.events().delete(calendarId=calendar_id, eventId=event['id']).execute()
                    print(f"Deleted past event: {summary}")
                except Exception as e:
                    print(f"Error deleting event {summary}: {e}")
                continue  # Skip adding this event to calendar_data

            if event_datetime.date() < today_date:
                continue

            time_diff = calculate_time_difference(event_datetime)

            if time_diff[0] == "Now":
                calendar_data.append([summary, location, start_time, event_datetime.strftime('%b %d'), "Now"])
            else:
                months, days, hours, minutes = time_diff
                calendar_data.append([
                    summary, location, start_time, event_datetime.strftime('%b %d'), 
                    days, months, hours, minutes
                ])

    return render_template('calendar.html', calendar=calendar_data, today=formatted_today)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8014, debug=True)
