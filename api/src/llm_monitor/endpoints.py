from loguru import logger
from fastapi import APIRouter, Response, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
import httpx
from typing import List, Dict, Any, Optional
from llm_monitor import get_discovery_manager
from llm_monitor.schema import BulkCreateRequest, BulkPurgeRequest
from llm_monitor.litellm_client import LiteLLMClient
from llm_monitor.env_config import load_litellm_config
from llm_monitor.endpoints_cache import get_endpoints_cache

router = APIRouter()

# Global LiteLLM client instance
_litellm_client: Optional[LiteLLMClient] = None


def get_litellm_client() -> Optional[LiteLLMClient]:
    """Get or initialize the LiteLLM client"""
    global _litellm_client
    if _litellm_client is None:
        config = load_litellm_config()
        if config:
            _litellm_client = LiteLLMClient(config)
    return _litellm_client


class PullRequest(BaseModel):
    model_name: str


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    stream: bool = True
    model: str | None = None


class DeleteRequest(BaseModel):
    model_name: str


@router.get("")
async def get_index():
    """
    Get status of all discovered Ollama endpoints from cache.
    
    The endpoint data is cached and refreshed periodically by a background task
    to reduce load when multiple clients are polling this endpoint.
    
    Returns:
        JSON response with endpoints and their status
    """
    logger.trace("GET /llmm endpoint called (serving from cache)")
    
    # Get cached endpoints
    endpoints_cache = get_endpoints_cache()
    json_endpoints = await endpoints_cache.get_endpoints()
    
    logger.trace(f"Returning {len(json_endpoints)} endpoint(s) from cache")
    
    return Response(
        content=json.dumps({"endpoints": json_endpoints}),
        media_type="application/json"
    )


@router.get("/{label}/models")
async def get_models(label: str):
    """
    Get available models for a specific Ollama host.
    
    Args:
        label: The host label
    
    Returns:
        JSON response with list of model names
    """
    logger.info(f"GET /llmm/{label}/models called")
    
    # Get discovery manager and plugin service
    discovery_manager = get_discovery_manager()
    plugin_service = discovery_manager.get_plugin_service()
    
    # Find the plugin for this label
    if label not in plugin_service.plugins:
        logger.error(f"Plugin not found for label: {label}")
        raise HTTPException(status_code=404, detail=f"Host '{label}' not found")
    
    plugin = plugin_service.plugins[label]
    ollama_url = f"http://{plugin.ip}:{plugin.port}/api/tags"
    
    logger.info(f"Fetching models from {ollama_url}")
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(ollama_url)
            response.raise_for_status()
            data = response.json()
            
            # Extract model names from the response
            models = [model["name"] for model in data.get("models", [])]
            logger.info(f"Found {len(models)} model(s) for {label}")
            
            return Response(
                content=json.dumps({"models": models}),
                media_type="application/json"
            )
    except httpx.HTTPError as e:
        logger.error(f"Failed to fetch models from {label}: {e}")
        return Response(
            content=json.dumps({"models": []}),
            media_type="application/json"
        )
    except Exception as e:
        logger.error(f"Unexpected error fetching models from {label}: {e}")
        return Response(
            content=json.dumps({"models": []}),
            media_type="application/json"
        )


@router.post("/{label}/pull")
async def pull_model(label: str, request: PullRequest):
    """
    Pull a model on a specific Ollama host with progress streaming.
    
    Args:
        label: The host label
        request: Pull request containing model_name
    
    Returns:
        Streaming response with pull progress
    """
    logger.info(f"POST /llmm/{label}/pull called for model: {request.model_name}")
    
    # Get discovery manager and plugin service
    discovery_manager = get_discovery_manager()
    plugin_service = discovery_manager.get_plugin_service()
    
    # Find the plugin for this label
    if label not in plugin_service.plugins:
        logger.error(f"Plugin not found for label: {label}")
        raise HTTPException(status_code=404, detail=f"Host '{label}' not found")
    
    plugin = plugin_service.plugins[label]
    ollama_url = f"http://{plugin.ip}:{plugin.port}/api/pull"
    
    logger.info(f"Proxying pull request to {ollama_url}")
    
    async def stream_pull_progress():
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream(
                    "POST",
                    ollama_url,
                    json={"name": request.model_name},
                ) as response:
                    if response.status_code != 200:
                        error_msg = await response.aread()
                        logger.error(f"Pull failed: {error_msg}")
                        yield json.dumps({"error": error_msg.decode()}) + "\n"
                        return
                    
                    async for chunk in response.aiter_lines():
                        if chunk:
                            logger.debug(f"Pull progress: {chunk}")
                            yield chunk + "\n"
        except Exception as e:
            logger.error(f"Error during pull: {e}")
            yield json.dumps({"error": str(e)}) + "\n"
    
    return StreamingResponse(stream_pull_progress(), media_type="application/x-ndjson")


