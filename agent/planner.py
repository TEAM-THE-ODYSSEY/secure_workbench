"""
Context Planner and Intent Analyzer for Main AI Agent (LLM Generation #1).
Dynamically plans evidence requirements, target entities, and capability tool calls.
"""

import logging
from typing import Any, Dict, List, Optional
from agent.models.model_manager import ModelManager
from agent.models.schemas import ContextPlan, TaskRequest

logger = logging.getLogger("agent.planner")

PLANNING_SYSTEM_PROMPT = """You are the Context Planner for the MRPL Sovereign Agentic AI Workbench.
Your objective is to understand the user's request, identify intent, extract engineering entities/tags, and plan required evidence context and tool calls.

Available Capability Tools:
1. "knowledge_search": Search Knowledge Base for SOPs, equipment specs, maintenance logs, incident reports.
2. "pid_query": Query P&ID topology diagrams for tags, downstream/upstream connections, isolation valves, flow paths.
3. "document_info": Query document metadata, version history, or section structure.
4. "data_analysis": Query tabular equipment operating parameters or maintenance metrics.
5. "generate_report_pdf": Generate executive ReportLab SOP PDF artifact.

Input: User request objective and optional entity tags.

Output JSON format strictly matching:
{
  "intent": "<FAILURE_ANALYSIS | TOPOLOGY_QUERY | SOP_SYNTHESIS | DATA_QUERY | GENERAL_REASONING>",
  "entities": ["<extracted equipment tag e.g. P-101A, XV-101>"],
  "required_context": ["<evidence domain e.g. equipment_spec, maintenance_history, sop, pid_topology>"],
  "tool_calls": [
    {"tool": "knowledge_search", "query": "<search query>"},
    {"tool": "pid_query", "tag": "<equipment tag>", "query_type": "<DOWNSTREAM | ISOLATION_VALVES | FLOW_PATH>"}
  ],
  "output_type": "<TEXT | PDF>"
}
Do NOT generate arbitrary code or execution commands.
"""


class ContextPlanner:
    """
    Context Planner executing LLM Generation #1 to dynamically analyze user intent,
    extract canonical entity tags, and build targeted context acquisition plans.
    """

    def __init__(self, model_manager: Optional[ModelManager] = None):
        self.model_manager = model_manager or ModelManager()

    def plan_context(
        self,
        request: TaskRequest,
        task_id: Optional[str] = None,
    ) -> ContextPlan:
        """
        Execute LLM Generation #1: Produce structured ContextPlan.
        Falls back to rule-based planning if LLM API is unavailable.
        """
        prompt = f"User Request: '{request.objective}'\nEntities: {request.entities}\nDocument Type: {request.document_type}"
        messages = [
            {"role": "system", "content": PLANNING_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        try:
            plan_obj, meta = self.model_manager.generate_structured(
                messages=messages,
                response_schema=ContextPlan,
                temperature=0.0,
                max_tokens=1024,
                task_id=task_id,
            )
            logger.info(f"[{task_id or 'global'}] LLM #1 Context Planner generated intent: '{plan_obj.intent}' with {len(plan_obj.tool_calls)} tool calls.")
            return plan_obj
        except Exception as e:
            logger.warning(f"[{task_id or 'global'}] LLM #1 Context Planner failed ({e}). Falling back to rule-based context planner.")
            return self._heuristic_fallback_plan(request)

    def _heuristic_fallback_plan(self, request: TaskRequest) -> ContextPlan:
        """Rule-based heuristic context planner fallback."""
        obj_lower = request.objective.lower()
        entities = list(request.entities)

        # Rule 1: Explicit PDF report generation request
        is_pdf = any(kw in obj_lower for kw in ["generate pdf", "download pdf", "export pdf", "create pdf report", "make a pdf"])
        output_type = "PDF" if is_pdf else "TEXT"

        # Rule 2: Equipment tag extraction
        import re
        extracted_tags = re.findall(r'\b[A-Z]{1,3}[-_\s]?\d{3}[A-Z]?\b', request.objective)
        for tag in extracted_tags:
            tag_clean = tag.upper().replace(" ", "")
            if tag_clean not in entities:
                entities.append(tag_clean)

        # Rule 0: Conversational greeting check
        import re
        is_doc = any(kw in obj_lower for kw in ["explain", "doc", "pdf", "file", "report"])
        greeting_pattern = r'\b(hi|hai|hello|hey|greetings|good morning|good afternoon|good evening|how are you|how are u|how do you do|who are you|what can you do)\b'
        is_greeting = not is_doc and (bool(re.search(greeting_pattern, obj_lower)) or (len(obj_lower) <= 4 and not any(c.isdigit() for c in obj_lower)))
        if is_greeting:
            return ContextPlan(
                intent="GREETING",
                entities=[],
                required_context=[],
                tool_calls=[],
                output_type="TEXT"
            )

        # Rule 3: Intent determination and tool planning
        tool_calls = []
        intent = "GENERAL_REASONING"

        if "downstream" in obj_lower or "valve" in obj_lower or "topology" in obj_lower or "pid" in obj_lower or "isolate" in obj_lower:
            intent = "TOPOLOGY_QUERY"
            tag = entities[0] if entities else "P-101A"
            query_type = "ISOLATION_VALVES" if "valve" in obj_lower or "isolate" in obj_lower else "DOWNSTREAM"
            tool_calls.append({"tool": "pid_query", "tag": tag, "query_type": query_type})
            tool_calls.append({"tool": "knowledge_search", "query": f"{tag} operating SOP specification"})
        elif "fail" in obj_lower or "abnormal" in obj_lower or "maintenance" in obj_lower or "vibration" in obj_lower:
            intent = "FAILURE_ANALYSIS"
            tag = entities[0] if entities else "P-101A"
            tool_calls.append({"tool": "pid_query", "tag": tag, "query_type": "ISOLATION_VALVES"})
            tool_calls.append({"tool": "knowledge_search", "query": f"{tag} failure maintenance operating limits SOP"})
            tool_calls.append({"tool": "data_analysis", "entity_id": tag, "metric_name": "maintenance_frequency"})
        elif is_pdf or "sop" in obj_lower:
            intent = "SOP_SYNTHESIS"
            query_term = entities[0] if entities else request.objective
            tool_calls.append({"tool": "knowledge_search", "query": f"{query_term} procedure steps operating limits"})
        else:
            tool_calls.append({"tool": "knowledge_search", "query": request.objective})

        return ContextPlan(
            intent=intent,
            entities=entities,
            required_context=["equipment_spec", "maintenance_history", "sop", "pid_topology"],
            tool_calls=tool_calls,
            output_type=output_type,
        )
