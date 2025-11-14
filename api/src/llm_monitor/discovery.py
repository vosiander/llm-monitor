"""Network discovery for Ollama hosts"""
import asyncio
import ipaddress
import socket
from datetime import datetime
from typing import Optional

import aiohttp
from loguru import logger

from llm_monitor.schema import DiscoveredHost


def is_duplicate_host(ip: str, port: int, existing_hosts: dict[str, DiscoveredHost]) -> bool:
    """
    Check if host with same ip:port already exists in registry.
    
    Args:
        ip: IP address to check
        port: Port to check
        existing_hosts: Dictionary of existing hosts (keyed by label)
    
    Returns:
        True if duplicate exists, False otherwise
    """
    for host in existing_hosts.values():
        if host.ip == ip and host.port == port:
            logger.trace(f"Duplicate host found: {ip}:{port}")
            return True
    return False


async def resolve_hostname(ip: str) -> Optional[str]:
    """
    Resolve IP address to hostname using reverse DNS lookup.
    
    Uses asyncio.run_in_executor to avoid blocking the event loop
    during the potentially slow DNS lookup.
    
    Args:
        ip: IP address to resolve
    
    Returns:
        Hostname if resolution succeeds, None otherwise
    """
    try:
        loop = asyncio.get_event_loop()
        hostname, _, _ = await loop.run_in_executor(
            None, socket.gethostbyaddr, ip
        )
        logger.debug(f"Resolved {ip} to hostname: {hostname}")
        return hostname
    except (socket.herror, socket.gaierror) as e:
        logger.trace(f"Could not resolve hostname for {ip}: {e}")
        return None
    except Exception as e:
        logger.trace(f"Unexpected error resolving hostname for {ip}: {e}")
        return None


async def validate_ollama_api(
    ip: str,
    port: int,
    session: aiohttp.ClientSession,
    timeout: float
) -> bool:
    """
    Validate that /api/ps endpoint responds correctly.
    
    Args:
        ip: IP address to check
        port: Port number to check
        session: aiohttp session for HTTP requests
        timeout: Timeout in seconds
    
    Returns:
        True if API responds with 200 status, False otherwise
    """
    url = f"http://{ip}:{port}/api/ps"
    
    try:
        async with session.get(
            url,
            timeout=aiohttp.ClientTimeout(total=timeout)
        ) as response:
            if response.status == 200:
                # Try to parse JSON to ensure it's a valid Ollama response
                data = await response.json()
                # Ollama API should return a dict with 'models' key
                if isinstance(data, dict) and 'models' in data:
                    logger.debug(f"Valid Ollama API found at {ip}:{port}")
                    return True
                else:
                    logger.trace(f"Invalid response format from {ip}:{port}")
                    return False
            else:
                logger.trace(f"API endpoint returned status {response.status} for {ip}:{port}")
                return False
    except aiohttp.ClientError as e:
        logger.trace(f"HTTP error validating {ip}:{port}: {e}")
        return False
    except asyncio.TimeoutError:
        logger.trace(f"Timeout validating API at {ip}:{port}")
        return False
    except Exception as e:
        logger.trace(f"Unexpected error validating {ip}:{port}: {e}")
        return False


async def check_ollama_host(
    ip: str,
    port: int,
    session: aiohttp.ClientSession,
    semaphore: asyncio.Semaphore,
    timeout: float,
    discovery_queue: Optional[asyncio.Queue] = None
) -> Optional[DiscoveredHost]:
    """
    Check if a specific IP has Ollama running.
    
    First does TCP port check, then validates /api/ps endpoint.
    If discovery_queue is provided, pushes discovered hosts immediately.
    
    Args:
        ip: IP address to check
        port: Port number to check
        session: aiohttp session for HTTP requests
        semaphore: Semaphore to limit concurrent connections
        timeout: Timeout in seconds
        discovery_queue: Optional queue for streaming discovered hosts
    
    Returns:
        DiscoveredHost if valid Ollama host found, None otherwise
    """
    async with semaphore:
        try:
            # First, attempt TCP connection to check if port is open
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(ip, port),
                    timeout=timeout
                )
                writer.close()
                await writer.wait_closed()
                logger.trace(f"Port {port} is open on {ip}")
            except (asyncio.TimeoutError, ConnectionRefusedError, OSError) as e:
                logger.trace(f"Port {port} not accessible on {ip}: {e}")
                return None
            
            # If port is open, validate it's actually Ollama
            if await validate_ollama_api(ip, port, session, timeout):
                # Attempt to resolve hostname for better labeling
                hostname = await resolve_hostname(ip)
                
                host = DiscoveredHost(
                    ip=ip,
                    port=port,
                    hostname=hostname,
                    last_seen=datetime.now(),
                    is_online=True
                )
                
                # Push to queue immediately for real-time availability
                if discovery_queue is not None:
                    await discovery_queue.put(host)
                    logger.debug(f"Host {ip} pushed to discovery queue")
                
                if hostname:
                    logger.info(f"Discovered Ollama host: {ip}:{port} (hostname: {hostname})")
                else:
                    logger.info(f"Discovered Ollama host: {ip}:{port}")
                return host
            else:
                logger.trace(f"Port {port} on {ip} is not Ollama")
                return None
                
        except Exception as e:
            logger.trace(f"Error checking {ip}:{port}: {e}")
            return None