@router.post("/{label}/chat")
async def chat_completion(label: str, request: ChatRequest):
    """
    OpenAI-compatible chat endpoint for a specific Ollama host.
    
    Args:
        label: The host label
        request: Chat request with messages
    
    Returns:
        Streaming response with chat completion
    """
    logger.info(f"POST /llmm/{label}/chat called with {len(request.messages)} message(s)")
    
    # Get discovery manager and plugin service
    discovery_manager = get_discovery_manager()
    plugin_service = discovery_manager.get_plugin_service()
    
    # Find the plugin for this label
    if label not in plugin_service.plugins:
        logger.error(f"Plugin not found for label: {label}")
        raise HTTPException(status_code=404, detail=f"Host '{label}' not found")
    
    plugin = plugin_service.plugins[label]
    ollama_url = f"http://{plugin.ip}:{plugin.port}/v1/chat/completions"
    
    logger.info(f"Proxying chat request to {ollama_url}")
    
    # Convert messages to dict format
    messages_dict = [msg.model_dump() for msg in request.messages]
    
    async def stream_chat_response():
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream(
                    "POST",
                    ollama_url,
                    json={
                        "messages": messages_dict,
                        "stream": request.stream,
                        "model": request.model or "llama3"
                    },
                ) as response:
                    if response.status_code != 200:
                        error_msg = await response.aread()
                        logger.error(f"Chat failed: {error_msg}")
                        yield json.dumps({"error": error_msg.decode()}) + "\n"
                        return
                    
                    async for chunk in response.aiter_bytes():
                        if chunk:
                            yield chunk
        except Exception as e:
            logger.error(f"Error during chat: {e}")
            yield json.dumps({"error": str(e)}).encode() + b"\n"
    
    return StreamingResponse(stream_chat_response(), media_type="text/event-stream")


@router.delete("/{label}/delete")
async def delete_model(label: str, request: DeleteRequest):
    """
    Delete a model from a specific Ollama host.

    Args:
        label: The host label
        request: Delete request containing model_name

    Returns:
        JSON response with success or error message
    """
    logger.info(f"DELETE /llmm/{label}/delete called for model: {request.model_name}")

    # Get discovery manager and plugin service
    discovery_manager = get_discovery_manager()
    plugin_service = discovery_manager.get_plugin_service()

    # Find the plugin for this label
    if label not in plugin_service.plugins:
        logger.error(f"Plugin not found for label: {label}")
        raise HTTPException(status_code=404, detail=f"Host '{label}' not found")

    plugin = plugin_service.plugins[label]
    ollama_url = f"http://{plugin.ip}:{plugin.port}/api/delete"
    payload = {"model": request.model_name}

    logger.info(f"Sending DELETE request to Ollama")
    logger.info(f"  URL: {ollama_url}")
    logger.info(f"  Payload: {payload}")
    logger.info(f"  Model to delete: {request.model_name}")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method="DELETE",
                url=ollama_url,
                json=payload
            )

            # Log detailed response information
            logger.info(f"Ollama response status code: {response.status_code}")
            logger.info(f"Ollama response body: {response.text}")
            logger.info(f"Ollama response headers: {dict(response.headers)}")

            if response.status_code == 200:
                logger.info(f"Successfully deleted model {request.model_name} from {label}")
                return Response(
                    content=json.dumps({"status": "success"}),
                    media_type="application/json"
                )
            else:
                error_msg = response.text
                logger.error(f"Ollama returned error - Status: {response.status_code}, Body: {error_msg}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Ollama error deleting model '{request.model_name}': {error_msg}"
                )
    except httpx.HTTPError as e:
        logger.error(f"HTTP error during model deletion: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during model deletion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/litellm/status")
