#!/usr/bin/python3

from __future__ import print_function
import httplib2
import os
import time

import googleapiclient.discovery as discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

from datetime import datetime

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None


SCOPES = 'https://www.googleapis.com/auth/calendar.readonly'
CLIENT_SECRET_FILE = 'client_secret_google_calendar.json'
APPLICATION_NAME = 'Google Calendar - Raw Python'
import datetime
from flask import Flask, render_template


app = Flask(__name__)
app.config.from_object(__name__)


def get_credentials():
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
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else:  # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        #print('Storing credentials to ' + credential_path)
    return credentials

 
@app.route('/')
def index():
    calendar = []
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    print(http)
    service = discovery.build('calendar', 'v3', http=http)

    page_token = None
    calendar_ids = []
    while True:
        try:
            calendar_list = service.calendarList().list(pageToken=page_token).execute()
            for calendar_list_entry in calendar_list['items']:
                if '@gmail.com' in calendar_list_entry['id']:
                    calendar_ids.append(calendar_list_entry['id'])
            page_token = calendar_list.get('nextPageToken')
            if not page_token:
                break
        except:
            time.sleep(1)
    end_date = datetime.datetime.utcnow().isoformat() + 'Z'
    today_iso = datetime.datetime.now()
    today = today_iso.strftime('%b %d')
    start_date_z = datetime.datetime.now().date()

    day_name = today_iso.strftime('%a')
    tomorrow_iso = today_iso + datetime.timedelta(days=1)
    tomorrow = tomorrow_iso.strftime('%b %d')
    week_iso = today_iso + datetime.timedelta(days=6)
    week = week_iso.strftime('%a')
    

    for calendar_id in calendar_ids:
        eventsResult = service.events().list(
            calendarId=calendar_id,
            singleEvents=True,
            timeMin = end_date,
            maxResults = 10,
            orderBy='startTime').execute()
        events = eventsResult.get('items', [])
        for event in events:
            summary = event['summary']
            try:
                location = event['location']
            except KeyError:
                location = ''
            try:
                start_iso = event['start']['dateTime']
                start_iso_slice = datetime.datetime.strptime(start_iso[slice(-6)], '%Y-%m-%dT%H:%M:%S')
                start_day_slice = datetime.datetime.strptime(start_iso[slice(-15)], '%Y-%m-%d').date()
                start_time = datetime.datetime.strptime(start_iso, '%Y-%m-%dT%H:%M:%S%z').strftime('%I:%M %p')
                start_date = datetime.datetime.strptime(start_iso, '%Y-%m-%dT%H:%M:%S%z').strftime('%b %d')
                start_day = datetime.datetime.strptime(start_iso, '%Y-%m-%dT%H:%M:%S%z').strftime('%a')
            except KeyError: #for all day events.
                start_iso = event['start']['date']
                start_iso_string = datetime.datetime.strptime(start_iso, '%Y-%m-%d').strftime('%Y-%m-%dT%H:%M:%S')
                start_iso_slice = datetime.datetime.strptime(start_iso_string, '%Y-%m-%dT%H:%M:%S')
                start_day_slice = datetime.datetime.strptime(start_iso, '%Y-%m-%d').date()
                start_time = 'All Day'
                start_date = datetime.datetime.strptime(start_iso, '%Y-%m-%d').strftime('%b %d')
                start_day = datetime.datetime.strptime(start_iso, '%Y-%m-%d').strftime('%a')

            try:
                days_till = start_day_slice-start_date_z
                days_till = str(days_till).strip(', 0:00:00')
                days_till = str(days_till).strip(' days')
                try:
                    days_till = int(days_till)
                except:
                    days_till = 0
                if days_till == 0:
                    start_date = 'Today'
                elif days_till == 1:
                    start_date = 'Tomorrow'
                elif days_till > 1 and days_till < 8:
                    start_date = start_day
                elif days_till > 7:
                    start_date
            except TypeError as e:
                print(e)
            except UnboundLocalError as e:
                print(e)
                days_till = 'error'
            
            calendar.append([summary, location, start_time, start_date, day_name, today, days_till])
    return render_template('calendar.html',calendar=calendar)


if __name__ == '__main__':
   get_credentials()
   app.run(host='0.0.0.0', port=8014, debug=True)