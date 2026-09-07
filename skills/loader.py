"""
Loader initializing built-in domain skills into SkillRegistry.
"""

import logging
from skills.registry import DomainSkill
from agent.models.schemas import TaskContext

logger = logging.getLogger("skills.loader")


def _dummy_workflow(name: str):
    def handler(context: TaskContext):
        return {"status": "executed", "skill": name, "query": context.query}
    return handler


def load_builtin_skills():
    """Register core domain skills."""
    skills = [
        DomainSkill(
            name="shutdown_sop",
            description="Shutdown SOP Analysis and unit isolation procedures",
            required_inputs=["query"],
            allowed_agents=["knowledge", "pid"],
            allowed_tools=["knowledge_search", "pid_query"],
            workflow_handler=_dummy_workflow("shutdown_sop"),
        ),
        DomainSkill(
            name="equipment_failure",
            description="Root cause equipment failure analysis across SOP, Maintenance, and Incident logs",
            required_inputs=["query", "equipment_tag"],
            allowed_agents=["knowledge", "document", "pid"],
            allowed_tools=["knowledge_search", "pid_query"],
            workflow_handler=_dummy_workflow("equipment_failure"),
        ),
        DomainSkill(
            name="pid_topology",
            description="P&ID diagram topology, upstream/downstream flow, and isolation path lookup",
            required_inputs=["tag"],
            allowed_agents=["pid"],
            allowed_tools=["pid_query"],
            workflow_handler=_dummy_workflow("pid_topology"),
        ),
        DomainSkill(
            name="pump_efficiency",
            description="Pump thermal and mechanical efficiency calculation via Python coding sandbox",
            required_inputs=["flow_rate", "head"],
            allowed_agents=["coding"],
            allowed_tools=["sandbox_execute"],
            workflow_handler=_dummy_workflow("pump_efficiency"),
        ),
        DomainSkill(
            name="document_summary",
            description="Summarize uploaded PDF/DOCX document with key findings",
            required_inputs=["document_id"],
            allowed_agents=["document"],
            allowed_tools=["document_parser"],
            workflow_handler=_dummy_workflow("document_summary"),
        ),
        DomainSkill(
            name="document_comparison",
            description="Cross-compare uploaded document against MRPL Knowledge Base SOPs",
            required_inputs=["document_id"],
            allowed_agents=["document", "knowledge"],
            allowed_tools=["document_parser", "knowledge_search"],
            workflow_handler=_dummy_workflow("document_comparison"),
        ),
        DomainSkill(
            name="action_items",
            description="Extract operational action items and next steps from documents/analysis",
            required_inputs=["query"],
            allowed_agents=["general", "knowledge"],
            allowed_tools=[],
            workflow_handler=_dummy_workflow("action_items"),
        ),
        DomainSkill(
            name="technical_report",
            description="Generate verified executive ReportLab PDF report artifact",
            required_inputs=["evidence"],
            allowed_agents=["report"],
            allowed_tools=["generate_report_pdf"],
            workflow_handler=_dummy_workflow("technical_report"),
            output_format="PDF",
        ),
    ]

    from skills.registry import skill_registry
    for s in skills:
        skill_registry.register(s)
    logger.info(f"Loaded {len(skills)} built-in domain skills into SkillRegistry.")


# Load on module import
load_builtin_skills()
