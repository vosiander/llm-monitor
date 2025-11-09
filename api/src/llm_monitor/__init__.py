from llm_monitor.discovery_manager import DiscoveryManager
from llm_monitor.schema import DiscoveryConfig


# Global discovery manager instance
_discovery_manager_instance = None


def hello() -> str:
    return "Hello from llm-monitor!"


def init_discovery_manager(config: DiscoveryConfig) -> DiscoveryManager:
    """
    Initialize the global discovery manager instance.
    
    Args:
        config: Discovery configuration
    
    Returns:
        DiscoveryManager instance
    """
    global _discovery_manager_instance
    if _discovery_manager_instance is None:
        _discovery_manager_instance = DiscoveryManager(config)
    return _discovery_manager_instance


def get_discovery_manager() -> DiscoveryManager:
    """
    Get the global discovery manager instance.
    
    Returns:
        DiscoveryManager instance
    
    Raises:
        RuntimeError: If discovery manager not initialized
    """
    if _discovery_manager_instance is None:
        raise RuntimeError("DiscoveryManager not initialized. Call init_discovery_manager() first.")
    return _discovery_manager_instance