async def get_litellm_status():
    """
    Get LiteLLM configuration and connection status.
    
    Returns:
        JSON response with LiteLLM status
    """
    logger.info("GET /llmm/litellm/status called")
    
    client = get_litellm_client()
    
    if client is None:
        return Response(
            content=json.dumps({
                "configured": False,
                "available": False,
                "url": None
            }),
            media_type="application/json"
        )
    
    # Check if LiteLLM API is available
    is_available = await client.check_health()
    
    return Response(
        content=json.dumps({
            "configured": True,
            "available": is_available,
            "url": client.base_url
        }),
        media_type="application/json"
    )


@router.post("/litellm/models/bulk-create")
async def bulk_create_litellm_models(request: BulkCreateRequest):
    """
    Create models in LiteLLM for multiple Ollama hosts.
    
    Args:
        request: Bulk create request with model_name and host_labels
    
    Returns:
        JSON response with creation results
    """
    logger.info(f"POST /llmm/litellm/models/bulk-create called for model: {request.model_name}")
    logger.info(f"Host labels: {request.host_labels}")
    
    # Check if LiteLLM is configured
    client = get_litellm_client()
    if client is None:
        raise HTTPException(
            status_code=503,
            detail="LiteLLM is not configured. Set LITELLM_URL and LITELLM_MASTER_KEY environment variables."
        )
    
    # Get discovery manager and plugin service
    discovery_manager = get_discovery_manager()
    plugin_service = discovery_manager.get_plugin_service()
    
    results = []
    
    for label in request.host_labels:
        # Find the plugin for this label
        if label not in plugin_service.plugins:
            logger.warning(f"Plugin not found for label: {label}")
            results.append({
                "host": label,
                "success": False,
                "error": f"Host '{label}' not found"
            })
            continue
        
        plugin = plugin_service.plugins[label]
        
        # Generate unique model_id for this host
        model_id = f"{label}-{request.model_name}"
        # Use the provided model name
        model_name = request.model_name
        ollama_api_base = f"http://{plugin.ip}:{plugin.port}"
        
        try:
            # Create model in LiteLLM
            response = await client.create_model(
                model_id=model_id,
                model_name=model_name,
                ollama_model=request.ollama_model,
                api_base=ollama_api_base
            )
            
            results.append({
                "host": label,
                "model_id": model_id,
                "model_name": model_name,
                "success": True,
                "response": response
            })
            
            logger.info(f"Successfully created LiteLLM model for {label}")
            
        except Exception as e:
            logger.error(f"Failed to create LiteLLM model for {label}: {e}")
            results.append({
                "host": label,
                "model_id": model_id,
                "model_name": model_name,
                "success": False,
                "error": str(e)
            })
    
    # Count successes and failures
    successes = sum(1 for r in results if r.get("success"))
    failures = len(results) - successes
    
    logger.info(f"Bulk create completed: {successes} succeeded, {failures} failed")
    
    return Response(
        content=json.dumps({
            "total": len(results),
            "successes": successes,
            "failures": failures,
            "results": results
        }),
        media_type="application/json"
    )


@router.get("/litellm/models/{label}")
async def get_litellm_models_for_host(label: str):
    """
    Get all LiteLLM models for a specific host.
    
    Args:
        label: The host label
    
    Returns:
        JSON response with list of models for this host
    """
    logger.info(f"GET /llmm/litellm/models/{label} called")
    
    # Check if LiteLLM is configured
    client = get_litellm_client()
    if client is None:
        raise HTTPException(
            status_code=503,
            detail="LiteLLM is not configured. Set LITELLM_URL and LITELLM_MASTER_KEY environment variables."
        )
    
    try:
        models = await client.get_models_for_host(label)
        logger.info(f"Found {len(models)} LiteLLM model(s) for host {label}")
        
        return Response(
            content=json.dumps({"models": models}),
            media_type="application/json"
        )
    except Exception as e:
        logger.error(f"Failed to get LiteLLM models for {label}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve models: {str(e)}"
        )


