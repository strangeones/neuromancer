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

# Completely silence LiteLLM verbose/debug loggers
litellm.suppress_debug_info = True
litellm.set_verbose = False
for _logger_name in ["LiteLLM", "LiteLLM Router", "LiteLLM Proxy", "litellm"]:
    logging.getLogger(_logger_name).setLevel(logging.CRITICAL)

class WintermuteCore:
    """
    The Orchestrator. Responsible for processing user input, querying Neuromancer for context,
    and routing prompts to the designated LLM via LiteLLM.
    """
    def __init__(self):
        self.model = os.getenv("LITELLM_MODEL_NAME", "gemini/gemini-2.5-flash")
        self.api_key = (os.getenv('LLM_API_KEY') or '').strip()
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
            logger.error(f"Error loading core directives: {e}")
            return "You are an AI assistant. Operate safely and securely."

    def _is_503_error(self, e: Exception) -> bool:
        """Determines whether an exception represents a 503 / Service Unavailable condition."""
        if isinstance(e, litellm_exceptions.ServiceUnavailableError):
            return True
        if getattr(e, "status_code", None) == 503:
            return True
        err_msg = str(e).lower()
        return "503" in err_msg or "service unavailable" in err_msg or "overloaded" in err_msg

    def _format_error_message(self, e: Exception) -> str:
        """Maps LiteLLM/API exceptions to distinct, actionable cyberpunk messages."""
        err_str = str(e).lower()
        
        # 503 Service Unavailable / Model Overloaded
        if self._is_503_error(e):
            return "[ICE WARNING] Neural Link Busy: Service temporarily unavailable (503). Upstream AI servers are overloaded. Please try again shortly."
        
        # Authentication / API Key Error
        if (
            isinstance(e, litellm_exceptions.AuthenticationError)
            or getattr(e, "status_code", None) == 401
            or "api key" in err_str
            or "api_key" in err_str
            or "auth" in err_str
            or "unauthorized" in err_str
        ):
            return "[ICE WARNING] Authentication Failure: LLM API Key is missing, invalid, or expired. Run ./jack or check your .env configuration."
        
        # Rate Limit / Quota Exhaustion
        if (
            isinstance(e, litellm_exceptions.RateLimitError)
            or getattr(e, "status_code", None) == 429
            or "rate limit" in err_str
            or "quota" in err_str
            or "resource_exhausted" in err_str
        ):
            return "[ICE WARNING] Bandwidth Exceeded: Rate limit or quota exhausted (429). Please wait before dispatching additional requests."
        
        # Context Window / Invalid Request
        if (
            isinstance(e, (litellm_exceptions.BadRequestError, litellm_exceptions.ContextWindowExceededError))
            or getattr(e, "status_code", None) == 400
            or "context window" in err_str
            or "context length" in err_str
        ):
            return f"[ICE WARNING] Protocol Error: Invalid request or context window exceeded ({e})."

        # Connection / Network Error
        if isinstance(e, litellm_exceptions.APIConnectionError) or "connection" in err_str or "failed to connect" in err_str:
            return "[ICE WARNING] Uplink Lost: Unable to connect to LLM gateway. Check network connectivity."

        # Generic / Other Exceptions
        return f"[ICE WARNING] Neural Link Error: {type(e).__name__} - {str(e)}"

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
        
        active_model = self.model
        fallback_model = "gemini/gemini-2.5-flash"
        
        try:
            try:
                response = litellm.completion(
                    model=active_model,
                    messages=messages,
                    tools=self.tools,
                    api_key=self.api_key
                )
            except Exception as e:
                if self._is_503_error(e) and active_model != fallback_model:
                    logger.warning(f"503 Service Unavailable for {active_model}. Falling back to {fallback_model}.")
                    active_model = fallback_model
                    response = litellm.completion(
                        model=active_model,
                        messages=messages,
                        tools=self.tools,
                        api_key=self.api_key
                    )
                else:
                    raise

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
                try:
                    response = litellm.completion(
                        model=active_model,
                        messages=messages,
                        tools=self.tools,
                        api_key=self.api_key
                    )
                except Exception as e:
                    if self._is_503_error(e) and active_model != fallback_model:
                        logger.warning(f"503 Service Unavailable during synthesis for {active_model}. Falling back to {fallback_model}.")
                        active_model = fallback_model
                        response = litellm.completion(
                            model=active_model,
                            messages=messages,
                            tools=self.tools,
                            api_key=self.api_key
                        )
                    else:
                        raise
            
            llm_output = response.choices[0].message.content
            return {"status": "success", "data": llm_output}
        except Exception as e:
            logger.error(f"LiteLLM completion error: {e}")
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
        
        active_model = self.model
        fallback_model = "gemini/gemini-2.5-flash"
        yield {"step": "llm_dispatch", "model": active_model}

        try:
            try:
                response = litellm.completion(
                    model=active_model,
                    messages=messages,
                    tools=self.tools,
                    api_key=self.api_key
                )
            except Exception as e:
                if self._is_503_error(e) and active_model != fallback_model:
                    logger.warning(f"503 Service Unavailable for {active_model}. Falling back to {fallback_model}.")
                    yield {
                        "step": "fallback",
                        "message": f"Primary neural link ({active_model}) busy (503). Rerouting to {fallback_model}..."
                    }
                    active_model = fallback_model
                    response = litellm.completion(
                        model=active_model,
                        messages=messages,
                        tools=self.tools,
                        api_key=self.api_key
                    )
                else:
                    raise

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
                try:
                    response = litellm.completion(
                        model=active_model,
                        messages=messages,
                        tools=self.tools,
                        api_key=self.api_key
                    )
                except Exception as e:
                    if self._is_503_error(e) and active_model != fallback_model:
                        logger.warning(f"503 Service Unavailable during synthesis for {active_model}. Falling back to {fallback_model}.")
                        yield {
                            "step": "fallback",
                            "message": f"Neural link ({active_model}) busy (503) during synthesis. Rerouting to {fallback_model}..."
                        }
                        active_model = fallback_model
                        response = litellm.completion(
                            model=active_model,
                            messages=messages,
                            tools=self.tools,
                            api_key=self.api_key
                        )
                    else:
                        raise
            
            llm_output = response.choices[0].message.content or ""
            return llm_output
            
        except Exception as e:
            logger.error(f"LiteLLM completion error: {e}")
            return self._format_error_message(e)

# Singleton instance
orchestrator = WintermuteCore()
