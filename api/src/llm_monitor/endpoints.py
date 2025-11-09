from loguru import logger
from fastapi import APIRouter, Response, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
import httpx
from typing import List, Dict, Any
from llm_monitor import get_discovery_manager

router = APIRouter()


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
    Get status of all discovered Ollama endpoints.
    
    Returns:
        JSON response with endpoints and their status
    """
    logger.info("GET /llmm endpoint called")
    
    # Get discovery manager and its plugin service
    discovery_manager = get_discovery_manager()
    plugin_service = discovery_manager.get_plugin_service()
    
    # Fetch endpoints from all plugins
    endpoints = plugin_service.llm_endpoints()
    
    # Convert to JSON-serializable format
    json_endpoints = {}
    for label, endpoint in endpoints.items():
        json_endpoints[label] = endpoint.model_dump()
    
    logger.info(f"Returning {len(json_endpoints)} endpoint(s)")
    
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
            response = await client.delete(ollama_url, json=payload)
            
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
