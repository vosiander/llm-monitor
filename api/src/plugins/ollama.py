import requests
from loguru import logger
from llm_monitor.plugins import Plugin
from llm_monitor.schema import Model, ProcessStatus


class Ollama(Plugin):
    """Ollama plugin for monitoring Ollama instances"""
    
    def __init__(self, ip: str, port: int = 11434, timeout: float = 2.0):
        """
        Initialize Ollama plugin.
        
        Args:
            ip: IP address of the Ollama host
            port: Port number (default: 11434)
            timeout: Request timeout in seconds (default: 2.0)
        """
        self.ip = ip
        self.port = port
        self.timeout = timeout
        self.url = f"http://{ip}:{port}"
        logger.debug(f"Ollama plugin initialized for {self.url}")

    def get_version(self) -> str | None:
        """
        Get Ollama version from the API.
        
        Returns:
            Version string if available, None otherwise
        """
        try:
            response = requests.get(f"{self.url}/api/version", timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            version = data.get('version')
            
            if version:
                logger.debug(f"Ollama version at {self.url}: {version}")
            
            return version
            
        except requests.exceptions.Timeout:
            logger.debug(f"Timeout getting version from Ollama at {self.url}")
            return None
        except requests.exceptions.ConnectionError:
            logger.debug(f"Connection error getting version from Ollama at {self.url}")
            return None
        except requests.exceptions.HTTPError as e:
            logger.debug(f"HTTP error getting version from Ollama at {self.url}: {e}")
            return None
        except Exception as e:
            logger.debug(f"Unexpected error getting version from Ollama at {self.url}: {e}")
            return None

    def ps(self) -> ProcessStatus:
        """
        Get process status from Ollama API.
        
        Returns:
            ProcessStatus with list of running models and version
        """
        logger.info(f"Running ollama plugin for {self.url}")
        
        try:
            response = requests.get(f"{self.url}/api/ps", timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            logger.debug(f"Response from {self.url}: {data}")
            
            # Parse models from response
            models = [Model(**model) for model in data.get('models', [])]
            
            # Fetch version
            version = self.get_version()
            
            result = ProcessStatus(
                models=models,
                is_online=True,
                version=version
            )
            
            logger.info(f"Ollama at {self.url}: {len(models)} model(s) running, version: {version}")
            return result
            
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout connecting to Ollama at {self.url}")
            return ProcessStatus(models=[], is_online=False, version=None)
        except requests.exceptions.ConnectionError:
            logger.warning(f"Connection error to Ollama at {self.url}")
            return ProcessStatus(models=[], is_online=False, version=None)
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error from Ollama at {self.url}: {e}")
            return ProcessStatus(models=[], is_online=False, version=None)
        except Exception as e:
            logger.error(f"Unexpected error querying Ollama at {self.url}: {e}")
            return ProcessStatus(models=[], is_online=False, version=None)
