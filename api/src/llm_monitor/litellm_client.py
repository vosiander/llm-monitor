"""LiteLLM API client for model management"""
import httpx
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from loguru import logger
from llm_monitor.schema import LiteLLMConfig


class LiteLLMClient:
    """Client for interacting with LiteLLM API"""
    
    def __init__(self, config: LiteLLMConfig):
        self.config = config
        self.base_url = config.url
        self.headers = {
            "Authorization": f"Bearer {config.master_key}",
            "Content-Type": "application/json"
        }
    
    async def check_health(self) -> bool:
        """Check if LiteLLM API is available"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{self.base_url}/health/liveliness",
                    headers=self.headers
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"LiteLLM health check failed: {e}")
            return False
    
    async def create_model(
        self,
        model_id: str,
        model_name: str,
        ollama_model: str,
        api_base: str
    ) -> Dict[str, Any]:
        """
        Create a model in LiteLLM.
        
        Args:
            model_id: Unique model ID in LiteLLM (e.g., "host1-llama3")
            model_name: Model name for load balancing (e.g., "llama3")
            ollama_model: Ollama model name (e.g., "llama3")
            api_base: Ollama host URL (e.g., "http://192.168.1.10:11434")
        
        Returns:
            Response from LiteLLM API
        
        Raises:
            httpx.HTTPError: If the request fails
        """
        now = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        
        model_data = {
            "model_name": model_name,
            "litellm_params": {
                "model": ollama_model,
                "api_base": api_base
            },
            "model_info": {
                "id": model_id,
                "mode": "completion",
                "created_at": now,
                "updated_at": now,
                "created_by": "llm-monitor"
            }
        }
        
        logger.info(f"Creating LiteLLM model: {model_name} (ID: {model_id})")
        logger.debug(f"Model data: {model_data}")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/model/new",
                    headers=self.headers,
                    json=model_data
                )
                response.raise_for_status()
                logger.info(f"Successfully created model {model_name} (ID: {model_id})")
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to create model {model_name} (ID: {model_id}): {e}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Response: {e.response.text}")
            raise
    
    async def get_model_by_name(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get model information by name"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{self.base_url}/model/info",
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    models_data = response.json()
                    if "data" in models_data:
                        for model in models_data["data"]:
                            if model.get("id") == model_name or model.get("model_name") == model_name:
                                return model
                    logger.info(f"Model {model_name} not found in LiteLLM")
                    return None
                else:
                    logger.error(f"Failed to list models: {response.status_code}")
                    return None
        except Exception as e:
            logger.error(f"Exception while getting model {model_name}: {e}")
            return None
    
    async def get_models_for_host(self, host_label: str) -> list[Dict[str, Any]]:
        """
        Get all models for a specific host.
        
        Args:
            host_label: The host label (e.g., "bequiet")
        
        Returns:
            List of models that have model_id starting with "{host_label}-"
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{self.base_url}/model/info",
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    models_data = response.json()
                    if "data" in models_data:
                        # Filter models where id starts with host_label prefix
                        prefix = f"{host_label}-"
                        filtered_models = [
                            model for model in models_data["data"]
                            if model.get("model_info", {}).get("id", "").startswith(prefix)
                        ]
                        logger.info(f"Found {len(filtered_models)} model(s) for host {host_label}")
                        return filtered_models
                    else:
                        logger.info(f"No data field in response")
                        return []
                else:
                    logger.error(f"Failed to list models: {response.status_code}")
                    return []
        except Exception as e:
            logger.error(f"Exception while getting models for host {host_label}: {e}")
            return []
    
    async def delete_model(self, model_id: str) -> Dict[str, Any]:
        """
        Delete a model from LiteLLM.
        
        Args:
            model_id: The unique model ID to delete (e.g., "bequiet-gemma3")
        
        Returns:
            Response from LiteLLM API
        
        Raises:
            httpx.HTTPError: If the request fails
        """
        logger.info(f"Deleting LiteLLM model: {model_id}")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/model/delete",
                    headers=self.headers,
                    json={"id": model_id}
                )
                response.raise_for_status()
                logger.info(f"Successfully deleted model {model_id}")
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to delete model {model_id}: {e}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Response: {e.response.text}")
            raise
