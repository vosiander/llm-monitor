"""Environment configuration for network discovery and LiteLLM"""
import os
import ipaddress
from datetime import datetime
from loguru import logger
from typing import Optional
from llm_monitor.schema import DiscoveryConfig, LiteLLMConfig, DiscoveredHost


def parse_cidr_ranges(ranges_str: str) -> list[str]:
    """
    Parse comma-separated CIDR ranges and validate them.
    
    Args:
        ranges_str: Comma-separated CIDR ranges (e.g., "192.168.1.0/24,10.0.0.0/16")
    
    Returns:
        List of valid CIDR strings
    
    Raises:
        ValueError: If any CIDR range is invalid
    """
    if not ranges_str or not ranges_str.strip():
        raise ValueError("CIDR ranges string is empty")
    
    ranges = [r.strip() for r in ranges_str.split(',') if r.strip()]
    
    if not ranges:
        raise ValueError("No valid CIDR ranges found")
    
    validated_ranges = []
    for cidr in ranges:
        try:
            # Validate the CIDR notation
            network = ipaddress.ip_network(cidr, strict=False)
            validated_ranges.append(str(network))
            logger.debug(f"Validated CIDR range: {network}")
        except ValueError as e:
            raise ValueError(f"Invalid CIDR range '{cidr}': {e}")
    
    return validated_ranges


def load_discovery_config() -> DiscoveryConfig:
    """
    Load discovery configuration from environment variables.
    
    Required environment variables:
        DISCOVERY_CIDR_RANGES: Comma-separated CIDR ranges (e.g., "192.168.1.0/24,10.0.0.0/16")
    
    Optional environment variables:
        DISCOVERY_INTERVAL_SECONDS: Discovery interval (default: 60)
        DISCOVERY_MAX_PARALLEL: Maximum parallel connections (default: 10)
        DISCOVERY_TIMEOUT_SECONDS: Connection timeout (default: 2.0)
        DISCOVERY_PORT: Port to scan (default: 11434)
    
    Returns:
        DiscoveryConfig object
    
    Raises:
        ValueError: If required environment variables are missing or invalid
    """
    logger.info("Loading discovery configuration from environment variables")
    
    # Required: CIDR ranges
    cidr_ranges_str = os.getenv('DISCOVERY_CIDR_RANGES')
    if not cidr_ranges_str:
        raise ValueError(
            "Required environment variable DISCOVERY_CIDR_RANGES is not set. "
            "Example: DISCOVERY_CIDR_RANGES=192.168.1.0/24,10.0.0.0/16"
        )
    
    cidr_ranges = parse_cidr_ranges(cidr_ranges_str)
    logger.info(f"Parsed CIDR ranges: {cidr_ranges}")
    
    # Optional: Interval seconds
    interval_seconds = int(os.getenv('DISCOVERY_INTERVAL_SECONDS', '60'))
    if interval_seconds < 1:
        raise ValueError(f"DISCOVERY_INTERVAL_SECONDS must be at least 1, got {interval_seconds}")
    logger.debug(f"Discovery interval: {interval_seconds} seconds")
    
    # Optional: Max parallel connections
    max_parallel = int(os.getenv('DISCOVERY_MAX_PARALLEL', '10'))
    if max_parallel < 1:
        raise ValueError(f"DISCOVERY_MAX_PARALLEL must be at least 1, got {max_parallel}")
    logger.debug(f"Max parallel connections: {max_parallel}")
    
    # Optional: Timeout seconds
    timeout_seconds = float(os.getenv('DISCOVERY_TIMEOUT_SECONDS', '2.0'))
    if timeout_seconds <= 0:
        raise ValueError(f"DISCOVERY_TIMEOUT_SECONDS must be positive, got {timeout_seconds}")
    logger.debug(f"Connection timeout: {timeout_seconds} seconds")
    
    # Optional: Port
    port = int(os.getenv('DISCOVERY_PORT', '11434'))
    if port < 1 or port > 65535:
        raise ValueError(f"DISCOVERY_PORT must be between 1 and 65535, got {port}")
    logger.debug(f"Discovery port: {port}")
    
    config = DiscoveryConfig(
        cidr_ranges=cidr_ranges,
        interval_seconds=interval_seconds,
        max_parallel=max_parallel,
        timeout_seconds=timeout_seconds,
        port=port
    )
    
    logger.info(f"Discovery configuration loaded successfully: {len(cidr_ranges)} CIDR range(s)")
    return config


