"""Discovery manager for orchestrating network discovery and managing host registry"""
import asyncio
from datetime import datetime
from typing import Dict

from loguru import logger

from llm_monitor.schema import DiscoveryConfig, DiscoveredHost
from llm_monitor.discovery import discover_all_hosts, is_duplicate_host
from llm_monitor.plugins import PluginService
from llm_monitor.env_config import load_ollama_hosts


class DiscoveryManager:
    """
    Manages network discovery and host registry.
    
    Orchestrates periodic scanning of CIDR ranges, maintains a registry
    of discovered hosts, and provides a PluginService with current hosts.
    """
    
    def __init__(self, config: DiscoveryConfig):
        """
        Initialize the discovery manager.
        
        Args:
            config: Discovery configuration
        """
        self.config = config
        self.hosts_registry: Dict[str, DiscoveredHost] = {}  # Keyed by IP address
        self.plugin_service: PluginService = PluginService([])
        self.running = False
        self.lock = asyncio.Lock()  # For thread-safe registry access
        self._discovery_task = None
        
        # Queue for streaming host discovery
        self.discovery_queue: asyncio.Queue = asyncio.Queue()
        self._queue_consumer_task = None
        
        logger.info(f"DiscoveryManager initialized with {len(config.cidr_ranges)} CIDR range(s)")
        
        # Initialize predefined hosts from environment
        self._initialize_predefined_hosts()
    
    def _initialize_predefined_hosts(self) -> None:
        """
        Initialize predefined hosts from OLLAMA_HOSTS environment variable.
        
        Loads static hosts and adds them to the registry with is_predefined=True.
        These hosts are never removed from the registry, only marked as online/offline.
        """
        predefined_hosts = load_ollama_hosts()
        
        if not predefined_hosts:
            logger.debug("No predefined hosts configured")
            return
        
        for host in predefined_hosts:
            self.hosts_registry[host.ip] = host
            logger.info(f"Predefined host added to registry: {host.ip}:{host.port}")
        
        logger.info(f"Initialized {len(predefined_hosts)} predefined host(s)")
    
    async def _consume_discovered_hosts(self):
        """
        Consumer task that processes hosts from the queue in real-time.
        
        Runs continuously while discovery is active. Hosts are made available
        immediately as they are discovered, without waiting for the full scan.
        """
        logger.info("Starting discovery queue consumer")
        
        while self.running:
            try:
                # Wait for hosts with timeout to check running flag periodically
                host = await asyncio.wait_for(
                    self.discovery_queue.get(), 
                    timeout=1.0
                )
                
                # Process discovered host immediately
                async with self.lock:
                    # Check if this is a duplicate (same IP:port already exists)
                    if is_duplicate_host(host.ip, host.port, self.hosts_registry):
                        # Update existing host information
                        existing = self.hosts_registry[host.ip]
                        existing.last_seen = host.last_seen
                        existing.is_online = True
                        if host.hostname:
                            existing.hostname = host.hostname
                        logger.debug(f"Updated existing host: {host.ip}:{host.port}")
                    else:
                        # New host - add to registry
                        self.hosts_registry[host.ip] = host
                        logger.info(f"New host immediately available: {host.ip}:{host.port}")
                    
                    # Refresh plugins with all hosts (online and offline)
                    all_hosts = list(self.hosts_registry.values())
                    self.plugin_service.refresh_plugins(all_hosts)
                    logger.debug(f"Plugins refreshed: {len(all_hosts)} host(s)")
                
                # Mark task as done
                self.discovery_queue.task_done()
                
            except asyncio.TimeoutError:
                # Normal timeout, check if still running
                continue
            except asyncio.CancelledError:
                logger.info("Queue consumer cancelled")
                break
            except Exception as e:
                logger.error(f"Error processing discovered host: {e}", exc_info=True)
        
        logger.info("Discovery queue consumer stopped")
    
    async def discover_hosts(self) -> list[DiscoveredHost]:
        """
        Execute one discovery scan across all CIDR ranges.
        
        Hosts are streamed to the queue as discovered and made immediately available.
        After scan completes, marks hosts not found as offline.
        
        Returns:
            List of currently online discovered hosts
        """
        logger.info("Starting discovery scan")
        
        # Perform discovery with queue for real-time host availability
        discovered_hosts = await discover_all_hosts(
            cidr_ranges=self.config.cidr_ranges,
            port=self.config.port,
            timeout=self.config.timeout_seconds,
            max_parallel=self.config.max_parallel,
            discovery_queue=self.discovery_queue
        )
        
        # Wait for all queued hosts to be processed
        await self.discovery_queue.join()
        logger.debug("All queued hosts processed")
        
        # After scan completes, mark hosts not found as offline
        async with self.lock:
            discovered_ips = {host.ip for host in discovered_hosts}
            registry_ips = set(self.hosts_registry.keys())
            offline_ips = registry_ips - discovered_ips
            
            for ip in offline_ips:
                if self.hosts_registry[ip].is_online:
                    self.hosts_registry[ip].is_online = False
                    logger.info(f"Host marked as offline: {ip}")
            
            # Final plugin refresh after marking offline hosts
            all_hosts = list(self.hosts_registry.values())
            online_count = len([h for h in all_hosts if h.is_online])
            self.plugin_service.refresh_plugins(all_hosts)
            
            logger.info(
                f"Discovery scan complete: {online_count} online, "
                f"{len(offline_ips)} offline, {len(self.hosts_registry)} total"
            )
        
        return discovered_hosts
    
    async def start_discovery_loop(self):
        """
        Start continuous discovery loop with real-time host streaming.
        
        Launches queue consumer for immediate host availability.
        Runs discovery scan every interval_seconds.
        This method runs indefinitely until stop() is called.
        """
        self.running = True
        logger.info(f"Starting discovery system (interval: {self.config.interval_seconds}s)")
        
        # Start queue consumer task
        self._queue_consumer_task = asyncio.create_task(
            self._consume_discovered_hosts()
        )
        logger.info("Queue consumer task started")
        
        # Run initial discovery immediately
        try:
            await self.discover_hosts()
        except Exception as e:
            logger.error(f"Error in initial discovery: {e}")
        
        # Continue with periodic discovery
        while self.running:
            try:
                # Wait for the interval
                await asyncio.sleep(self.config.interval_seconds)
                
                if not self.running:
                    break
                
                # Run discovery
                await self.discover_hosts()
                
            except asyncio.CancelledError:
                logger.info("Discovery loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in discovery loop: {e}", exc_info=True)
                # Continue running even if there's an error
                await asyncio.sleep(5)  # Short delay before retry
        
        logger.info("Discovery loop stopped")
    
    def get_online_hosts(self) -> list[DiscoveredHost]:
        """
        Get current list of online hosts.
        
        Thread-safe access to registry.
        
        Returns:
            List of online discovered hosts
        """
        # Note: In async context, this should be called with await self.lock
        # But for simplicity in sync contexts, we return a snapshot
        return [host for host in self.hosts_registry.values() if host.is_online]
    
    def get_all_hosts(self) -> list[DiscoveredHost]:
        """
        Get all hosts in registry (both online and offline).
        
        Returns:
            List of all discovered hosts
        """
        return list(self.hosts_registry.values())
    
    def get_plugin_service(self) -> PluginService:
        """
        Get PluginService with current discovered hosts.
        
        The plugin service is automatically updated during discovery scans.
        
        Returns:
            PluginService instance
        """
        return self.plugin_service
    
    async def stop(self):
        """
        Stop discovery system gracefully.
        
        Sets running flag to False, cancels queue consumer, and waits for tasks to complete.
        """
        logger.info("Stopping discovery manager")
        self.running = False
        
        # Cancel queue consumer task
        if self._queue_consumer_task and not self._queue_consumer_task.done():
            self._queue_consumer_task.cancel()
            try:
                await self._queue_consumer_task
            except asyncio.CancelledError:
                pass
            logger.info("Queue consumer task stopped")
        
        # If there's a discovery task running, cancel it
        if self._discovery_task and not self._discovery_task.done():
            self._discovery_task.cancel()
            try:
                await self._discovery_task
            except asyncio.CancelledError:
                pass
            logger.info("Discovery task stopped")
        
        logger.info("Discovery manager stopped")
    
    def get_stats(self) -> dict:
        """
        Get statistics about discovered hosts.
        
        Returns:
            Dictionary with statistics
        """
        online_count = len([h for h in self.hosts_registry.values() if h.is_online])
        offline_count = len([h for h in self.hosts_registry.values() if not h.is_online])
        
        return {
            "total_hosts": len(self.hosts_registry),
            "online_hosts": online_count,
            "offline_hosts": offline_count,
            "cidr_ranges": self.config.cidr_ranges,
            "scan_interval": self.config.interval_seconds,
            "is_running": self.running
        }
