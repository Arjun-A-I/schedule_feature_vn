

import instructor
from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError
from typing import List, Literal
import json
import os
from dotenv import load_dotenv, find_dotenv
from cal import run
from datetime import datetime, date, timedelta

today = date.today()
now = datetime.now()
time_details = now.strftime("%H:%M:%S")

load_dotenv(find_dotenv())
api_key = os.getenv("OPENAI_API_KEY")

instructor_openai_client = instructor.from_openai(OpenAI(
    api_key=api_key,
    timeout=20000,
    max_retries=3,
    # temperature=0.4,
))

date_details = date.today().strftime("%B %d, %Y")
w = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
day = w[date.today().weekday()]


class GetTime(BaseModel):
    hours: Literal["00", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23"] = Field(default="00", description=f"From the timing of event extract the hours value in 24 hour format.Two digit Integer value between 00-23 accepted.Current time is {time_details}")
    minutes: Literal["00", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23", "24", "25", "26", "27", "28", "29", "30", "31", "32", "33", "34", "35", "36", "37", "38", "39", "40", "41", "42", "43", "44", "45", "46", "47", "48", "49", "50", "51", "52", "53", "54", "55", "56", "57", "58", "59"] = Field(default="00", description=f"From the timing of event extract the minutes value.Two digit Integer value between 00-59 accepted.. Current time is {time_details}")
    seconds: Literal["00"] = Field(default="00", description=f"Return 00")
    
class TimeExtract(BaseModel):
    date: str = Field(default=f"{today}", description=f"The date of the event if present in the text. It should be derived from phrases like 'next Monday', 'this Friday', etc. Current date is {today}. Return in YYYY-MM-DD format only. Other formats will be discarded")
    start_time: GetTime = Field(default=None, description="The start time of the event.")
    end_time:  GetTime = Field(default=None, description="The end time of the event.")


class TaskDetails(BaseModel):
    day: Literal['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday', 'NULL'] = Field(default="NULL", description="The day of the event if present in the summary.")
    event: str = Field(default="NULL", description="Title or summary of the event.")
    current_day: Literal['Yes', 'No'] = Field(default="No", description="The current day mentioned in the conversation.")
    successive_day: Literal['Yes', 'No'] = Field(default="No", description="The successive day mentioned in the conversation.")
    timeline: TimeExtract = Field(default=None, description="The time-related details of the event.")

class MultipleTaskData(BaseModel):
    tasks: List[TaskDetails]

def extract_event_details(conversation_summary: str) -> MultipleTaskData:
    completion = instructor_openai_client.chat.completions.create(
        model="gpt-4-turbo-preview",
        temperature=0.2,
        
        messages=[
            {"role": "user", "content": f"Please convert the following information into valid JSON representing the event details: {conversation_summary} specifically for assigning each task to google calender api."}
        ],
        response_model=MultipleTaskData
    )

    try:
        multiple_task_data = MultipleTaskData(**completion.model_dump())
        return multiple_task_data
    except ValidationError as e:
        print(f"Error extracting event details: {e}")
        return None




conversation_summary = f"""
Current details:{time_details}, {date_details}, {day}
Had a very hectic day with continuous classes from morning till evening.
Need to brainstorm ideas on building access Laravel tomorrow.
Must focus on finishing a project with a friend by this evening to send the mail.
Need to schedule a meeting with the dentist for next Friday.
Have to complete assignments for algorithm analysis by next Tuesday.
Exam starts on Monday.
"""

if "evening" in conversation_summary.lower():
    conversation_summary = conversation_summary.replace("evening", "16:00:00")
if "today" in conversation_summary:
    conversation_summary = conversation_summary.replace("today", today)
if "tomorrow" in conversation_summary:
    tmmr =  str(date.today() + timedelta(days=1))
    conversation_summary = conversation_summary.replace("tomorrow", tmmr )

if "morning" in conversation_summary.lower():
    conversation_summary = conversation_summary.replace("morning", "8:00:00")

if "noon" in conversation_summary.lower():
    conversation_summary = conversation_summary.replace("noon", "12:00:00")

multiple_task_data = extract_event_details(conversation_summary)

if multiple_task_data:
    print("JSON")
    print(json.dumps(multiple_task_data.dict(), indent=2))
    tasks = multiple_task_data.dict()["tasks"]
    print(tasks)
    print(len(tasks))

    for task in tasks:
        if task["timeline"]["date"] == "NULL":
            task["timeline"]["date"] = today
            print("Today", today)
        if task["timeline"]["start_time"] == "NULL":
            task["timeline"]["start_time"] = time_details
        if task["timeline"]["end_time"] == "NULL":
            task["timeline"]["end_time"] = (
                datetime.strptime(task["timeline"]["start_time"], "%H:%M:%S")
                + timedelta(hours=1)
            ).strftime("%H:%M:%S")
        date = (task["timeline"]["date"])
        print(date)
        print(task["event"])
        print(task["timeline"]["start_time"])
        print(task["timeline"]["end_time"])
        parsed_date = datetime.fromisoformat(date)

        start_time = (task["timeline"]["start_time"])
        end_time = (task["timeline"]["end_time"])

        parsed_start = datetime.strptime(start_time, "%H:%M:%S")

        # Combine the time and date
        combined_datetime_start = datetime(parsed_date.year, parsed_date.month, parsed_date.day, parsed_start.hour, parsed_start.minute, parsed_start.second)

        # Convert to ISO format
        start_time = combined_datetime_start.isoformat()

        parsed_end = datetime.strptime(end_time, "%H:%M:%S")

        # Combine the time and date
        combined_datetime_end = datetime(parsed_date.year, parsed_date.month, parsed_date.day, parsed_end.hour, parsed_end.minute, parsed_end.second)

        # Convert to ISO format
        end_time = combined_datetime_end.isoformat()

        run(summary=task["event"], start_time=start_time, end_time=end_time)
else:
    print("Failed to extract event details.")