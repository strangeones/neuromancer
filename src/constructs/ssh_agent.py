import paramiko
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class Construct:
    def __init__(self, hostname: str, username: str, password: Optional[str] = None, key_filename: Optional[str] = None):
        self.hostname = hostname
        self.username = username
        self.password = password
        self.key_filename = key_filename
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def execute(self, command: str) -> dict:
        result = {"stdout": "", "stderr": ""}
        try:
            self.client.connect(
                hostname=self.hostname,
                username=self.username,
                password=self.password,
                key_filename=self.key_filename,
            )
            stdin, stdout, stderr = self.client.exec_command(command)
            result["stdout"] = stdout.read().decode("utf-8")
            result["stderr"] = stderr.read().decode("utf-8")
        except Exception as e:
            logger.error(f"Error executing command '{command}' on {self.hostname}: {e}")
            result["stderr"] = str(e)
        finally:
            self.client.close()
        return result
