import re
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BLACK-ICE")

class BlackICE:
    """
    Security middleware designed to prevent destructive actions by the AI core or subnets.
    """
    def __init__(self):
        # List of regex patterns for dangerous commands
        self.dangerous_patterns = [
            r"rm\s+-r[fF]?\s+/",         # Wipe root
            r"mkfs",                     # Format disk
            r"dd\s+if=.*of=/dev/",       # Overwrite block devices
            r"chmod\s+-R\s+777\s+/",     # Nuke root permissions
            r"chown\s+-R\s+.*:/",        # Nuke root ownership
            r">\s*/dev/sd[a-z]",         # Direct write to disk
            r"mv\s+.* /dev/null",        # Move to null (dangerous on system dirs)
            r"shutdown\s+-h",            # Halt system
            r"reboot",                   # Reboot system
        ]
        
        # Protected directories that the AI cannot modify
        self.protected_dirs = [
            "/etc",
            "/boot",
            "/var/lib",
            "/usr/lib"
        ]

    def validate_command(self, command: str) -> bool:
        """
        Parses a shell command. Returns True if safe, False if blocked by ICE.
        """
        for pattern in self.dangerous_patterns:
            if re.search(pattern, command):
                logger.warning(f"ICE INTERCEPT: Blocked destructive command pattern matched: {pattern}")
                return False
                
        for p_dir in self.protected_dirs:
            # Basic check for commands targeting protected directories
            if p_dir in command and any(cmd in command for cmd in ["rm", "mv", "cp", "chmod", "chown"]):
                logger.warning(f"ICE INTERCEPT: Attempted modification of protected directory: {p_dir}")
                return False

        return True

    def verify_file_access(self, file_path: str, mode: str = 'w') -> bool:
        """
        Checks if the AI is allowed to read/write a specific file.
        """
        abs_path = os.path.abspath(file_path)
        
        # Prevent writing to its own core files
        if mode in ['w', 'a', 'x']:
            if "src/" in abs_path or "core_directives.md" in abs_path or "jack-in.sh" in abs_path:
                logger.warning(f"ICE INTERCEPT: Attempted write to core system file: {abs_path}")
                return False
                
        return True

# Global ICE instance
ice_middleware = BlackICE()
