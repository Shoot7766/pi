import os
import psutil
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from config.settings import settings
from config.logger import logger
from core.security import security_guard

app = FastAPI(
    title="Central AI Boss API Gateway",
    description="Local secure API endpoints for physical microcontrollers, dashboard streams, and CRM automation.",
    version="1.0.0"
)

# Pydantic models for incoming integration payloads
class ESP32Payload(BaseModel):
    device_id: str
    sensor_type: str
    value: float
    status: str

class CRMPayload(BaseModel):
    event_type: str
    lead_id: str
    client_name: str
    message: str

@app.get("/")
def read_root():
    return {
        "status": "online",
        "system": "Central AI Boss Core OS",
        "endpoints": ["/health", "/status", "/webhook/esp32", "/webhook/crm"]
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "FastAPI Gateway"}

@app.get("/status")
def system_status():
    """Returns local host resource utilization telemetry."""
    try:
        cpu_usage = psutil.cpu_percent(interval=None)
        ram_usage = psutil.virtual_memory().percent
        disk_usage = psutil.disk_usage("/").percent
    except Exception:
        cpu_usage = "N/A"
        ram_usage = "N/A"
        disk_usage = "N/A"

    pending_hitl = security_guard.get_pending_requests()

    return {
        "os": os.name,
        "telemetry": {
            "cpu_percent": cpu_usage,
            "ram_percent": ram_usage,
            "disk_percent": disk_usage
        },
        "security": {
            "pending_hitl_count": len(pending_hitl),
            "pending_hitl_list": pending_hitl
        }
    }

@app.post("/webhook/esp32")
async def esp32_webhook(payload: ESP32Payload, background_tasks: BackgroundTasks):
    """
    Receives physical telemetry from ESP32 iot devices.
    Fires automatic agent rules or alerts if sensors cross critical thresholds.
    """
    logger.info(f"ESP32 Webhook triggered: Device={payload.device_id}, {payload.sensor_type}={payload.value}")
    
    # Example autonomous action trigger
    if payload.value > 80.0 and payload.sensor_type == "temperature":
        logger.warning(f"CRITICAL: High temperature detected on {payload.device_id}: {payload.value}°C")
        # In a fully realized system, background tasks can push alerts directly to the Telegram bot layer.
        
    return {"status": "received", "action": "logged"}

@app.post("/webhook/crm")
async def crm_webhook(payload: CRMPayload):
    """
    Exposes lead/deal tracking integration.
    Agents can analyze client data and format response pitches automatically.
    """
    logger.info(f"CRM Webhook triggered: Event={payload.event_type}, Client={payload.client_name}")
    return {"status": "processed", "lead": payload.lead_id}
