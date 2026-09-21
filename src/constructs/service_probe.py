import socket
import ssl
import logging
import datetime
from typing import Optional, Dict, Any, List
import requests
from bs4 import BeautifulSoup
import urllib3

# Suppress insecure SSL warnings for target service probing
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

try:
    from cryptography import x509
    from cryptography.x509.oid import NameOID, ExtensionOID
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False

class ServiceProbeConstruct:
    """
    Construct for deep service reconnaissance.
    Probes open host:port targets for service banners, HTTP/HTTPS response headers,
    and SSL/TLS certificate details.
    """
    def __init__(self, default_timeout: float = 5.0):
        self.default_timeout = default_timeout

    def probe(self, host: str, port: int, timeout: Optional[float] = None) -> Dict[str, Any]:
        """
        Main probe orchestrator for a given host and port.
        """
        to = timeout or self.default_timeout
        result: Dict[str, Any] = {
            "host": host,
            "port": port,
            "banner": None,
            "http": None,
            "ssl": None,
            "status": "unknown"
        }

        # Test socket reachability and grab raw banner
        banner, is_open = self._probe_banner(host, port, to)
        result["banner"] = banner
        if not is_open:
            result["status"] = "unreachable"
            result["error"] = f"Unable to establish TCP connection to {host}:{port}"
            return result

        result["status"] = "open"

        # Probe SSL/TLS details
        ssl_info = self._probe_ssl(host, port, to)
        if ssl_info:
            result["ssl"] = ssl_info

        # Probe HTTP/HTTPS headers and metadata
        http_info = self._probe_http(host, port, to, has_ssl=bool(ssl_info))
        if http_info:
            result["http"] = http_info

        return result

    def _probe_banner(self, host: str, port: int, timeout: float) -> tuple[Optional[str], bool]:
        """
        Connects via raw TCP socket, attempts to read initial service greeting,
        or sends probe bytes to elicit a banner response.
        """
        try:
            with socket.create_connection((host, port), timeout=timeout) as s:
                s.settimeout(1.5)
                # 1. Check for immediate banner on connect (e.g. SSH, FTP, SMTP, MySQL)
                try:
                    data = s.recv(2048)
                    if data:
                        return data.decode("utf-8", errors="replace").strip(), True
                except (socket.timeout, socket.error):
                    pass

                # 2. If quiet, send generic probe
                try:
                    s.sendall(b"\r\n\r\n")
                    data = s.recv(2048)
                    if data:
                        return data.decode("utf-8", errors="replace").strip(), True
                except (socket.timeout, socket.error):
                    pass

                return None, True
        except (socket.timeout, socket.error, OSError) as e:
            logger.debug(f"TCP connection failed to {host}:{port}: {e}")
            return None, False

    def _probe_ssl(self, host: str, port: int, timeout: float) -> Optional[Dict[str, Any]]:
        """
        Initiates TLS handshake to extract SSL/TLS protocol version, cipher, and certificate details.
        """
        # Don't probe SSL on known plaintext protocols unless standard SSL ports or instructed
        known_plain = [21, 22, 23, 25, 53, 80, 110, 143]
        if port in known_plain and port not in [443, 8443]:
            return None

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        try:
            with socket.create_connection((host, port), timeout=timeout) as sock:
                with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                    version = ssock.version()
                    cipher_info = ssock.cipher()
                    der_cert = ssock.getpeercert(binary_form=True)

                    ssl_details: Dict[str, Any] = {
                        "version": version,
                        "cipher": cipher_info[0] if cipher_info else None,
                        "cipher_bits": cipher_info[2] if cipher_info and len(cipher_info) > 2 else None,
                    }

                    if der_cert and HAS_CRYPTOGRAPHY:
                        cert_data = self._parse_x509_cert(der_cert)
                        ssl_details.update(cert_data)

                    return ssl_details
        except Exception as e:
            logger.debug(f"SSL probe skipped/failed for {host}:{port}: {e}")
            return None

    def _parse_x509_cert(self, der_bytes: bytes) -> Dict[str, Any]:
        """Parses DER-encoded X.509 certificate using cryptography."""
        try:
            cert = x509.load_der_x509_certificate(der_bytes)
            
            # Subject details
            subject_cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
            subject_org = cert.subject.get_attributes_for_oid(NameOID.ORGANIZATION_NAME)
            
            # Issuer details
            issuer_cn = cert.issuer.get_attributes_for_oid(NameOID.COMMON_NAME)
            issuer_org = cert.issuer.get_attributes_for_oid(NameOID.ORGANIZATION_NAME)
            
            # SANs (Subject Alternative Names)
            sans: List[str] = []
            try:
                san_ext = cert.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
                sans = [str(name.value) for name in san_ext.value]
            except Exception:
                pass

            # Validity timestamps
            try:
                not_before = cert.not_valid_before_utc.isoformat()
                not_after = cert.not_valid_after_utc.isoformat()
            except AttributeError:
                # Compatibility with older cryptography versions
                not_before = cert.not_valid_before.isoformat()
                not_after = cert.not_valid_after.isoformat()

            return {
                "subject": {
                    "common_name": subject_cn[0].value if subject_cn else None,
                    "organization": subject_org[0].value if subject_org else None,
                },
                "issuer": {
                    "common_name": issuer_cn[0].value if issuer_cn else None,
                    "organization": issuer_org[0].value if issuer_org else None,
                },
                "serial_number": hex(cert.serial_number),
                "valid_from": not_before,
                "valid_until": not_after,
                "sans": sans[:15]  # Cap to top 15 SANs
            }
        except Exception as e:
            logger.debug(f"Failed to parse X.509 cert: {e}")
            return {}

    def _probe_http(self, host: str, port: int, timeout: float, has_ssl: bool = False) -> Optional[Dict[str, Any]]:
        """
        Attempts HTTP/HTTPS probe to fetch headers, server identification, and page title.
        """
        schemes = ["https", "http"] if has_ssl or port in [443, 8443] else ["http", "https"]

        for scheme in schemes:
            url = f"{scheme}://{host}:{port}/"
            try:
                resp = requests.get(
                    url,
                    timeout=timeout,
                    verify=False,
                    allow_redirects=True,
                    headers={"User-Agent": "Mozilla/5.0 (Tessier-Ashpool Construct/1.0)"}
                )

                # Extract HTML title if present
                title = None
                content_type = resp.headers.get("Content-Type", "")
                if "text/html" in content_type and resp.text:
                    try:
                        soup = BeautifulSoup(resp.text[:8192], "html.parser")
                        if soup.title and soup.title.string:
                            title = soup.title.string.strip()
                    except Exception:
                        pass

                return {
                    "url": url,
                    "status_code": resp.status_code,
                    "server": resp.headers.get("Server"),
                    "headers": dict(resp.headers),
                    "title": title
                }
            except Exception:
                continue

        return None
