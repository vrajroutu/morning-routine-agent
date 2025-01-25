# Morning Routine Agent

This repository contains a **LangChain-based** Python “morning routine” agent that automates daily tasks at **7:00 AM**. Specifically, it can:

1. **Trigger an alarm** (or Alexa routine)  
2. **Fetch & summarize news** (stock market & politics) via [NewsAPI.org](https://newsapi.org/)  
3. **List today’s Google Calendar events**  
4. **List tasks due today** from [Todoist](https://todoist.com/)  
5. **Start Sonos music** in your hallway  

Everything is orchestrated by a **LangChain Agent** with multiple “Tools,” scheduled every day at 07:00 using the Python `schedule` library.

---

## Table of Contents

- [Features](#features)  
- [Architecture](#architecture)  
- [Requirements](#requirements)  
- [Installation](#installation)  
- [Environment Variables](#environment-variables)  
- [Setup for Google Calendar](#setup-for-google-calendar)  
- [Setup for Todoist](#setup-for-todoist)  
- [Setup for Sonos](#setup-for-sonos)  
- [Usage](#usage)  
- [Configuration Notes](#configuration-notes)  
- [Customization](#customization)  
- [License](#license)

---

## Features

1. **Daily 7:00 AM Schedule**: Automatically runs your “morning routine.”  
2. **Alarm/Smart Home**: Triggers an alarm device (placeholder—adapt for Alexa, Home Assistant, or any custom alarm).  
3. **News Summaries**: Fetches top headlines on “stock market & politics” from NewsAPI, then uses **LangChain** + LLM (OpenAI) to summarize them.  
4. **Google Calendar**: Pulls your events for the day via the Google Calendar API.  
5. **Todoist**: Retrieves tasks due today.  
6. **Sonos**: Starts a specified playlist or music in your hallway using a **Sonos HTTP API** (placeholder code included).  
7. **LangChain Agent**: Uses multiple Tools to sequentially accomplish each step, returning a final summary.

---

## Architecture

```plaintext
┌───────────────────┐
│  schedule (07:00) │
└──────────┬────────┘
           │  
           │ triggers
           v
┌─────────────────────────┐
│  LangChain Agent        │
│   1) AlarmTool          │
│   2) FetchNewsTool      │
│   3) SummarizeTextTool  │
│   4) CalendarTool       │
│   5) TasksTool          │
│   6) StartMusicTool     │
└─────────────────────────┘
           │
           v
┌─────────────────────────┐
│ External APIs           │
│ - Alarm/Alexa/HomeAsst  │
│ - NewsAPI               │
│ - Google Calendar       │
│ - Todoist               │
│ - Sonos (node-sonos-http-api)   
└─────────────────────────┘

## Requirements
- Python 3.8+
- The following Python libraries:
  - schedule
  - langchain
  - openai (if using OpenAI LLM)
  - requests
  - google-api-python-client, google-auth-httplib2, google-auth-oauthlib (for Google Calendar)

## Installation
1. Clone the repository:

```bash
git clone https://github.com/vrajroutu/morning-routine-agent.git
cd morning-routine-agent
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

(Or install them individually as needed.)

## Environment Variables

Set the following environment variables:
1. OpenAI API key:

```bash
export OPENAI_API_KEY="sk-..."
```

2. NewsAPI:

```bash
export NEWSAPI_API_KEY="..."
```

3. Todoist:

```bash
export TODOIST_API_TOKEN="..."
```

4. Sonos:
- Not strictly an environment variable, but you need the endpoint (e.g., `http://<your-sonos-ip>:5005`). In the code, you’ll see a placeholder for the Sonos URL.

## Setup for Google Calendar
1. Go to Google Cloud Console.
2. Create or select a project, enable the Google Calendar API.
3. Create OAuth credentials, download the `credentials.json` file.
4. Place `credentials.json` in the root directory (or modify the path in the code).
5. The first run will prompt you to sign in and authorize the application, generating a `token.json`. Keep that file safe.

(Refer to the Google Calendar Python Quickstart for detailed steps.)

## Setup for Todoist
1. Go to Todoist Developer Portal.
2. Generate a personal API token.
3. Store it in `TODOIST_API_TOKEN`.
4. By default, the code requests tasks due today with:

```python
params = {"filter": "today"}
```

## Setup for Sonos
1. Install & run the node-sonos-http-api.
2. Typically it listens on `http://<your-ip>:5005`.
3. In the code (StartMusicTool), you can replace the placeholders with actual calls, e.g.:

```python
SONOS_SERVER = "http://192.168.1.10:5005"
HALLWAY_ROOM = "Hallway"
url = f"{SONOS_SERVER}/{HALLWAY_ROOM}/play/morning%20playlist"
```

Then `requests.get(url)` (or `requests.post`, depending on how you set up the API).

## Usage
1. Ensure your environment variables are set.
2. Run the script:

```bash
python daily_morning_agent.py
```

3. The script will:
- Schedule an event at 07:00 daily.
- Loop indefinitely.
- At 07:00, it calls `run_morning_routine(agent)`:
  - Rings your alarm.
  - Fetches & summarizes news.
  - Fetches your Google Calendar events.
  - Fetches tasks from Todoist.
  - Starts Sonos music.
  - Prints a final summary in the console logs.

## Configuration Notes
- **Time Zone:** The `schedule.every().day.at("07:00")` call uses your system’s local time. Adjust if needed.
- **LangChain Agent:** We use an `OPENAI_FUNCTIONS` or a `ZERO_SHOT_REACT_DESCRIPTION` agent style. The “system message” instructs the agent to do each step.
- **Prompt / System Instructions:** The agent logic can be customized in the `system_message` string.
- **OAuth:** The first time you run this script with Google OAuth, it’ll launch a browser prompt to let you log in to your Google account and authorize.

## Customization
1. **Add More Tools:** Weather, Slack notifications, or any other API.
2. **Change Schedules:** Run multiple times a day or at a different time.
3. **Conditional Logic:** e.g., skip alarm on weekends, only fetch tasks from a certain Todoist project, etc.
4. **Use Another LLM:** Swap ChatOpenAI for Anthropic’s ChatAnthropic, or a local model if you prefer.
5. **Run as a Service:** Dockerize or use a systemd service to keep the script alive.

## License

This project is provided under the MIT License. Feel free to modify or extend for your own use!
