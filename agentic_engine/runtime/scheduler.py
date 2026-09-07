from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional, Set

from ..orchestration.execution_plan import DAGNodeDefinition

logger = logging.getLogger("agentic_engine.scheduler")


class DAGExecutionError(RuntimeError):
    pass


class DAGScheduler:
    """Executes multi-step workflows according to their dependency graph,
    running independent nodes concurrently where safe.
    """

    def __init__(self, max_concurrency: int = 4):
        self.max_concurrency = max_concurrency

    def execute_dag(
        self,
        nodes: List[DAGNodeDefinition],
        node_executor_fn: Callable[[DAGNodeDefinition, Dict[str, Any]], Any],
    ) -> Dict[str, Any]:
        """Executes a list of DAG nodes respecting dependencies and executing
        parallel branches concurrently.
        """
        node_map = {n.node_id: n for n in nodes}
        completed_nodes: Set[str] = set()
        node_results: Dict[str, Any] = {}
        pending_nodes = set(node_map.keys())

        with ThreadPoolExecutor(max_workers=self.max_concurrency) as executor:
            while pending_nodes:
                # 1. Find all nodes whose dependencies are completely satisfied
                ready_nodes = [
                    node_id for node_id in pending_nodes
                    if all(dep in completed_nodes for dep in node_map[node_id].dependencies)
                ]

                if not ready_nodes:
                    raise DAGExecutionError(
                        f"Cyclic or unresolvable dependencies in DAG. Pending: {pending_nodes}"
                    )

                # 2. Dispatch all ready nodes in parallel
                future_to_node = {
                    executor.submit(node_executor_fn, node_map[nid], node_results): nid
                    for nid in ready_nodes
                }

                # 3. Collect completed nodes
                for future in as_completed(future_to_node):
                    nid = future_to_node[future]
                    node = node_map[nid]
                    try:
                        result = future.result()
                        node.status = "COMPLETED"
                        node.result = result
                        node_results[nid] = result
                        completed_nodes.add(nid)
                        pending_nodes.remove(nid)
                        logger.info(f"DAG Node '{nid}' completed successfully.")
                    except Exception as exc:
                        node.status = "FAILED"
                        node.error = str(exc)
                        logger.error(f"DAG Node '{nid}' failed: {exc}", exc_info=True)
                        raise DAGExecutionError(f"DAG execution halted: Node '{nid}' failed: {exc}") from exc

        return node_results
