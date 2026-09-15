import os
import logging
from typing import Dict, Any, Generator, Union

import litellm
from litellm import exceptions as litellm_exceptions
from dotenv import load_dotenv

# Import the local subnet modules
from src.ice import ice_middleware
from src.neuromancer import memory_core

# Load environment variables (API keys, model selection)
load_dotenv()
logger = logging.getLogger(__name__)

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
            prompt_path = os.getenv("CORE_DIRECTIVES_PATH", "core_directives.md")
            if os.path.exists(prompt_path):
                with open(prompt_path, "r", encoding="utf-8") as f:
                    return f.read()
            else:
                logger.warning(f"Core directives file not found at {prompt_path}.")
                return "You are an AI assistant. Operate safely and securely."
        except Exception as e:
            logger.error(f"Error loading core directives: {e}", exc_info=True)
            return "You are an AI assistant. Operate safely and securely."

    def process_request(self, user_prompt: str, yield_thoughts: bool = False) -> Union[Dict[str, Any], Generator[Dict[str, Any], None, None]]:
        """
        Main execution pipeline.
        If yield_thoughts is True, it yields steps as structured dicts.
        """
        if yield_thoughts:
            return self._process_request_generator(user_prompt)
        else:
            return self._process_request_sync(user_prompt)

    def _process_request_sync(self, user_prompt: str) -> Dict[str, Any]:
        memories = memory_core.retrieve_relevant_memory(user_prompt)
        
        memory_context = ""
        if memories:
            memory_context = "\n\n--- RELEVANT PAST MEMORIES ---\n" + "\n".join(memories)

        messages = [
            {"role": "system", "content": f"{self.system_prompt}{memory_context}"},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            response = litellm.completion(
                model=self.model,
                messages=messages
            )
            llm_output = response.choices[0].message.content
            return {"status": "success", "data": llm_output}
        except Exception as e:
            logger.error(f"LiteLLM completion error: {e}", exc_info=True)
            return {"status": "error", "error": str(e), "error_type": type(e).__name__}

    def _process_request_generator(self, user_prompt: str) -> Generator[Dict[str, Any], None, None]:
        yield {"step": "init", "message": "Analyzing request"}
        
        yield {"step": "memory_query", "message": "Querying vector memory"}
        memories = memory_core.retrieve_relevant_memory(user_prompt)
        
        memory_context = ""
        if memories:
            yield {"step": "memory_found", "count": len(memories)}
            memory_context = "\n\n--- RELEVANT PAST MEMORIES ---\n" + "\n".join(memories)
        else:
            yield {"step": "memory_empty"}

        messages = [
            {"role": "system", "content": f"{self.system_prompt}{memory_context}"},
            {"role": "user", "content": user_prompt}
        ]
        
        yield {"step": "llm_dispatch", "model": self.model}

        try:
            response = litellm.completion(
                model=self.model,
                messages=messages
            )
            llm_output = response.choices[0].message.content
            yield {"step": "llm_response", "status": "success", "data": llm_output}
            
        except Exception as e:
            logger.error(f"LiteLLM completion error: {e}", exc_info=True)
            yield {"step": "llm_response", "status": "error", "error": str(e), "error_type": type(e).__name__}

# Singleton instance
orchestrator = WintermuteCore()
