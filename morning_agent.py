import os
import time
import schedule
import requests
from datetime import datetime, timedelta

# --- Google Calendar imports ---
import google.auth
import google.auth.transport.requests
from googleapiclient.discovery import build

# LangChain imports
from langchain.chat_models import ChatOpenAI
from langchain.agents import AgentExecutor, initialize_agent, AgentType
from langchain.schema import HumanMessage
from langchain.tools import BaseTool

###############################################################################
# HELPER FUNCTIONS FOR GOOGLE CALENDAR & TODOIST
###############################################################################

def get_today_events_from_google_calendar() -> list:
    """
    Fetches today's events from the primary Google Calendar.
    Returns a list of dicts: [{"title": ..., "time": ...}, ...]
    """
    # Assumes you have a 'credentials.json' or 'token.json' in the working directory
    # from the OAuth flow. Modify as needed.
    import os.path
    from google.oauth2.credentials import Credentials

    SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

    creds = None
    token_path = "token.json"
    creds_path = "credentials.json"

    # Load existing tokens
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    # If there are no valid creds available, let the user follow the OAuth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(google.auth.transport.requests.Request())
        else:
            # Full OAuth flow if needed:
            from google_auth_oauthlib.flow import InstalledAppFlow
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the creds for the next run
        with open(token_path, 'w') as token:
            token.write(creds.to_json())

    service = build("calendar", "v3", credentials=creds)

    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    time_min = today_start.isoformat() + "Z"  # 'Z' indicates UTC time
    time_max = today_end.isoformat() + "Z"

    events_result = service.events().list(
        calendarId="primary",
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,
        orderBy="startTime"
    ).execute()

    events = events_result.get("items", [])
    results = []
    for event in events:
        start = event.get("start", {})
        summary = event.get("summary", "No Title")
        # Attempt to parse a time
        start_time = start.get("dateTime", start.get("date", None))
        results.append({"title": summary, "time": start_time})
    return results


def get_todays_todoist_tasks() -> list:
    """
    Fetches tasks due today from Todoist.
    Returns a list of dicts: [{"task": ..., "due": ...}, ...]
    """
    token = os.environ.get("TODOIST_API_TOKEN")
    if not token:
        return [{"error": "Missing TODOIST_API_TOKEN"}]

    # We'll call the 'tasks' endpoint with a filter for 'today'
    # https://developer.todoist.com/rest/v2/#get-active-tasks
    url = "https://api.todoist.com/rest/v2/tasks"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"filter": "today"}  # tasks due 'today'
    resp = requests.get(url, headers=headers, params=params)
    if resp.status_code != 200:
        return [{"error": f"Todoist API error: {resp.text}"}]

    data = resp.json()  # list of tasks
    results = []
    for item in data:
        content = item.get("content")
        due_date = item.get("due", {}).get("date")
        results.append({"task": content, "due": due_date})
    return results


###############################################################################
# TOOLS
###############################################################################

class AlarmTool(BaseTool):
    """
    Triggers an alarm or Alexa routine. Placeholder uses simple print statements,
    but you can adapt to your real system.
    """
    name = "alarm_tool"
    description = (
        "Use this to ring the alarm. Input should be a short string describing the event "
        "like 'morning alarm'. The output will confirm if the alarm triggered."
    )

    def _run(self, query: str) -> str:
        print("[AlarmTool] Triggered the alarm (placeholder).")
        # Example or placeholder call:
        # requests.post("https://my-alarm-device.com/trigger", json={"reason": query})
        return "Alarm sounded successfully."

    async def _arun(self, query: str) -> str:
        raise NotImplementedError("AlarmTool does not support async")


class FetchNewsTool(BaseTool):
    """
    A tool to fetch news headlines from NewsAPI.org for a given topic.
    Returns up to 5 articles in JSON-ish format.
    """
    name = "fetch_news"
    description = (
        "Use this to fetch the latest news headlines about a given topic. "
        "Input should be a string specifying topics or keywords, e.g., 'stock market', 'politics'. "
        "Output is JSON-like text with article info."
    )

    def _run(self, query: str) -> str:
        api_key = os.environ.get("NEWSAPI_API_KEY")
        if not api_key:
            return "Error: Missing NEWSAPI_API_KEY environment variable."

        url = "https://newsapi.org/v2/top-headlines"
        params = {
            "apiKey": api_key,
            "q": query,
            "language": "en",
            "pageSize": 5
        }
        resp = requests.get(url, params=params)
        if resp.status_code != 200:
            return f"Error from NewsAPI: {resp.text}"

        data = resp.json()
        articles = data.get("articles", [])
        return str(articles)

    async def _arun(self, query: str) -> str:
        raise NotImplementedError("FetchNewsTool does not support async")


class SummarizeTextTool(BaseTool):
    """
    Summarizes text using the LLM.
    """
    name = "summarize_text"
    description = (
        "Use this to summarize any text input. "
        "Input should be a long string. Output will be a short summary."
    )

    def _run(self, text: str) -> str:
        llm = ChatOpenAI(
            temperature=0.3,
            model_name="gpt-3.5-turbo",
            openai_api_key=os.environ.get("OPENAI_API_KEY", ""),
        )
        messages = [
            HumanMessage(
                content=(
                    "Please summarize the following text in a concise, conversational style:\n\n"
                    f"{text}\n\nSummary:"
                )
            )
        ]
        response = llm(messages)
        return response.content.strip()

    async def _arun(self, text: str) -> str:
        raise NotImplementedError("SummarizeTextTool does not support async")


