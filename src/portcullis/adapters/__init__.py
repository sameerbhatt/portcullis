"""Framework adapters for portcullis.

Each adapter wraps a specific agent framework's tools so their calls route
through the governance engine. The LangGraph adapter is the reference
implementation; the core has no dependency on any of them.
"""
