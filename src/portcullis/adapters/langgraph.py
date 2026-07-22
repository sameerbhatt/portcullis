"""LangGraph / LangChain adapter.

This is the only module in the library that knows about LangChain. It wraps
a LangChain tool (anything callable, or a BaseTool) so that every invocation
is routed through the GovernanceEngine first.

The import of langchain is deferred and optional: the core library works
without it, and importing this module only fails if you actually try to wrap
a tool without langchain installed.
"""

from __future__ import annotations

from typing import Any, Callable

from ..core.engine import GovernanceEngine


def govern_tool(engine: GovernanceEngine, tool: Any, name: str | None = None) -> Any:
    """Return a governed version of a LangChain tool.

    Accepts either a LangChain BaseTool or a plain callable. The returned
    object is the same shape as the input (a BaseTool stays a BaseTool, a
    function stays a function) so it drops into an existing graph unchanged.
    """
    tool_name = name or _infer_name(tool)

    if _is_base_tool(tool):
        return _wrap_base_tool(engine, tool, tool_name)
    if callable(tool):
        return _wrap_callable(engine, tool, tool_name)
    raise TypeError(f"cannot govern object of type {type(tool)!r}")


def govern_all(engine: GovernanceEngine, tools: list[Any]) -> list[Any]:
    """Convenience: govern a whole list of tools at once."""
    return [govern_tool(engine, t) for t in tools]


def _wrap_callable(engine: GovernanceEngine, fn: Callable[..., Any], name: str) -> Callable[..., Any]:
    def governed(*args: Any, **kwargs: Any) -> Any:
        return engine.guard(name, fn, *args, **kwargs)

    governed.__name__ = getattr(fn, "__name__", name)
    governed.__doc__ = getattr(fn, "__doc__", None)
    governed.__governed__ = True  # type: ignore[attr-defined]
    return governed


def _wrap_base_tool(engine: GovernanceEngine, tool: Any, name: str) -> Any:
    """Wrap a LangChain BaseTool by intercepting its run methods.

    We subclass on the fly so LangGraph still sees a BaseTool with the same
    name, description, and args schema -- only the execution is governed.
    """
    from langchain_core.tools import BaseTool  # deferred import

    original_run = tool._run
    original_arun = getattr(tool, "_arun", None)

    class _Governed(type(tool)):  # type: ignore[misc]
        def _run(self, *args: Any, **kwargs: Any) -> Any:
            return engine.guard(name, original_run, *args, **kwargs)

    # copy the instance state onto a new governed instance
    governed = _Governed(**_tool_init_kwargs(tool))
    if original_arun is not None:
        async def _arun(*args: Any, **kwargs: Any) -> Any:
            # governance decision is sync; the wrapped call may be async
            return engine.guard(name, lambda *a, **k: original_arun(*a, **k), *args, **kwargs)
        governed._arun = _arun  # type: ignore[assignment]
    assert isinstance(governed, BaseTool)
    return governed


def _tool_init_kwargs(tool: Any) -> dict:
    keys = ("name", "description")
    kwargs = {k: getattr(tool, k) for k in keys if hasattr(tool, k)}
    if hasattr(tool, "args_schema") and tool.args_schema is not None:
        kwargs["args_schema"] = tool.args_schema
    if hasattr(tool, "func") and getattr(tool, "func") is not None:
        kwargs["func"] = tool.func
    return kwargs


def _is_base_tool(obj: Any) -> bool:
    try:
        from langchain_core.tools import BaseTool
    except ImportError:
        return False
    return isinstance(obj, BaseTool)


def _infer_name(tool: Any) -> str:
    for attr in ("name", "__name__"):
        val = getattr(tool, attr, None)
        if isinstance(val, str) and val:
            return val
    return tool.__class__.__name__