async def scan_cidr_range(
    cidr: str,
    port: int,
    timeout: float,
    semaphore: asyncio.Semaphore,
    discovery_queue: Optional[asyncio.Queue] = None
) -> list[DiscoveredHost]:
    """
    Scan a CIDR range for Ollama hosts.
    
    Args:
        cidr: CIDR range to scan (e.g., "192.168.1.0/24")
        port: Port to scan for Ollama
        timeout: Connection timeout in seconds
        semaphore: Semaphore to limit concurrent connections
        discovery_queue: Optional queue for streaming discovered hosts
    
    Returns:
        List of discovered Ollama hosts
    """
    try:
        network = ipaddress.ip_network(cidr, strict=False)
        logger.info(f"Scanning CIDR range: {network} ({network.num_addresses} addresses)")
        
        # Create aiohttp session with connection pooling
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=10)
        async with aiohttp.ClientSession(connector=connector) as session:
            # Create tasks for all IPs in the network
            tasks = []
            for ip in network.hosts():
                task = check_ollama_host(
                    str(ip),
                    port,
                    session,
                    semaphore,
                    timeout,
                    discovery_queue
                )
                tasks.append(task)
            
            # For very small networks (like /32 or single IPs), network.hosts() might be empty
            # In that case, check the network address itself
            if not tasks:
                task = check_ollama_host(
                    str(network.network_address),
                    port,
                    session,
                    semaphore,
                    timeout,
                    discovery_queue
                )
                tasks.append(task)
            
            # Wait for all tasks to complete
            logger.debug(f"Checking {len(tasks)} IP addresses in {cidr}")
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out None results and exceptions
            discovered_hosts = []
            for result in results:
                if isinstance(result, DiscoveredHost):
                    discovered_hosts.append(result)
                elif isinstance(result, Exception):
                    logger.warning(f"Task failed with exception: {result}")
            
            logger.info(f"Scan complete for {cidr}: found {len(discovered_hosts)} host(s)")
            return discovered_hosts
            
    except ValueError as e:
        logger.error(f"Invalid CIDR range '{cidr}': {e}")
        return []
    except Exception as e:
        logger.error(f"Error scanning CIDR range '{cidr}': {e}")
        return []


async def discover_all_hosts(
    cidr_ranges: list[str],
    port: int,
    timeout: float,
    max_parallel: int,
    discovery_queue: Optional[asyncio.Queue] = None
) -> list[DiscoveredHost]:
    """
    Discover Ollama hosts across multiple CIDR ranges.
    
    Args:
        cidr_ranges: List of CIDR ranges to scan
        port: Port to scan for Ollama
        timeout: Connection timeout in seconds
        max_parallel: Maximum number of parallel connections
        discovery_queue: Optional queue for streaming discovered hosts
    
    Returns:
        List of all discovered Ollama hosts
    """
    logger.info(f"Starting discovery across {len(cidr_ranges)} CIDR range(s)")
    
    # Create semaphore to limit concurrent connections
    semaphore = asyncio.Semaphore(max_parallel)
    
    # Scan all CIDR ranges in parallel
    tasks = [
        scan_cidr_range(cidr, port, timeout, semaphore, discovery_queue)
        for cidr in cidr_ranges
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Flatten results and filter out errors
    all_hosts = []
    for result in results:
        if isinstance(result, list):
            all_hosts.extend(result)
        elif isinstance(result, Exception):
            logger.error(f"CIDR scan failed: {result}")
    
    logger.info(f"Discovery complete: found {len(all_hosts)} total host(s)")
    return all_hosts
