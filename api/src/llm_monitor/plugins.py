from loguru import logger
from llm_monitor.schema import ProcessStatus, DiscoveredHost


class Plugin:
    """Base plugin class"""
    def ps(self) -> ProcessStatus:
        raise NotImplementedError("Each plugin must implement the ps method")


class PluginService:
    """
    Service for managing plugins dynamically based on discovered hosts.
    
    Creates and manages Ollama plugin instances for each discovered host.
    """
    
    def __init__(self, hosts: list[DiscoveredHost]):
        """
        Initialize plugin service with discovered hosts.
        
        Args:
            hosts: List of discovered Ollama hosts
        """
        self.hosts = hosts
        self.plugins = self._create_plugins(hosts)
        logger.info(f"PluginService initialized with {len(self.plugins)} plugin(s)")
    
    def _create_plugins(self, hosts: list[DiscoveredHost]) -> dict:
        """
        Create Ollama plugin instances for each discovered host.
        
        Args:
            hosts: List of discovered hosts
        
        Returns:
            Dictionary of plugin instances keyed by label
        """
        from plugins.ollama import Ollama
        
        plugins = {}
        for host in hosts:
            # Create a unique label for each host
            # Prefer hostname (short form) over IP address
            if host.hostname:
                label = host.hostname
            else:
                # Fallback to IP-based label
                label = f"ollama-{host.ip.replace('.', '-')}"
            
            try:
                # Create Ollama plugin instance with IP and port
                plugin = Ollama(ip=host.ip, port=host.port)
                plugins[label] = plugin
                logger.debug(f"Created plugin '{label}' for {host.ip}:{host.port}")
            except Exception as e:
                logger.error(f"Failed to create plugin for {host.ip}:{host.port}: {e}")
        
        return plugins
    
    def refresh_plugins(self, hosts: list[DiscoveredHost]):
        """
        Update plugin list based on current hosts.
        
        This is called by the discovery manager when hosts change.
        
        Args:
            hosts: Updated list of discovered hosts
        """
        logger.info(f"Refreshing plugins with {len(hosts)} host(s)")
        self.hosts = hosts
        self.plugins = self._create_plugins(hosts)
        logger.info(f"Plugin refresh complete: {len(self.plugins)} active plugin(s)")
    
    def llm_endpoints(self):
        """
        Fetch status from all LLM endpoints.
        
        Returns:
            Dictionary of plugin labels to ProcessStatus objects
        """
        logger.info("Fetching LLM endpoints")
        endpoints = {}
        
        for label, plugin in self.plugins.items():
            try:
                logger.debug(f"Fetching endpoints for plugin {label}")
                result = plugin.ps()
                if result:
                    # Add IP and port from plugin
                    result.ip = plugin.ip
                    result.port = plugin.port
                    endpoints[label] = result
                    logger.debug(f"Endpoints for plugin {label}: {result}")
            except Exception as e:
                logger.error(f"Failed to get endpoints for plugin {label}: {e}")
                # Return offline status for failed plugins
                endpoints[label] = ProcessStatus(
                    models=[], 
                    is_online=False,
                    ip=plugin.ip,
                    port=plugin.port
                )
        
        logger.info(f"Fetched endpoints: {len(endpoints)} endpoint(s)")
        return endpoints
