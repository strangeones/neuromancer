import nmap
import logging
import concurrent.futures
import shlex
import re

logger = logging.getLogger(__name__)

class ScannerConstruct:
    """Construct for network traversal and port scanning using Nmap."""
    def __init__(self):
        try:
            self.nm = nmap.PortScanner()
        except nmap.PortScannerError:
            logger.error("Nmap not found. Ensure nmap is installed on the system.")
            self.nm = None

    def scan(self, hosts: str, arguments: str = '-T4 -F --host-timeout 20s --max-retries 1') -> dict:
        """
        Executes an nmap scan.
        hosts: e.g., '192.168.1.0/24' or '192.168.1.50'
        arguments: default is Fast scan with timeout and retry limits.
        """
        if not self.nm:
            return {"error": "Nmap binary not found on the host system."}
            
        if not re.match(r'^[a-zA-Z0-9.\-/_ ]+$', hosts):
            return {"error": "Security restriction: Invalid characters in hosts parameter."}

        if '--host-timeout' not in arguments:
            arguments = f"{arguments} --host-timeout 20s"
            
        dangerous_flags = ['--script', '-o', '-i', '--exec', '--sh-exec']
        parsed_args = shlex.split(arguments)
        for flag in dangerous_flags:
            if any(arg.startswith(flag) for arg in parsed_args):
                return {"error": f"Security restriction: The '{flag}' flag is not allowed."}
            
        result = {"hosts": {}}
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        try:
            future = executor.submit(self.nm.scan, hosts=hosts, arguments=arguments)
            future.result(timeout=25)
            for host in self.nm.all_hosts():
                host_info = {
                    "state": self.nm[host].state(),
                    "protocols": {}
                }
                for proto in self.nm[host].all_protocols():
                    ports = self.nm[host][proto].keys()
                    host_info["protocols"][proto] = {}
                    for port in ports:
                        host_info["protocols"][proto][port] = self.nm[host][proto][port]
                result["hosts"][host] = host_info
        except concurrent.futures.TimeoutError:
            executor.shutdown(wait=False, cancel_futures=True)
            logger.error("ICE Timeout: Target host scan exceeded 25s deadline.")
            return {"hosts": {}, "error": "ICE Timeout: Target host scan exceeded 25s deadline."}
        except Exception as e:
            executor.shutdown(wait=False)
            logger.error(f"Error during nmap scan: {e}")
            result["error"] = str(e)
        else:
            executor.shutdown(wait=False)
            
        return result