class StartMusicTool(BaseTool):
    """
    Turns on music in the hallway via Sonos HTTP API (placeholder).
    Node-Sonos-HTTP-API is typical at: http://<sonos-server>:5005/<ROOM>/play/<URI or search>
    """
    name = "start_music"
    description = (
        "Use this to start music in the hallway. Input can be a short string like 'play jazz' or 'play morning playlist'."
    )

    def _run(self, query: str) -> str:
        # Example usage for node-sonos-http-api:
        # SONOS_SERVER = "http://localhost:5005"
        # HALLWAY_ROOM = "Hallway"
        # search_term = query.replace(" ", "%20")
        # url = f"{SONOS_SERVER}/{HALLWAY_ROOM}/say/{search_term}"
        # Or play from a favorite or station:
        # url = f"{SONOS_SERVER}/{HALLWAY_ROOM}/musicsearch/spotify/album:{search_term}"
        #
        # We'll just print for example:
        print("[StartMusicTool] Attempting to start Sonos hallway music:", query)
        return f"Sonos hallway music started with: {query}"

    async def _arun(self, query: str) -> str:
        raise NotImplementedError("StartMusicTool does not support async")


class CalendarTool(BaseTool):
    """
    Fetches today's Google Calendar events.
    """
    name = "calendar_tool"
    description = (
        "Use this to retrieve a list of today's calendar events. "
        "Input should be 'get my meetings today'. Output: JSON or text about events."
    )

    def _run(self, query: str) -> str:
        events = get_today_events_from_google_calendar()
        return str(events)

    async def _arun(self, query: str) -> str:
        raise NotImplementedError("CalendarTool does not support async")


class TasksTool(BaseTool):
    """
    Fetches today's tasks from Todoist.
    """
    name = "tasks_tool"
    description = (
        "Use this to retrieve a list of tasks due today from Todoist. "
        "Input should be 'get my tasks'. Output: JSON or text about tasks."
    )

    def _run(self, query: str) -> str:
        tasks = get_todays_todoist_tasks()
        return str(tasks)

    async def _arun(self, query: str) -> str:
        raise NotImplementedError("TasksTool does not support async")

###############################################################################
# BUILD AGENT
###############################################################################

def build_agent() -> AgentExecutor:
    """
    Create an agent that:
      1) Triggers an alarm
      2) Fetches & summarizes Stock Market + Politics news
      3) Retrieves today's Google Calendar events
      4) Retrieves today's Todoist tasks
      5) Starts Sonos music in the hallway
    Then returns a final summary to the user.
    """

    # Tools
    alarm_tool = AlarmTool()
    fetch_tool = FetchNewsTool()
    summarize_tool = SummarizeTextTool()
    music_tool = StartMusicTool()
    calendar_tool = CalendarTool()
    tasks_tool = TasksTool()

    tools = [
        alarm_tool, fetch_tool, summarize_tool,
        music_tool, calendar_tool, tasks_tool
    ]

    # LLM
    llm = ChatOpenAI(
        temperature=0.0,
        model_name="gpt-3.5-turbo",  # or "gpt-4"
        openai_api_key=os.environ.get("OPENAI_API_KEY", "")
    )

    system_message = (
        "You are a helpful home-assistant agent. You have the following tools:\n"
        " - alarm_tool: ring the alarm\n"
        " - fetch_news: get news headlines\n"
        " - summarize_text: summarize text\n"
        " - start_music: start music in the hallway (Sonos)\n"
        " - calendar_tool: get today's Google Calendar events\n"
        " - tasks_tool: get today's Todoist tasks\n\n"
        "When asked to run the 'morning routine' you should:\n"
        " 1) Trigger the alarm.\n"
        " 2) Fetch news about 'stock market' and 'politics' (fetch_news).\n"
        " 3) Summarize that news (summarize_text).\n"
        " 4) Retrieve today's Google Calendar events (calendar_tool).\n"
        " 5) Retrieve today's Todoist tasks (tasks_tool).\n"
        " 6) Start Sonos music in the hallway (start_music), e.g. 'play morning playlist'.\n"
        "Then provide a final summary of what you did, including any relevant details (events, tasks, news highlights)."
        "Stop after completing these steps.\n"
    )

    # Build the agent
    agent = initialize_agent(
        tools=tools,
        llm=llm,
        agent=AgentType.OPENAI_FUNCTIONS,  # or ZERO_SHOT_REACT_DESCRIPTION
        verbose=True,
        system_message=system_message,
    )
    return agent


###############################################################################
# SCHEDULING
###############################################################################

def run_morning_routine(agent: AgentExecutor):
    """
    The function the schedule calls at 07:00 daily.
    We simply pass 'Please run morning routine.' to the agent,
    which orchestrates the steps via Tools.
    """
    user_message = "Please run morning routine."
    response = agent.run(user_message)
    print("\n=== Final Agent Response ===")
    print(response)

def main():
    agent = build_agent()

    # Schedule daily at 07:00
    schedule.every().day.at("07:00").do(run_morning_routine, agent=agent)

    print("Scheduled the agent to run every day at 07:00.")

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
    
