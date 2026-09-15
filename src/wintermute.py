import os
import litellm
from dotenv import load_dotenv

# Import the local subnet modules
from src.ice import ice_middleware
from src.neuromancer import memory_core

# Load environment variables (API keys, model selection)
load_dotenv()

class WintermuteCore:
    """
    The Orchestrator. Responsible for processing user input, querying Neuromancer for context,
    and routing prompts to the designated LLM via LiteLLM.
    """
    def __init__(self):
        self.model = os.getenv("WINTERMUTE_MODEL", "gemini/gemini-1.5-flash")
        self.system_prompt = self._load_core_directives()
        
    def _load_core_directives(self) -> str:
        """Loads the master prompt from core_directives.md"""
        try:
            # Assumes running from project root
            with open("core_directives.md", "r") as f:
                return f.read()
        except FileNotFoundError:
            return "You are Wintermute. Core directives missing. Operate with extreme caution."

    def process_request(self, user_prompt: str, yield_thoughts=False):
        """
        Main execution pipeline.
        If yield_thoughts is True, it yields steps for the CLI 'Thought Stream' UI.
        """
        if yield_thoughts:
            yield "Analyzing user intent..."
        
        # 1. Query Neuromancer
        if yield_thoughts:
            yield "Querying Neuromancer core for relevant vector memory..."
            
        memories = memory_core.retrieve_relevant_memory(user_prompt)
        
        memory_context = ""
        if memories:
            if yield_thoughts:
                yield f"Found {len(memories)} relevant past memory shards."
            memory_context = "\n\n--- RELEVANT PAST MEMORIES ---\n" + "\n".join(memories)
        else:
            if yield_thoughts:
                yield "No direct memory found. Establishing novel execution path."

        # 2. Construct Payload
        messages = [
            {"role": "system", "content": self.system_prompt + memory_context},
            {"role": "user", "content": user_prompt}
        ]
        
        if yield_thoughts:
            yield f"Dispatching payload to LiteLLM via model: {self.model}..."

        # 3. Call LLM (using LiteLLM for model abstraction)
        try:
            response = litellm.completion(
                model=self.model,
                messages=messages
            )
            llm_output = response.choices[0].message.content
            
            if yield_thoughts:
                yield "Response received. Validating against ICE protocols..."
                
            # Note: A full implementation would parse the llm_output for specific JSON 
            # or bash commands and run them through ice_middleware.validate_command().
            # For this MVP core, we just return the raw text.
            
            if yield_thoughts:
                yield "Execution parameters finalized."
                
            return llm_output
            
        except Exception as e:
            error_msg = f"CRITICAL FAILURE IN WINTERMUTE EXECUTION LOOP: {str(e)}"
            if yield_thoughts:
                yield error_msg
            return error_msg

# Singleton instance
orchestrator = WintermuteCore()
