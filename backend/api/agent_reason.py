import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from fastapi import APIRouter, HTTPException
import logging

from agent.main_agent import main_agent
from agent.models.schemas import TaskRequest, AgentTaskResult

logger = logging.getLogger("api.agent_reason")
router = APIRouter(tags=["agent"])

@router.post("/v1/agent/reason", response_model=AgentTaskResult)
def reason_agent_task(request: TaskRequest):
    try:
        result = main_agent.process_task(request)
        return result
    except Exception as e:
        logger.error(f"Error processing agent task: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
