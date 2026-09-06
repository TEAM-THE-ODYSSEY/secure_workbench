import requests
import json


class PIDLLMAgent:

    def __init__(
        self,
        model="qwen2.5:7b",
        url="http://localhost:11434/api/generate"
    ):
        self.model = model
        self.url = url

    def build_prompt(self, question, analysis):

        objects = []

        for obj in analysis.objects:
            objects.append({
                "id": obj.object_id,
                "type": obj.object_type,
                "tag": obj.tag,
                "confidence": obj.association_confidence
            })

        lines = []

        for line in analysis.lines:
            lines.append({
                "id": line.line_id,
                "type": line.line_type,
                "confidence": line.confidence
            })

        relationships = []

        for rel in analysis.relationships:
            relationships.append({
                "source": rel.source,
                "target": rel.target,
                "relationship": rel.relationship,
                "line": rel.pipe,
                "confidence": rel.confidence
            })

        context = {
            "objects": objects,
            "lines": lines,
            "relationships": relationships,
            "graph": analysis.graph,
            "warnings": analysis.warnings
        }

        prompt = f"""
You are an engineering P&ID explanation assistant.

The P&ID image has already been processed by a P&ID
analysis engine.

You MUST answer using only the structured information
provided below.

P&ID INFORMATION:
{json.dumps(context, indent=2)}

USER QUESTION:
{question}

Explain the P&ID clearly.

If the extracted information is uncertain, explicitly
say that it is uncertain.

Do not invent equipment, tags, connections, or values
that are not present in the supplied information.

Give a simple engineering explanation.
"""

        return prompt

    def ask(self, question, analysis):

        prompt = self.build_prompt(question, analysis)

        response = requests.post(
            self.url,
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False
            },
            timeout=120
        )

        response.raise_for_status()

        return response.json()["response"]