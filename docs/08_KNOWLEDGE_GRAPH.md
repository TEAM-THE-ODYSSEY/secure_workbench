# P&ID Knowledge Graph

Start with NetworkX for development and debugging. Move to Neo4j only when graph scale/query requirements justify it.

Suggested node types:
- equipment
- valve
- instrument
- pipe
- tank
- exchanger
- controller

Suggested relationships:
- connected_by_pipe
- feeds
- discharges_to
- suction_from
- controlled_by
- measures
- isolates

Each edge should retain confidence and provenance.
