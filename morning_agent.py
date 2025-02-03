import os
import time
import schedule
import requests
from datetime import datetime, timedelta
from typing import List, Dict
import hashlib
import json
from typing import Optional

# Blockchain Implementation
class Block:
    """Basic blockchain block structure"""
    def __init__(self, index: int, timestamp: float, data: dict, previous_hash: str):
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.nonce = 0
        self.hash = self.calculate_hash()

    def calculate_hash(self) -> str:
        """Calculate SHA-256 hash of block contents"""
        block_string = json.dumps({
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce
        }, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def mine_block(self, difficulty: int):
        """Proof-of-work mining mechanism"""
        while self.hash[:difficulty] != '0' * difficulty:
            self.nonce += 1
            self.hash = self.calculate_hash()

class BlockchainManager:
    """Manages blockchain operations for security auditing"""
    def __init__(self, difficulty: int = 4):
        self.chain: List[Block] = []
        self.difficulty = difficulty
        self.initialize_chain()

    def initialize_chain(self):
        """Create genesis block if chain is empty"""
        if not self.chain:
            genesis_block = Block(0, time.time(), {"message": "Genesis Block"}, "0")
            genesis_block.mine_block(self.difficulty)
            self.chain.append(genesis_block)

    def add_block(self, data: dict) -> Block:
        """Add new block to the chain with validation"""
        last_block = self.chain[-1]
        new_block = Block(
            index=len(self.chain),
            timestamp=time.time(),
            data=data,
            previous_hash=last_block.hash
        )
        new_block.mine_block(self.difficulty)
        self.chain.append(new_block)
        return new_block

    def validate_chain(self) -> bool:
        """Verify blockchain integrity"""
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i-1]

            if current_block.hash != current_block.calculate_hash():
                return False
            if current_block.previous_hash != previous_block.hash:
                return False
        return True

    def save_chain(self, filename: str = "blockchain.json"):
        """Persist blockchain to file"""
        chain_data = [{
            "index": block.index,
            "timestamp": block.timestamp,
            "data": block.data,
            "previous_hash": block.previous_hash,
            "nonce": block.nonce,
            "hash": block.hash
        } for block in self.chain]
        
        with open(filename, 'w') as f:
            json.dump(chain_data, f, indent=2)

    def load_chain(self, filename: str = "blockchain.json"):
        """Load blockchain from file"""
        try:
            with open(filename, 'r') as f:
                chain_data = json.load(f)
                
            self.chain = [
                Block(
                    index=item['index'],
                    timestamp=item['timestamp'],
                    data=item['data'],
                    previous_hash=item['previous_hash']
                ) for item in chain_data
            ]
            # Restore computed properties
            for i, block in enumerate(self.chain):
                block.nonce = chain_data[i]['nonce']
                block.hash = chain_data[i]['hash']
                
        except FileNotFoundError:
            self.initialize_chain()

class EnhancedSmartHomeTools(SmartHomeTools):
    """Smart home tools with blockchain logging"""
    def __init__(self, blockchain: BlockchainManager):
        self.blockchain = blockchain

    def trigger_alarm(self, message: str) -> str:
        result = super().trigger_alarm(message)
        self.blockchain.add_block({
            "action": "trigger_alarm",
            "message": message,
            "status": "executed"
        })
        return result

    def play_music(self, query: str) -> str:
        result = super().play_music(query)
        self.blockchain.add_block({
            "action": "play_music",
            "query": query,
            "status": "executed"
        })
        return result

class SecureMorningRoutineAgent(MorningRoutineAgent):
    """Enhanced agent with blockchain security features"""
    def __init__(self):
        self.blockchain = BlockchainManager()
        self.blockchain.load_chain()
        super().__init__()

    def _initialize_agent(self) -> AgentExecutor:
        """Initialize agent with secure tools"""
        # Create secure tools with blockchain integration
        tools = [
            BaseTool(
                name="get_calendar_events",
                func=self._secure_get_calendar_events,
                description="Get today's calendar events"
            ),
            BaseTool(
                name="get_todoist_tasks",
                func=self._secure_get_todoist_tasks,
                description="Get today's Todoist tasks"
            ),
            BaseTool(
                name="get_news_summary",
                func=self._secure_get_news_summary,
                description="Get news summary for a specific topic"
            ),
            BaseTool(
                name="trigger_alarm",
                func=EnhancedSmartHomeTools(self.blockchain).trigger_alarm,
                description="Trigger alarm system"
            ),
            BaseTool(
                name="play_music",
                func=EnhancedSmartHomeTools(self.blockchain).play_music,
                description="Play music on Sonos system"
            )
        ]

        # Add blockchain validation to system message
        system_message = SystemMessage(content=(
            "You are an advanced secure home assistant AI. Additional security features:\n"
            "1. All actions are logged to an immutable blockchain\n"
            "2. Data integrity is verified through cryptographic hashing\n"
            "3. Full audit trail of all operations\n"
            "Original morning routine functionality remains the same but now with enhanced security."
        ))

        llm = ChatOpenAI(
            temperature=0.3,
            model_name="gpt-3.5-turbo",
            openai_api_key=os.getenv('OPENAI_API_KEY')
        )

        return initialize_agent(
            tools=tools,
            llm=llm,
            agent=AgentType.OPENAI_FUNCTIONS,
            agent_kwargs={"system_message": system_message},
            verbose=True
        )

    def _secure_get_calendar_events(self, _: Optional[str] = None) -> str:
        """Get calendar events with blockchain verification"""
        events = self.calendar.get_todays_events()
        self.blockchain.add_block({
            "action": "get_calendar_events",
            "data_hash": hashlib.sha256(str(events).encode()).hexdigest(),
            "entries": len(events)
        })
        return str(events)

    def _secure_get_todoist_tasks(self, _: Optional[str] = None) -> str:
        """Get Todoist tasks with blockchain verification"""
        tasks = self.todoist.get_todays_tasks()
        self.blockchain.add_block({
            "action": "get_todoist_tasks",
            "data_hash": hashlib.sha256(str(tasks).encode()).hexdigest(),
            "entries": len(tasks)
        })
        return str(tasks)

    def _secure_get_news_summary(self, topic: str) -> str:
        """Get news summary with blockchain verification"""
        news = self.news.get_news(topic)
        self.blockchain.add_block({
            "action": "get_news_summary",
            "topic": topic,
            "data_hash": hashlib.sha256(str(news).encode()).hexdigest(),
            "articles": len(news)
        })
        return str(news)

    def run_routine(self):
        """Execute the secure morning routine"""
        try:
            if not self.blockchain.validate_chain():
                raise SecurityError("Blockchain integrity compromised!")
            
            super().run_routine()
            
            # Finalize and save blockchain
            self.blockchain.add_block({
                "action": "routine_complete",
                "status": "success",
                "timestamp": datetime.now().isoformat()
            })
            self.blockchain.save_chain()
            
        except Exception as e:
            self.blockchain.add_block({
                "action": "routine_error",
                "error": str(e),
                "status": "failed"
            })
            self.blockchain.save_chain()
            raise

class SecurityError(Exception):
    """Custom security exception"""
    pass

# Update main function
def main():
    """Main execution with security checks"""
    agent = SecureMorningRoutineAgent()
    
    # Add blockchain integrity check to schedule
    schedule.every().hour.do(lambda: 
        print("Blockchain valid:", agent.blockchain.validate_chain())
    )
    
    schedule.every().day.at("07:00").do(agent.run_routine)
    print("Secure morning routine scheduler started...")

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
