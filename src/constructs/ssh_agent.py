import os
import glob
import logging
import datetime
from typing import Optional, Dict, List, Any
import paramiko

logger = logging.getLogger(__name__)

class SSHNodeManager:
    """
    Stateful SSH Node Manager with connection pooling, automatic private key detection,
    remote command execution, session management, and SFTP file transfer capabilities.
    """
    def __init__(
        self,
        hostname: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        key_filename: Optional[str] = None,
        port: int = 22
    ):
        self.default_hostname = hostname
        self.default_username = username
        self.default_password = password
        self.default_key_filename = key_filename
        self.default_port = port

        # Connection pool: hostname -> paramiko.SSHClient
        self.sessions: Dict[str, paramiko.SSHClient] = {}
        # Session metadata: hostname -> dict
        self.session_meta: Dict[str, Dict[str, Any]] = {}

    def _detect_key(self, password: Optional[str] = None, key_filename: Optional[str] = None) -> Optional[str]:
        """
        Auto-detects SSH private key paths.
        Checks explicit key_filename, checks if password is a file path,
        or scans default ~/.ssh identity locations.
        """
        if key_filename:
            expanded = os.path.expanduser(key_filename)
            if os.path.isfile(expanded):
                return expanded

        if password and isinstance(password, str):
            expanded_pw = os.path.expanduser(password)
            if os.path.isfile(expanded_pw):
                return expanded_pw

        # Check default ~/.ssh keys
        ssh_dir = os.path.expanduser("~/.ssh")
        candidates = ["id_ed25519", "id_rsa", "id_ecdsa", "id_dsa"]
        for candidate in candidates:
            key_path = os.path.join(ssh_dir, candidate)
            if os.path.isfile(key_path):
                return key_path

        return None

    def get_connection(
        self,
        hostname: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        key_filename: Optional[str] = None,
        port: int = 22,
        timeout: int = 15
    ) -> paramiko.SSHClient:
        """
        Retrieves an active SSH connection from the pool, or establishes a new one.
        Reuses open sessions if transport is still active.
        """
        # Check existing connection in pool
        if hostname in self.sessions:
            client = self.sessions[hostname]
            transport = client.get_transport()
            if transport and transport.is_active():
                self.session_meta[hostname]["last_used"] = datetime.datetime.now().isoformat()
                logger.info(f"Reusing active pooled SSH connection for {hostname}")
                return client
            else:
                logger.info(f"Pooled connection for {hostname} is stale; reconnecting")
                self.disconnect(hostname)

        # Establish new connection
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        detected_key = self._detect_key(password=password, key_filename=key_filename)
        actual_user = username or self.default_username
        
        connect_kwargs: Dict[str, Any] = {
            "hostname": hostname,
            "port": port or self.default_port or 22,
            "timeout": timeout,
            "allow_agent": True,
            "look_for_keys": True,
        }
        if actual_user:
            connect_kwargs["username"] = actual_user

        if detected_key:
            connect_kwargs["key_filename"] = detected_key
            logger.debug(f"Connecting to {hostname} using detected SSH key: {detected_key}")
        elif password and not os.path.isfile(os.path.expanduser(password)):
            connect_kwargs["password"] = password

        client.connect(**connect_kwargs)
        self.sessions[hostname] = client
        self.session_meta[hostname] = {
            "hostname": hostname,
            "username": actual_user,
            "port": port,
            "connected_at": datetime.datetime.now().isoformat(),
            "last_used": datetime.datetime.now().isoformat(),
            "key_file": detected_key
        }
        logger.info(f"Established new SSH session for {hostname} (pooled)")
        return client

    def execute(
        self,
        command: str,
        hostname: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        key_filename: Optional[str] = None,
        port: int = 22,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        Executes a shell command on a remote host via pooled SSH session.
        """
        target_host = hostname or self.default_hostname
        if not target_host:
            return {"stdout": "", "stderr": "No hostname specified for SSH command execution.", "exit_code": -1}

        target_user = username or self.default_username
        target_pw = password or self.default_password
        target_key = key_filename or self.default_key_filename
        target_port = port or self.default_port or 22

        result = {"stdout": "", "stderr": "", "exit_code": 0}
        try:
            client = self.get_connection(
                hostname=target_host,
                username=target_user,
                password=target_pw,
                key_filename=target_key,
                port=target_port
            )
            stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
            result["stdout"] = stdout.read().decode("utf-8", errors="replace")
            result["stderr"] = stderr.read().decode("utf-8", errors="replace")
            result["exit_code"] = stdout.channel.recv_exit_status()
        except Exception as e:
            logger.error(f"Error executing command '{command}' on {target_host}: {e}")
            result["stderr"] = str(e)
            result["exit_code"] = -1

        return result

    def list_active_nodes(self) -> List[Dict[str, Any]]:
        """
        Returns a list of currently active nodes in the connection pool.
        Prunes inactive connections.
        """
        active_nodes = []
        dead_hosts = []

        for host, client in list(self.sessions.items()):
            transport = client.get_transport()
            if transport and transport.is_active():
                meta = self.session_meta.get(host, {})
                active_nodes.append({
                    "hostname": host,
                    "username": meta.get("username"),
                    "port": meta.get("port", 22),
                    "connected_at": meta.get("connected_at"),
                    "last_used": meta.get("last_used"),
                    "status": "connected"
                })
            else:
                dead_hosts.append(host)

        for host in dead_hosts:
            self.disconnect(host)

        return active_nodes

    def disconnect(self, hostname: Optional[str] = None) -> Dict[str, Any]:
        """
        Disconnects an active session by hostname, or disconnects all sessions if hostname is None or 'all'.
        """
        if not hostname or hostname.strip().lower() == "all":
            count = len(self.sessions)
            for host, client in list(self.sessions.items()):
                try:
                    client.close()
                except Exception as e:
                    logger.debug(f"Error closing session {host}: {e}")
            self.sessions.clear()
            self.session_meta.clear()
            return {"status": "success", "message": f"Disconnected all ({count}) active node sessions."}

        target = hostname.strip()
        if target in self.sessions:
            try:
                self.sessions[target].close()
            except Exception as e:
                logger.debug(f"Error closing session for {target}: {e}")
            self.sessions.pop(target, None)
            self.session_meta.pop(target, None)
            return {"status": "success", "message": f"Disconnected session for node {target}."}

        return {"status": "not_found", "message": f"No active session found for node {target}."}

    def transfer_file(
        self,
        hostname: Optional[str] = None,
        local_path: str = "",
        remote_path: str = "",
        action: str = "upload",
        username: Optional[str] = None,
        password: Optional[str] = None,
        key_filename: Optional[str] = None,
        port: int = 22
    ) -> Dict[str, Any]:
        """
        Transfers a file via SFTP over a pooled SSH connection.
        action: 'upload' (local -> remote) or 'download' (remote -> local)
        """
        target_host = hostname or self.default_hostname
        if not target_host:
            return {"status": "error", "error": "No hostname specified for SFTP transfer."}

        target_user = username or self.default_username
        target_pw = password or self.default_password
        target_key = key_filename or self.default_key_filename
        target_port = port or self.default_port or 22

        try:
            client = self.get_connection(
                hostname=target_host,
                username=target_user,
                password=target_pw,
                key_filename=target_key,
                port=target_port
            )
            sftp = client.open_sftp()
            try:
                norm_action = (action or "upload").strip().lower()
                if norm_action in ["upload", "put", "push"]:
                    exp_local = os.path.expanduser(local_path)
                    if not os.path.exists(exp_local):
                        return {"status": "error", "error": f"Local file not found: {local_path}"}
                    sftp.put(exp_local, remote_path)
                    size = os.path.getsize(exp_local)
                    return {
                        "status": "success",
                        "action": "upload",
                        "hostname": target_host,
                        "local_path": exp_local,
                        "remote_path": remote_path,
                        "bytes_transferred": size
                    }
                elif norm_action in ["download", "get", "pull"]:
                    exp_local = os.path.expanduser(local_path)
                    os.makedirs(os.path.dirname(os.path.abspath(exp_local)), exist_ok=True)
                    sftp.get(remote_path, exp_local)
                    size = os.path.getsize(exp_local) if os.path.exists(exp_local) else 0
                    return {
                        "status": "success",
                        "action": "download",
                        "hostname": target_host,
                        "local_path": exp_local,
                        "remote_path": remote_path,
                        "bytes_transferred": size
                    }
                else:
                    return {"status": "error", "error": f"Invalid action '{action}'. Use 'upload' or 'download'."}
            finally:
                sftp.close()
        except Exception as e:
            logger.error(f"SFTP transfer error on {target_host}: {e}")
            return {"status": "error", "error": str(e)}

# Backward compatibility alias
Construct = SSHNodeManager

# Global singleton manager instance
ssh_manager = SSHNodeManager()
