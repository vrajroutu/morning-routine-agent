import os
import time
import json
import requests
import asyncio
from typing import Dict, List
from dataclasses import dataclass
from queue import Queue
from threading import Thread

# Voice Interaction
import speech_recognition as sr
from gtts import gTTS
import pygame

# AI Components
from langchain.agents import Tool, AgentExecutor
from langchain.memory import ConversationBufferWindowMemory
from langchain.chat_models import ChatOpenAI
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma

# Home Automation
import phue  # Philips Hue
from pyharmony import harmony  # Logitech Harmony
import samsungtv  # Samsung Smart TV

@dataclass
class DeviceState:
    lights: Dict[str, bool]
    media: str
    climate: Dict[str, float]
    security: bool

class RealTimeHomeAgent:
    def __init__(self):
        self._init_voice()
        self._init_llm()
        self._init_iot_connections()
        self.command_queue = Queue()
        self.context_memory = Chroma(embedding_function=OpenAIEmbeddings())
        self.device_state = DeviceState({}, "off", {}, False)
        
    def _init_voice(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        pygame.mixer.init()
        
    def _init_llm(self):
        self.llm = ChatOpenAI(
            temperature=0.3,
            model_name="gpt-4",
            streaming=True
        )
        
        self.tools = [
            Tool(
                name="control_lights",
                func=self.control_lights,
                description="Control smart lights. Input: JSON with 'action'(on/off), 'room'(optional)"
            ),
            Tool(
                name="manage_climate",
                func=self.manage_climate,
                description="Adjust thermostat. Input: JSON with 'temp'(number), 'mode'(heat/cool/auto)"
            ),
            Tool(
                name="entertainment_system",
                func=self.control_entertainment,
                description="Control media systems. Input: JSON with 'action'(play/pause/volume), 'device'(tv/soundbar)"
            ),
            Tool(
                name="security_system",
                func=self.control_security,
                description="Arm/disarm security. Input: JSON with 'action'(arm/disarm)"
            ),
            Tool(
                name="context_memory",
                func=self.query_memory,
                description="Search past interactions. Input: natural language query"
            )
        ]
        
        self.memory = ConversationBufferWindowMemory(
            memory_key="chat_history",
            k=10
        )
        
        self.agent = AgentExecutor.from_agent_and_tools(
            agent=self._create_agent(),
            tools=self.tools,
            memory=self.memory,
            verbose=True
        )
        
    def _init_iot_connections(self):
        # Connect to Philips Hue Bridge
        self.hue_bridge = phue.Bridge(os.getenv('HUE_BRIDGE_IP'))
        self.hue_bridge.connect()
        
        # Connect to Harmony Hub
        self.harmony = harmony.Harmony(os.getenv('HARMONY_HUB_IP'))
        self.harmony.connect()
        
        # Connect to Samsung TV
        self.tv = samsungtv.SamsungTV(os.getenv('TV_IP'))
        
    def _create_agent(self):
        return initialize_agent(
            tools=self.tools,
            llm=self.llm,
            agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
            memory=self.memory,
            verbose=True
        )
        
    async def voice_listener(self):
        """Real-time voice input processing"""
        with self.microphone as source:
            print("Calibrating microphone...")
            self.recognizer.adjust_for_ambient_noise(source)
            
        while True:
            try:
                with self.microphone as source:
                    print("Listening...")
                    audio = self.recognizer.listen(source, timeout=5)
                    
                text = self.recognizer.recognize_google(audio)
                print(f"User: {text}")
                self.command_queue.put(text)
                
            except sr.WaitTimeoutError:
                continue
            except Exception as e:
                print(f"Voice error: {str(e)}")

    async def process_commands(self):
        """Process commands from queue"""
        while True:
            if not self.command_queue.empty():
                command = self.command_queue.get()
                response = await self.agent.arun(command)
                self.speak(response)
                self._update_context(command, response)
                
            await asyncio.sleep(0.1)

    def speak(self, text: str):
        """Text-to-speech output"""
        tts = gTTS(text=text, lang='en')
        tts.save("response.mp3")
        pygame.mixer.music.load("response.mp3")
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)

    def _update_context(self, query: str, response: str):
        """Store interaction in vector memory"""
        self.context_memory.add_texts([f"User: {query}\nAI: {response}"])

    def control_lights(self, command: str) -> str:
        """Control Philips Hue lights"""
        try:
            cmd = json.loads(command)
            lights = self.hue_bridge.get_light_objects('name')
            
            if 'room' in cmd:
                # Control entire room
                self.hue_bridge.set_group(cmd['room'], 'on' if cmd['action'] == 'on' else 'off')
            else:
                # Control individual lights
                for light in lights:
                    if light in cmd.get('lights', []):
                        lights[light].on = cmd['action'] == 'on'
            
            return f"Lights {cmd['action']} successful"
        except Exception as e:
            return f"Light control error: {str(e)}"

    def manage_climate(self, command: str) -> str:
        """Control smart thermostat (mock Nest API)"""
        try:
            cmd = json.loads(command)
            # Mock API call
            return f"Climate set to {cmd['temp']}°F in {cmd['mode']} mode"
        except:
            return "Climate control failed"

    def control_entertainment(self, command: str) -> str:
        """Control AV systems"""
        try:
            cmd = json.loads(command)
            if cmd['device'] == 'tv':
                if cmd['action'] == 'play':
                    self.tv.power_on()
                elif cmd['action'] == 'volume':
                    self.tv.set_volume(cmd['value'])
            return f"Entertainment system: {cmd['action']}"
        except:
            return "Entertainment control failed"

    def control_security(self, command: str) -> str:
        """Control security system"""
        try:
            cmd = json.loads(command)
            self.device_state.security = cmd['action'] == 'arm'
            return f"Security system {cmd['action']}ed"
        except:
            return "Security control failed"

    def query_memory(self, query: str) -> str:
        """Search conversation history"""
        docs = self.context_memory.similarity_search(query, k=3)
        return "\n".join([doc.page_content for doc in docs])

async def main():
    agent = RealTimeHomeAgent()
    
    # Start voice listener and command processor
    await asyncio.gather(
        agent.voice_listener(),
        agent.process_commands()
    )

if __name__ == "__main__":
    # Required environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = [
        'OPENAI_API_KEY',
        'HUE_BRIDGE_IP',
        'HARMONY_HUB_IP',
        'TV_IP'
    ]
    
    if not all(os.getenv(var) for var in required_vars):
        raise EnvironmentError("Missing required environment variables")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutting down...")
