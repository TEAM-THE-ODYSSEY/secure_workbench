from __future__ import annotations
class PIDGraph:
    def __init__(self):
        try:
            import networkx as nx
            self._g = nx.MultiDiGraph()
            self._nx = True
        except ImportError:
            self._g = {"nodes": {}, "edges": []}
            self._nx = False

    def add_object(self, obj):
        if self._nx:
            self._g.add_node(obj.object_id, tag=obj.tag, type=obj.object_type,
                             confidence=obj.association_confidence)
        else:
            self._g["nodes"][obj.object_id] = obj.model_dump()

    def add_relationship(self, rel):
        if self._nx:
            self._g.add_edge(rel.source, rel.target, relationship=rel.relationship,
                             pipe=rel.pipe, confidence=rel.confidence)
            self._g.add_edge(rel.target, rel.source, relationship=rel.relationship,
                             pipe=rel.pipe, confidence=rel.confidence)
        else:
            self._g["edges"].append(rel.model_dump())

    def to_dict(self):
        if self._nx:
            import networkx as nx
            return {
                "nodes": [{"id": n, **d} for n,d in self._g.nodes(data=True)],
                "edges": [{"source": u, "target": v, **d}
                          for u,v,d in self._g.edges(data=True)]
            }
        return self._g

    def neighbors(self, object_id):
        if self._nx:
            return list(self._g.neighbors(object_id))
        return [e["target"] for e in self._g["edges"] if e["source"] == object_id]
