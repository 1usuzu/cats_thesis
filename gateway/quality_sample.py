"""Dual-route quality sampling endpoint for ROUGE-L evaluation.

Sends the same prompt to both cloud and edge nodes simultaneously,
collects both responses for paired quality comparison.
"""

import asyncio
import time

import httpx
from fastapi import APIRouter

from config import settings
from models import QualitySampleRequest, QualitySampleResponse
from shared_client import shared_http_client

router = APIRouter(tags=["quality"])


@router.post(
    "/quality-sample",
    response_model=QualitySampleResponse,
    summary="Dual-route prompt for ROUGE-L quality comparison",
)
async def quality_sample(req: QualitySampleRequest):
    cloud_url = f"{settings.cloud_inference_url}/api/generate"
    edge_url = f"{settings.edge_inference_url}/api/generate"

    cloud_payload = {
        "model": settings.cloud_model,
        "prompt": req.prompt,
        "stream": False,
    }
    edge_payload = {
        "model": settings.edge_inference_model,
        "prompt": req.prompt,
        "stream": False,
    }

    async def call_node(url: str, payload: dict) -> tuple[str | None, int]:
        start = time.time()
        try:
            resp = await shared_http_client.client.post(url, json=payload)
            resp.raise_for_status()
            total_inference_ms = round((time.time() - start) * 1000)
            return resp.json().get("response"), total_inference_ms
        except Exception:
            return None, 0

    cloud_task = asyncio.create_task(call_node(cloud_url, cloud_payload))
    edge_task = asyncio.create_task(call_node(edge_url, edge_payload))

    cloud_resp, cloud_total_inference_ms = await cloud_task
    edge_resp, edge_total_inference_ms = await edge_task

    return QualitySampleResponse(
        prompt=req.prompt,
        cloud_response=cloud_resp,
        edge_response=edge_resp,
        cloud_model=settings.cloud_model,
        edge_model=settings.edge_inference_model,
        cloud_total_inference_ms=cloud_total_inference_ms,
        edge_total_inference_ms=edge_total_inference_ms,
    )
