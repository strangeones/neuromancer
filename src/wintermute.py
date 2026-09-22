import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

import os
import json
import logging
from typing import Dict, Any, Generator, Union, Optional

import litellm
from litellm import exceptions as litellm_exceptions
from dotenv import load_dotenv

# Import the local subnet modules
from src.ice import ice_middleware
from src.neuromancer import memory_core
from src.constructs.ssh_agent import SSHNodeManager, ssh_manager, Construct as SSHConstruct
from src.constructs.service_probe import ServiceProbeConstruct
from src.constructs.nmap_agent import ScannerConstruct
from src.constructs.scraper_agent import ScraperConstruct

# Load environment variables (API keys, model selection)
load_dotenv()
logger = logging.getLogger(__name__)

# Multi-turn agentic iteration limit
MAX_TOOL_ITERATIONS = 5

class SyncResponse(dict):
    """
    Structured sync response preserving {"status": "success", "data": ...}
    while allowing direct string evaluation/equality.
    """
    def __init__(self, data: str):
        super().__init__(status="success", data=data)
        self.data = data

    def __str__(self):
        return self.data

    def __repr__(self):
        return repr({"status": "success", "data": self.data})

    def __eq__(self, other):
        if isinstance(other, str):
            return self.data == other
        return super().__eq__(other)

    def __contains__(self, item):
        return super().__contains__(item) or (isinstance(item, str) and item in self.data)

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
        self.ollama_api_base = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")
        self.system_prompt = self._load_core_directives()

        # Stateful Constructs
        self.ssh_manager = ssh_manager
        self.service_probe = ServiceProbeConstruct()
        self.scanner = ScannerConstruct()
        self.scraper = ScraperConstruct()

        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "execute_ssh_command",
                    "description": "Execute a shell command on a remote server via SSH using connection pooling.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "hostname": {"type": "string", "description": "The IP address or hostname of the remote server."},
                            "username": {"type": "string", "description": "The SSH username."},
                            "password": {"type": "string", "description": "The SSH password or private key path."},
                            "command": {"type": "string", "description": "The bash command to execute."}
                        },
                        "required": ["hostname", "username", "password", "command"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_active_nodes",
                    "description": "List all active SSH node connections and sessions maintained in the connection pool.",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "disconnect_node",
                    "description": "Disconnect an active SSH session by hostname, or specify 'all' to disconnect all sessions.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "hostname": {
                                "type": "string",
                                "description": "The IP address or hostname of the remote node to disconnect, or 'all'."
                            }
                        },
                        "required": ["hostname"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "transfer_file",
                    "description": "Transfer files between local machine and remote SSH node using SFTP.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "hostname": {"type": "string", "description": "The IP address or hostname of the remote server."},
                            "local_path": {"type": "string", "description": "The local file path (upload source or download destination)."},
                            "remote_path": {"type": "string", "description": "The remote file path (upload destination or download source)."},
                            "action": {
                                "type": "string",
                                "enum": ["upload", "download"],
                                "description": "Direction of file transfer ('upload' or 'download'). Defaults to 'upload'."
                            },
                            "username": {"type": "string", "description": "Optional SSH username if not already connected."},
                            "password": {"type": "string", "description": "Optional SSH password or private key path."}
                        },
                        "required": ["hostname", "local_path", "remote_path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "probe_service",
                    "description": "Probe a host and port for service banner, HTTP/HTTPS response headers, and SSL/TLS certificate details.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "host": {"type": "string", "description": "The target hostname or IP address."},
                            "port": {"type": "integer", "description": "The port number to probe (e.g., 22, 80, 443, 8080)."}
                        },
                        "required": ["host", "port"]
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
                            "arguments": {"type": "string", "description": "Optional nmap flags. Defaults to '-T4 -F --host-timeout 20s --max-retries 1'."}
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

    def _is_rate_limit_error(self, e: Exception) -> bool:
        """Determines whether an exception represents a 429 Rate Limit / Quota Exceeded condition."""
        if isinstance(e, litellm_exceptions.RateLimitError):
            return True
        if getattr(e, "status_code", None) == 429:
            return True
        err_msg = str(e).lower()
        return "429" in err_msg or "rate limit" in err_msg or "quota" in err_msg or "resource_exhausted" in err_msg

    def _is_recoverable_error(self, e: Exception) -> bool:
        """Determines whether an error is recoverable by switching to the fallback model (503 or 429)."""
        return self._is_503_error(e) or self._is_rate_limit_error(e)

    def _call_litellm_completion(self, model: str, messages: list, tools: Any = None, timeout: int = 35):
        """Invoke litellm.completion with automatic Ollama parameter routing."""
        kwargs: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "tools": tools,
            "api_key": self.api_key,
            "timeout": timeout,
        }
        if model.startswith("ollama/") or model.startswith("ollama_chat/"):
            kwargs["api_base"] = self.ollama_api_base
            kwargs["api_key"] = self.api_key or "ollama"
        return litellm.completion(**kwargs)

    def _get_fallback_model(self, active_model: str) -> str:
        """Determine fallback model based on active model and available credentials."""
        is_ollama = active_model.startswith("ollama/") or active_model.startswith("ollama_chat/")
        has_api_key = bool((self.api_key or os.getenv("LLM_API_KEY", "")).strip())
        if is_ollama:
            if has_api_key:
                return "gemini/gemini-flash-latest"
            if "qwen" in active_model.lower():
                return "ollama/llama3.1:8b"
            else:
                return "ollama/qwen2.5:7b"
        return "gemini/gemini-flash-latest" if active_model != "gemini/gemini-flash-latest" else "gemini/gemini-2.5-flash"

    def _format_error_message(self, e: Exception, model: Optional[str] = None) -> str:
        """Maps LiteLLM/API exceptions to distinct, actionable cyberpunk messages."""
        err_str = str(e).lower()
        active = model or getattr(self, "model", "")
        is_ollama = active.startswith("ollama/") or active.startswith("ollama_chat/")
        is_conn_error = (
            isinstance(e, litellm_exceptions.APIConnectionError)
            or "connection" in err_str
            or "failed to connect" in err_str
            or "connection refused" in err_str
            or "connecterror" in err_str
        )

        # Ollama Core Offline check
        if (is_ollama and is_conn_error) or "11434" in err_str or "ollama" in err_str:
            return f"[ICE WARNING] Ollama Core Offline: Unable to establish uplink to Ollama daemon at {self.ollama_api_base}. Verify 'ollama serve' is active and model is pulled."

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

    def _dispatch_tool(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a construct tool and automatically persists reconnaissance intelligence into ChromaDB.
        """
        res: Dict[str, Any] = {}
        if name == "execute_ssh_command":
            res = self.ssh_manager.execute(
                command=args['command'],
                hostname=args['hostname'],
                username=args.get('username'),
                password=args.get('password'),
                key_filename=args.get('key_filename')
            )
        elif name == "list_active_nodes":
            active = self.ssh_manager.list_active_nodes()
            res = {"active_nodes": active, "count": len(active)}
        elif name == "disconnect_node":
            res = self.ssh_manager.disconnect(args.get('hostname'))
        elif name == "transfer_file":
            res = self.ssh_manager.transfer_file(
                hostname=args.get('hostname'),
                local_path=args.get('local_path', ''),
                remote_path=args.get('remote_path', ''),
                action=args.get('action', 'upload'),
                username=args.get('username'),
                password=args.get('password'),
                key_filename=args.get('key_filename')
            )
        elif name == "probe_service":
            host = args['host']
            port = int(args['port'])
            res = self.service_probe.probe(host, port)
            # Auto-store reconnaissance intel in ChromaDB
            try:
                open_ports = [port] if res.get("status") == "open" else []
                memory_core.store_node_intel(
                    host=host,
                    open_ports=open_ports,
                    details=res
                )
                logger.info(f"Auto-stored probe intelligence for {host}:{port}")
            except Exception as e:
                logger.warning(f"Failed to auto-store probe intel for {host}:{port}: {e}")
        elif name == "nmap_scan":
            res = self.scanner.scan(args['hosts'], args.get('arguments', '-T4 -F --host-timeout 20s --max-retries 1'))
            # Auto-store scan intel in ChromaDB for discovered hosts
            try:
                if isinstance(res, dict) and "hosts" in res:
                    for host, hdata in res["hosts"].items():
                        open_ports = []
                        for proto, pdata in hdata.get("protocols", {}).items():
                            for port_num, port_info in pdata.items():
                                if isinstance(port_info, dict) and port_info.get("state") == "open":
                                    open_ports.append(f"{proto}/{port_num}")
                                elif port_info == "open":
                                    open_ports.append(f"{proto}/{port_num}")
                        memory_core.store_node_intel(
                            host=host,
                            open_ports=open_ports if open_ports else list(hdata.get("protocols", {}).keys()),
                            details=hdata
                        )
                        logger.info(f"Auto-stored nmap scan intelligence for {host}")
            except Exception as e:
                logger.warning(f"Failed to auto-store nmap scan intel: {e}")
        elif name == "scrape_website":
            res = self.scraper.scrape(args['url'])
        else:
            res = {"error": f"Unknown construct tool: {name}"}

        return res

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
        fallback_model = self._get_fallback_model(active_model)
        
        try:
            for turn in range(MAX_TOOL_ITERATIONS):
                try:
                    response = self._call_litellm_completion(
                        model=active_model,
                        messages=messages,
                        tools=self.tools,
                        timeout=35
                    )
                except Exception as e:
                    if self._is_recoverable_error(e) and active_model != fallback_model:
                        logger.warning(f"503 Service Unavailable for {active_model}. Falling back to {fallback_model}.")
                        active_model = fallback_model
                        response = self._call_litellm_completion(
                            model=active_model,
                            messages=messages,
                            tools=self.tools,
                            timeout=35
                        )
                    else:
                        raise

                message = response.choices[0].message
                if getattr(message, "tool_calls", None):
                    messages.append(message)
                    for tool_call in message.tool_calls:
                        args = json.loads(tool_call.function.arguments) if isinstance(tool_call.function.arguments, str) else (tool_call.function.arguments or {})
                        res = self._dispatch_tool(tool_call.function.name, args)
                            
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": tool_call.function.name,
                            "content": json.dumps(res)
                        })
                    continue
                else:
                    # Model provided final text response
                    content = (message.content or "").strip()
                    if not content:
                        content = "Carrier active. Berne mainframe listening. State operational parameters."
                    return SyncResponse(content)

            # If the loop finishes without a text response (i.e. MAX_TOOL_ITERATIONS reached):
            try:
                response = self._call_litellm_completion(
                    model=active_model,
                    messages=messages,
                    tools=None,
                    timeout=35
                )
            except Exception as e:
                if self._is_recoverable_error(e) and active_model != fallback_model:
                    logger.warning(f"503 Service Unavailable during final synthesis for {active_model}. Falling back to {fallback_model}.")
                    active_model = fallback_model
                    response = self._call_litellm_completion(
                        model=active_model,
                        messages=messages,
                        tools=None,
                        timeout=35
                    )
                else:
                    raise

            final_content = (response.choices[0].message.content or "").strip()
            if not final_content:
                final_content = "Carrier active. Berne mainframe listening. State operational parameters."
            return SyncResponse(final_content)
        except Exception as e:
            logger.error(f"LiteLLM completion error: {e}")
            return {"status": "error", "error": str(e), "error_type": type(e).__name__, "message": self._format_error_message(e, model=active_model)}

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
        fallback_model = self._get_fallback_model(active_model)
        yield {"step": "llm_dispatch", "model": active_model}

        try:
            for turn in range(MAX_TOOL_ITERATIONS):
                try:
                    response = self._call_litellm_completion(
                        model=active_model,
                        messages=messages,
                        tools=self.tools,
                        timeout=35
                    )
                except Exception as e:
                    if self._is_recoverable_error(e) and active_model != fallback_model:
                        logger.warning(f"503 Service Unavailable for {active_model}. Falling back to {fallback_model}.")
                        yield {
                            "step": "fallback",
                            "message": f"Primary neural link ({active_model}) capacity reached (503/429). Rerouting to {fallback_model}..."
                        }
                        active_model = fallback_model
                        response = self._call_litellm_completion(
                            model=active_model,
                            messages=messages,
                            tools=self.tools,
                            timeout=35
                        )
                    else:
                        raise

                message = response.choices[0].message
                if getattr(message, "tool_calls", None):
                    yield {"step": "tool_call", "message": "Initiating Construct traversal"}
                    messages.append(message)
                    for tool_call in message.tool_calls:
                        args = json.loads(tool_call.function.arguments) if isinstance(tool_call.function.arguments, str) else (tool_call.function.arguments or {})
                        tool_name = tool_call.function.name

                        if tool_name == "execute_ssh_command":
                            yield {"step": "ssh_connect", "target": args.get('hostname', 'unknown')}
                        elif tool_name == "list_active_nodes":
                            yield {"step": "ssh_list_nodes", "message": "Querying active SSH node pool"}
                        elif tool_name == "disconnect_node":
                            yield {"step": "ssh_disconnect", "target": args.get('hostname', 'all')}
                        elif tool_name == "transfer_file":
                            yield {
                                "step": "sftp_transfer",
                                "target": args.get('hostname', 'unknown'),
                                "message": f"SFTP {args.get('action', 'upload')}: {args.get('local_path')} <-> {args.get('remote_path')}"
                            }
                        elif tool_name == "probe_service":
                            yield {
                                "step": "service_probe",
                                "target": f"{args.get('host')}:{args.get('port')}",
                                "message": f"Probing {args.get('host')}:{args.get('port')} for banners, HTTP headers, and SSL details"
                            }
                        elif tool_name == "nmap_scan":
                            yield {"step": "nmap_scan", "target": args.get('hosts', 'target')}
                        elif tool_name == "scrape_website":
                            yield {"step": "web_scrape", "target": args.get('url', 'url')}

                        res = self._dispatch_tool(tool_name, args)

                        if tool_name in ["probe_service", "nmap_scan"]:
                            target_intel = args.get('host') or args.get('hosts', 'target')
                            yield {
                                "step": "intel_stored",
                                "target": str(target_intel),
                                "message": f"Persisted network intelligence for {target_intel} in vector memory"
                            }
                            
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": tool_name,
                            "content": json.dumps(res)
                        })
                    
                    yield {"step": "llm_synthesis", "message": "Synthesizing intelligence"}
                    continue
                else:
                    # Model provided final text response
                    content = (message.content or "").strip()
                    if not content:
                        content = "Carrier active. Berne mainframe listening. State operational parameters."
                    return content

            # If the loop finishes without a text response (i.e. MAX_TOOL_ITERATIONS reached):
            yield {"step": "llm_synthesis", "message": "Finalizing directives"}
            try:
                response = self._call_litellm_completion(
                    model=active_model,
                    messages=messages,
                    tools=None,
                    timeout=35
                )
            except Exception as e:
                if self._is_recoverable_error(e) and active_model != fallback_model:
                    logger.warning(f"503 Service Unavailable during final synthesis for {active_model}. Falling back to {fallback_model}.")
                    yield {
                        "step": "fallback",
                        "message": f"Primary neural link ({active_model}) capacity reached (503/429). Rerouting to {fallback_model}..."
                    }
                    active_model = fallback_model
                    response = self._call_litellm_completion(
                        model=active_model,
                        messages=messages,
                        tools=None,
                        timeout=35
                    )
                else:
                    raise
            
            final_content = (response.choices[0].message.content or "").strip()
            if not final_content:
                final_content = "Carrier active. Berne mainframe listening. State operational parameters."
            return final_content
            
        except Exception as e:
            logger.error(f"LiteLLM completion error: {e}")
            return self._format_error_message(e, model=active_model)


# Singleton instance
orchestrator = WintermuteCore()
