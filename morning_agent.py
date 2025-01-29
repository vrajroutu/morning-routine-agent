import os
import time
import schedule
import requests
from datetime import datetime, timedelta
from typing import List, Dict

# Google Calendar imports
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# LangChain imports
from langchain.agents import AgentExecutor, initialize_agent, AgentType
from langchain.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
from langchain.tools import BaseTool

# Configuration constants
GOOGLE_SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
TODOIST_API_URL = "https://api.todoist.com/rest/v2/tasks"
NEWSAPI_URL = "https://newsapi.org/v2/top-headlines"
SONOS_BASE_URL = "http://localhost:5005"  # Update with your Sonos server details

class CalendarManager:
    """Handles Google Calendar authentication and event retrieval"""
    
    def __init__(self):
        self.creds = None
        self.service = None
        
    def authenticate(self):
        """Handle Google OAuth2 authentication flow"""
        if os.path.exists('token.json'):
            self.creds = Credentials.from_authorized_user_file('token.json', GOOGLE_SCOPES)

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', GOOGLE_SCOPES)
                self.creds = flow.run_local_server(port=0)
            
            with open('token.json', 'w') as token:
                token.write(self.creds.to_json())

        self.service = build('calendar', 'v3', credentials=self.creds)
    
    def get_todays_events(self) -> List[Dict]:
        """Retrieve today's calendar events"""
        if not self.service:
            self.authenticate()

        now = datetime.utcnow()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat() + 'Z'
        end_of_day = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0).isoformat() + 'Z'

        events_result = self.service.events().list(
            calendarId='primary',
            timeMin=start_of_day,
            timeMax=end_of_day,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        return [
            {
                'title': event.get('summary', 'No Title'),
                'time': event['start'].get('dateTime', event['start'].get('date')),
                'description': event.get('description', '')
            }
            for event in events_result.get('items', [])
        ]

class TodoistManager:
    """Handles Todoist task management"""
    
    def __init__(self):
        self.api_token = os.getenv('TODOIST_API_TOKEN')
        if not self.api_token:
            raise ValueError("TODOIST_API_TOKEN environment variable not set")

    def get_todays_tasks(self) -> List[Dict]:
        """Retrieve tasks due today"""
        headers = {'Authorization': f'Bearer {self.api_token}'}
        params = {'filter': 'today'}
        
        try:
            response = requests.get(TODOIST_API_URL, headers=headers, params=params)
            response.raise_for_status()
            return [
                {
                    'task': item.get('content'),
                    'due': item.get('due', {}).get('date'),
                    'priority': item.get('priority')
                }
                for item in response.json()
            ]
        except requests.exceptions.RequestException as e:
            print(f"Todoist API error: {str(e)}")
            return []

class NewsManager:
    """Handles news retrieval from NewsAPI"""
    
    def __init__(self):
        self.api_key = os.getenv('NEWSAPI_API_KEY')
        if not self.api_key:
            raise ValueError("NEWSAPI_API_KEY environment variable not set")

    def get_news(self, topic: str) -> List[Dict]:
        """Retrieve news articles for a specific topic"""
        params = {
            'apiKey': self.api_key,
            'q': topic,
            'pageSize': 5,
            'language': 'en'
        }
        
        try:
            response = requests.get(NEWSAPI_URL, params=params)
            response.raise_for_status()
            return [
                {
                    'title': article.get('title'),
                    'source': article.get('source', {}).get('name'),
                    'description': article.get('description'),
                    'url': article.get('url')
                }
                for article in response.json().get('articles', [])
            ]
        except requests.exceptions.RequestException as e:
            print(f"NewsAPI error: {str(e)}")
            return []

class SmartHomeTools:
    """Collection of smart home control tools"""
    
    @staticmethod
    def trigger_alarm(message: str) -> str:
        """Trigger alarm system (mock implementation)"""
        print(f"[ALARM] Triggered: {message}")
        return f"Alarm activated: {message}"

    @staticmethod
    def play_music(query: str) -> str:
        """Control Sonos music (mock implementation)"""
        print(f"[MUSIC] Playing: {query}")
        return f"Now playing: {query}"

class MorningRoutineAgent:
    """Main agent class handling the morning routine workflow"""
    
    def __init__(self):
        self.calendar = CalendarManager()
        self.todoist = TodoistManager()
        self.news = NewsManager()
        self.agent = self._initialize_agent()

    def _initialize_agent(self) -> AgentExecutor:
        """Initialize LangChain agent with tools"""
        tools = [
            BaseTool(
                name="get_calendar_events",
                func=lambda _: str(self.calendar.get_todays_events()),
                description="Get today's calendar events"
            ),
            BaseTool(
                name="get_todoist_tasks",
                func=lambda _: str(self.todoist.get_todays_tasks()),
                description="Get today's Todoist tasks"
            ),
            BaseTool(
                name="get_news_summary",
                func=lambda topic: str(self.news.get_news(topic)),
                description="Get news summary for a specific topic"
            ),
            BaseTool(
                name="trigger_alarm",
                func=SmartHomeTools.trigger_alarm,
                description="Trigger alarm system"
            ),
            BaseTool(
                name="play_music",
                func=SmartHomeTools.play_music,
                description="Play music on Sonos system"
            )
        ]

        llm = ChatOpenAI(
            temperature=0.3,
            model_name="gpt-3.5-turbo",
            openai_api_key=os.getenv('OPENAI_API_KEY')
        )

        system_message = SystemMessage(content=(
            "You are an advanced home assistant AI. Your morning routine includes:\n"
            "1. Triggering the wake-up alarm\n"
            "2. Providing news summary (technology and business)\n"
            "3. Reporting today's calendar events\n"
            "4. Listing Todoist tasks\n"
            "5. Starting morning music\n"
            "Respond in concise, natural language with emojis."
        ))

        return initialize_agent(
            tools=tools,
            llm=llm,
            agent=AgentType.OPENAI_FUNCTIONS,
            agent_kwargs={"system_message": system_message},
            verbose=True
        )

    def run_routine(self):
        """Execute the morning routine"""
        prompt = """Execute the full morning routine:
        1. Trigger the wake-up alarm
        2. Get technology and business news summaries
        3. Retrieve today's calendar events
        4. List today's Todoist tasks
        5. Start morning playlist
        Provide final summary in friendly tone."""
        
        try:
            response = self.agent.run(prompt)
            print("\n=== Morning Routine Complete ===")
            print(response)
        except Exception as e:
            print(f"Error running routine: {str(e)}")

def main():
    """Main execution and scheduling"""
    agent = MorningRoutineAgent()
    
    # Schedule daily at 7 AM
    schedule.every().day.at("07:00").do(agent.run_routine)
    print("Morning routine scheduler started. Waiting for 7 AM trigger...")

    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Validate required environment variables
    required_vars = ['OPENAI_API_KEY', 'TODOIST_API_TOKEN', 'NEWSAPI_API_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    main()