def load_litellm_config() -> Optional[LiteLLMConfig]:
    """
    Load LiteLLM configuration from environment variables.
    
    Optional environment variables:
        LITELLM_URL: LiteLLM API base URL
        LITELLM_MASTER_KEY: Master API key for authentication
    
    Returns:
        LiteLLMConfig object if configured, None otherwise
    """
    litellm_url = os.getenv('LITELLM_URL')
    litellm_master_key = os.getenv('LITELLM_MASTER_KEY')
    
    if not litellm_url or not litellm_master_key:
        logger.info("LiteLLM not configured (LITELLM_URL and/or LITELLM_MASTER_KEY not set)")
        return None
    
    logger.info(f"LiteLLM configuration loaded: {litellm_url}")
    
    return LiteLLMConfig(
        url=litellm_url.rstrip('/'),
        master_key=litellm_master_key
    )


def load_endpoints_refresh_interval() -> int:
    """
    Load endpoints refresh interval from environment variables.
    
    Optional environment variable:
        LLM_TRIGGER_ENDPOINTS_IN_SECONDS: Interval in seconds for refreshing endpoints cache (default: 10)
    
    Returns:
        Refresh interval in seconds
    """
    interval = int(os.getenv('LLM_TRIGGER_ENDPOINTS_IN_SECONDS', '30'))
    
    if interval < 1:
        logger.warning(f"LLM_TRIGGER_ENDPOINTS_IN_SECONDS must be at least 1, got {interval}. Using default: 10")
        interval = 10
    
    logger.info(f"Endpoints refresh interval: {interval} seconds")
    return interval


def parse_ollama_hosts(hosts_str: str) -> list[tuple[str, int]]:
    """
    Parse comma-separated ip:port pairs and validate them.
    
    Args:
        hosts_str: Comma-separated ip:port pairs (e.g., "192.168.1.10:11434,192.168.1.20:11434")
    
    Returns:
        List of (ip, port) tuples
    
    Raises:
        ValueError: If any host string is invalid
    """
    if not hosts_str or not hosts_str.strip():
        raise ValueError("Ollama hosts string is empty")
    
    hosts = [h.strip() for h in hosts_str.split(',') if h.strip()]
    
    if not hosts:
        raise ValueError("No valid Ollama hosts found")
    
    validated_hosts = []
    for host_str in hosts:
        try:
            # Parse ip:port format
            if ':' not in host_str:
                raise ValueError(f"Host must be in format 'ip:port', got '{host_str}'")
            
            parts = host_str.split(':')
            if len(parts) != 2:
                raise ValueError(f"Host must have exactly one colon, got '{host_str}'")
            
            ip_str, port_str = parts
            
            # Validate IP address
            try:
                ipaddress.ip_address(ip_str)
            except ValueError:
                raise ValueError(f"Invalid IP address: '{ip_str}'")
            
            # Validate port
            try:
                port = int(port_str)
                if port < 1 or port > 65535:
                    raise ValueError(f"Port must be between 1 and 65535, got {port}")
            except ValueError as e:
                raise ValueError(f"Invalid port: '{port_str}': {e}")
            
            validated_hosts.append((ip_str, port))
            logger.debug(f"Validated Ollama host: {ip_str}:{port}")
            
        except ValueError as e:
            raise ValueError(f"Invalid Ollama host '{host_str}': {e}")
    
    return validated_hosts


def load_ollama_hosts() -> list[DiscoveredHost]:
    """
    Load predefined Ollama hosts from OLLAMA_HOSTS environment variable.
    
    Optional environment variable:
        OLLAMA_HOSTS: Comma-separated ip:port pairs (e.g., "192.168.1.10:11434,192.168.1.20:11434")
    
    Returns:
        List of DiscoveredHost objects with is_predefined=True, or empty list if not configured
    """
    hosts_str = os.getenv('OLLAMA_HOSTS')
    
    if not hosts_str:
        logger.debug("OLLAMA_HOSTS environment variable not set")
        return []
    
    try:
        host_tuples = parse_ollama_hosts(hosts_str)
        logger.info(f"Parsed {len(host_tuples)} predefined Ollama host(s)")
        
        discovered_hosts = []
        for ip, port in host_tuples:
            host = DiscoveredHost(
                ip=ip,
                port=port,
                hostname=None,  # Will be resolved during first check
                last_seen=datetime.now(),
                is_online=False,  # Will be checked during initialization
                is_predefined=True
            )
            discovered_hosts.append(host)
            logger.info(f"Added predefined host: {ip}:{port}")
        
        return discovered_hosts
        
    except ValueError as e:
        logger.error(f"Failed to parse OLLAMA_HOSTS: {e}")
        return []
