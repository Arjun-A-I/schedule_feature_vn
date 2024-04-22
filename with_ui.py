import streamlit as st
import instructor
from pydantic import BaseModel, Field
from typing import List
from openai import OpenAI
from dotenv import load_dotenv, find_dotenv
import os
from datetime import datetime, date, timedelta
import json
from gcalender.cal_setup import get_calendar_service
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def run(summary, start_time, end_time, description = "Automated by ..."):
  """Shows basic usage of the Google Calendar API.
  Prints the start and name of the next 10 events on the user's calendar.
  """
  creds = None
  # The file token.json stores the user's access and refresh tokens, and is
  # created automatically when the authorization flow completes for the first
  # time.
  if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
  # If there are no (valid) credentials available, let the user log in.
  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
    else:
      flow = InstalledAppFlow.from_client_secrets_file(
          "credentials.json", SCOPES
      )
      creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open("token.json", "w") as token:
      token.write(creds.to_json())

  try:
    service = build("calendar", "v3", credentials=creds)

    # Call the Calendar API
    # now = datetime.datetime.utcnow().isoformat() + "Z"  # 'Z' indicates UTC time
    # print("Getting the upcoming 10 events")
    # events_result = (
    #     service.events()
    #     .list(
    #         calendarId="primary",
    #         timeMin=now,
    #         maxResults=10,
    #         singleEvents=True,
    #         orderBy="startTime",
    #     )
    #     .execute()
    # )
    # events = events_result.get("items", [])

    # if not events:
    #   print("No upcoming events found.")
    #   return

    # # Prints the start and name of the next 10 events
    # for event in events:
    #   start = event["start"].get("dateTime", event["start"].get("date"))
    #   print(start, event["summary"])
    # calendar = {
    #   'summary': 'calendarSummary',
    #   'timeZone': 'America/Los_Angeles'
    # }

    

    # d = datetime.datetime.now().date() 
    # print(d)
    # tomorrow = datetime.datetime(d.year, d.month, d.day, 10)+datetime.timedelta(days=1)
    # start = tomorrow.isoformat()
    # end = (tomorrow + datetime.timedelta(hours=1)).isoformat()

    event_result = service.events().insert(calendarId='primary',
        body={
            "summary": summary,
            "description":description,
            "start": {"dateTime": start_time, "timeZone": 'Asia/Kolkata'},
            "end": {"dateTime": end_time, "timeZone": 'Asia/Kolkata'},
        }
    ).execute()

    print("created event")
    print("id: ", event_result['id'])
    print("summary: ", event_result['summary'])
    print("starts at: ", event_result['start']['dateTime'])
    print("ends at: ", event_result['end']['dateTime'])


  except HttpError as error:
    print(f"An error occurred: {error}")

  

today = date.today()
now = datetime.now()
hour = int(now.strftime("%H")) + 1
time_details = f"{hour}:00:00"

print("Today's date:", today)
print("Current time:", time_details)

# Define your desired output structure
class TimeV(BaseModel):
    hours: str = Field(default=str(hour), description="Hour of the event")
    minutes: str = Field(default="00", description="Minutes of the event")
    seconds: str = Field(default="00", description="Seconds of the event")

class TimeDetails(BaseModel):
    date: str = Field(default=today, description="Date of the event")
    start_time: TimeV = Field(default=TimeV(), description="Start time of the event")
    end_time: TimeV = Field(default=TimeV(), description="End time of the event")

class TaskDetails(BaseModel):
    eventname: str = Field(default="Event", description="Title or summary of the event")
    timeline: TimeDetails = Field(default=None, description="Date and time details")

class MultipleTaskData(BaseModel):
    tasks: List[TaskDetails]

def process_data(summary):
    # Load your OpenAI API key from a .env file
    load_dotenv(find_dotenv())
    api_key = os.getenv("OPENAI_API_KEY")

    # Patch the OpenAI client
    client = instructor.from_openai(OpenAI(
        api_key=api_key,
        timeout=20000,
        max_retries=3
    ))

    if "morning" in summary.lower():
        summary = summary.replace("morning", "8:00:00")
    if "noon" in summary.lower():
        summary = summary.replace("noon", "12:00:00")
    if "evening" in summary.lower():
        summary = summary.replace("evening", "16:00:00")
    if "today" in summary:
        summary = summary.replace("today", str(today))
    if "tomorrow" in summary:
        tmmr = str(date.today() + timedelta(days=1))
        summary = summary.replace("tomorrow", tmmr)

    user_info = client.chat.completions.create(
        model="gpt-3.5-turbo",
        response_model=MultipleTaskData,
        messages=[{"role": "user", "content": f"Please convert the following information into valid JSON representing the event details: {summary} specifically for assigning each task to google calender api."}],
    )

    result = json.dumps(user_info.model_dump(), indent=2)
    return result

def add_to_google_calendar(task):
    event = run(task['eventname'], task['timeline']['start_time'], task['timeline']['end_time'])
    return event

def display_event_buttons(data):
    if 'added_events' not in st.session_state:
        st.session_state['added_events'] = set()

    # Initialize all checkbox states in session_state before any checkbox widgets are created
    for i, task in enumerate(data["tasks"]):
        checkbox_id = f"add_{i}"
        if checkbox_id not in st.session_state:
            st.session_state[checkbox_id] = i in st.session_state['added_events']

    # Create checkboxes and update session_state based on interactions
    for i, task in enumerate(data["tasks"]):
        checkbox_id = f"add_{i}"
        current_value = st.session_state[checkbox_id]
        new_value = st.checkbox(f"Add '{task['eventname']}' to calendar", value=current_value, key=checkbox_id)
        
        if new_value != current_value:
            st.session_state[checkbox_id] = new_value
            if new_value:
                st.session_state['added_events'].add(i)
            else:
                st.session_state['added_events'].discard(i)

def main():
    st.title("Input and Submit Example")

    # Create an input field
    summary = st.text_area("Enter your summary:", """
    Current date 2024-04-13, current time 15:00:00
    I have a meeting with the team tomorrow at noon.
    I have a meeting with the team today at 5pm.
    Brainstorming session next Friday at 10am to 11am.
    I have to complete the project by next Tuesday.
    Exam starts on Monday morning.
    """)
    if "load_state" not in st.session_state:
        st.session_state.load_state=False
        
    # Create a submit button
    if st.button("Submit", key="submit_button") or st.session_state.load_state:
        st.session_state.load_state=True
        with st.spinner("Processing data..."):
            result = process_data(summary)

        # Parse the JSON data
        data = json.loads(result)

        # Display the buttons for each event
        display_event_buttons(data)

if __name__ == "__main__":
    main()