@router.delete("/litellm/models/{model_id}")
async def delete_litellm_model(model_id: str):
    """
    Delete a model from LiteLLM.
    
    Args:
        model_id: The unique model ID to delete
    
    Returns:
        JSON response with deletion result
    """
    logger.info(f"DELETE /llmm/litellm/models/{model_id} called")
    
    # Check if LiteLLM is configured
    client = get_litellm_client()
    if client is None:
        raise HTTPException(
            status_code=503,
            detail="LiteLLM is not configured. Set LITELLM_URL and LITELLM_MASTER_KEY environment variables."
        )
    
    try:
        response = await client.delete_model(model_id)
        logger.info(f"Successfully deleted LiteLLM model {model_id}")
        
        return Response(
            content=json.dumps({
                "status": "success",
                "model_id": model_id,
                "response": response
            }),
            media_type="application/json"
        )
    except httpx.HTTPError as e:
        logger.error(f"Failed to delete LiteLLM model {model_id}: {e}")
        error_detail = str(e)
        if hasattr(e, 'response') and e.response:
            error_detail = e.response.text
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete model: {error_detail}"
        )
    except Exception as e:
        logger.error(f"Unexpected error deleting LiteLLM model {model_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )


@router.post("/litellm/models/bulk-purge")
async def bulk_purge_litellm_models(request: BulkPurgeRequest):
    """
    Purge all LiteLLM models for multiple hosts.
    
    Args:
        request: Bulk purge request with host_labels
    
    Returns:
        JSON response with purge results
    """
    logger.info(f"POST /llmm/litellm/models/bulk-purge called")
    logger.info(f"Host labels: {request.host_labels}")
    
    # Check if LiteLLM is configured
    client = get_litellm_client()
    if client is None:
        raise HTTPException(
            status_code=503,
            detail="LiteLLM is not configured. Set LITELLM_URL and LITELLM_MASTER_KEY environment variables."
        )
    
    results = []
    total_models_deleted = 0
    
    for label in request.host_labels:
        try:
            # Get all models for this host
            models = await client.get_models_for_host(label)
            
            if not models:
                logger.info(f"No models found for host {label}")
                results.append({
                    "host": label,
                    "models_deleted": 0,
                    "success": True,
                    "deleted_models": [],
                    "message": "No models found"
                })
                continue
            
            # Delete each model
            deleted_models = []
            failed_models = []
            
            for model in models:
                model_id = model.get("model_info", {}).get("id")
                if not model_id:
                    logger.warning(f"Model missing id: {model}")
                    continue
                
                try:
                    await client.delete_model(model_id)
                    deleted_models.append(model_id)
                    logger.info(f"Deleted model {model_id} from host {label}")
                except Exception as e:
                    logger.error(f"Failed to delete model {model_id}: {e}")
                    failed_models.append({
                        "model_id": model_id,
                        "error": str(e)
                    })
            
            total_models_deleted += len(deleted_models)
            
            # Determine if this host's purge was successful
            success = len(failed_models) == 0
            
            results.append({
                "host": label,
                "models_deleted": len(deleted_models),
                "success": success,
                "deleted_models": deleted_models,
                "failed_models": failed_models if failed_models else None
            })
            
            logger.info(f"Purged {len(deleted_models)} model(s) for host {label}")
            
        except Exception as e:
            logger.error(f"Failed to purge models for host {label}: {e}")
            results.append({
                "host": label,
                "models_deleted": 0,
                "success": False,
                "error": str(e)
            })
    
    # Count successes and failures
    successes = sum(1 for r in results if r.get("success"))
    failures = len(results) - successes
    
    logger.info(f"Bulk purge completed: {successes} hosts succeeded, {failures} hosts failed, {total_models_deleted} total models deleted")
    
    return Response(
        content=json.dumps({
            "total_hosts": len(results),
            "total_models_deleted": total_models_deleted,
            "successes": successes,
            "failures": failures,
            "results": results
        }),
        media_type="application/json"
    )
