import os
import json
import logging
from typing import Dict, Any, Generator, Union

import litellm
from litellm import exceptions as litellm_exceptions
from dotenv import load_dotenv

# Import the local subnet modules
from src.ice import ice_middleware
from src.neuromancer import memory_core
from src.constructs.ssh_agent import Construct as SSHConstruct
from src.constructs.nmap_agent import ScannerConstruct
from src.constructs.scraper_agent import ScraperConstruct

# Load environment variables (API keys, model selection)
load_dotenv()
logger = logging.getLogger(__name__)

class WintermuteCore:
    """
    The Orchestrator. Responsible for processing user input, querying Neuromancer for context,
    and routing prompts to the designated LLM via LiteLLM.
    """
    def __init__(self):
        self.model = os.getenv("LITELLM_MODEL_NAME", "gemini/gemini-1.5-flash")
        self.api_key = os.getenv("LLM_API_KEY")
        self.system_prompt = self._load_core_directives()
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "execute_ssh_command",
                    "description": "Execute a shell command on a remote server via SSH.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "hostname": {"type": "string", "description": "The IP address or hostname of the remote server."},
                            "username": {"type": "string", "description": "The SSH username."},
                            "password": {"type": "string", "description": "The SSH password or key path."},
                            "command": {"type": "string", "description": "The bash command to execute."}
                        },
                        "required": ["hostname", "username", "password", "command"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "nmap_scan",
                    "description": "Perform an Nmap port scan on a target host or subnet.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "hosts": {"type": "string", "description": "The target IP, hostname, or subnet (e.g. 192.168.1.0/24)."},
                            "arguments": {"type": "string", "description": "Optional nmap flags. Defaults to '-T4 -F'."}
                        },
                        "required": ["hosts"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "scrape_website",
                    "description": "Fetch and extract text content from a web URL or internal IP portal.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "The full HTTP/HTTPS URL to scrape."}
                        },
                        "required": ["url"]
                    }
                }
            }
        ]
        
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
                messages=messages,
                tools=self.tools,
                api_key=self.api_key
            )
            
            message = response.choices[0].message
            if getattr(message, "tool_calls", None):
                messages.append(message)
                for tool_call in message.tool_calls:
                    args = json.loads(tool_call.function.arguments)
                    res = {}
                    if tool_call.function.name == "execute_ssh_command":
                        c = SSHConstruct(args['hostname'], args['username'], args.get('password'))
                        res = c.execute(args['command'])
                    elif tool_call.function.name == "nmap_scan":
                        c = ScannerConstruct()
                        res = c.scan(args['hosts'], args.get('arguments', '-T4 -F'))
                    elif tool_call.function.name == "scrape_website":
                        c = ScraperConstruct()
                        res = c.scrape(args['url'])
                        
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_call.function.name,
                        "content": json.dumps(res)
                    })
                response = litellm.completion(
                    model=self.model,
                    messages=messages,
                    tools=self.tools,
                    api_key=self.api_key
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
                messages=messages,
                tools=self.tools,
                api_key=self.api_key
            )
            
            message = response.choices[0].message
            if getattr(message, "tool_calls", None):
                yield {"step": "tool_call", "message": "Initiating SSH Construct traversal"}
                messages.append(message)
                for tool_call in message.tool_calls:
                    args = json.loads(tool_call.function.arguments)
                    res = {}
                    if tool_call.function.name == "execute_ssh_command":
                        yield {"step": "ssh_connect", "target": args['hostname']}
                        c = SSHConstruct(args['hostname'], args['username'], args.get('password'))
                        res = c.execute(args['command'])
                    elif tool_call.function.name == "nmap_scan":
                        yield {"step": "nmap_scan", "target": args['hosts']}
                        c = ScannerConstruct()
                        res = c.scan(args['hosts'], args.get('arguments', '-T4 -F'))
                    elif tool_call.function.name == "scrape_website":
                        yield {"step": "web_scrape", "target": args['url']}
                        c = ScraperConstruct()
                        res = c.scrape(args['url'])
                        
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_call.function.name,
                        "content": json.dumps(res)
                    })
                
                yield {"step": "llm_synthesis", "message": "Synthesizing intelligence"}
                response = litellm.completion(
                    model=self.model,
                    messages=messages,
                    tools=self.tools,
                    api_key=self.api_key
                )
            
            llm_output = response.choices[0].message.content
            return llm_output
            
        except Exception as e:
            logger.error(f"LiteLLM completion error: {e}", exc_info=True)
            return "[ICE WARNING] Neural Link Failure: API Key Missing or Invalid."

# Singleton instance
orchestrator = WintermuteCore()
