"""Img2City -- an agentic image -> editable 3D city pipeline.

2D inputs (OSM footprints, satellite + Street View imagery) go in; a
parametric, editable Blender city model comes out, built by an LLM agent
running a render -> critique -> refine loop over a Blender-side parts kit.

Package map (see docs/architecture.md):
    config    paths, endpoints, LLM provider + models (from .env / environment)
    agent     llm front door + provider transports / planner / token logging / demo harness
    judge     deterministic + perceptual scoring anchors
    imagery   2D input acquisition and cleaning
    building  single building: image -> spec -> Blender model (+ appearance)
    city      block level: OSM -> LoD1 -> agent specs -> assembly -> verify
    scene     non-building layers: roads, trees, vehicles, traffic, shops
    kit       Blender-side parametric parts library (source-injected)
    library   agent-driven growth of the parts kit
    prior     learned image -> parameters prior
    webapp    local demo site
"""
__version__ = "0.1.0"
