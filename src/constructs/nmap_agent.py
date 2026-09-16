import nmap
import logging

logger = logging.getLogger(__name__)

class ScannerConstruct:
    """Construct for network traversal and port scanning using Nmap."""
    def __init__(self):
        try:
            self.nm = nmap.PortScanner()
        except nmap.PortScannerError:
            logger.error("Nmap not found. Ensure nmap is installed on the system.")
            self.nm = None

    def scan(self, hosts: str, arguments: str = '-T4 -F') -> dict:
        """
        Executes an nmap scan.
        hosts: e.g., '192.168.1.0/24' or '192.168.1.50'
        arguments: default is Fast scan.
        """
        if not self.nm:
            return {"error": "Nmap binary not found on the host system."}
            
        result = {"hosts": {}}
        try:
            self.nm.scan(hosts=hosts, arguments=arguments)
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
        except Exception as e:
            logger.error(f"Error during nmap scan: {e}")
            result["error"] = str(e)
            
        return result
