from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import json
import logging
import os
import re
from typing import Any, Callable, Dict, Optional, TypedDict

from dotenv import load_dotenv
from langgraph.graph import END, StateGraph

from server import alerts, db
from server.rules import Anomaly

load_dotenv()
logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="agent-triage")


class AgentState(TypedDict, total=False):
    """Shared state dictionary passed across LangGraph triage workflow nodes."""

    device_id: str
    anomaly: Anomaly
    mode: str
    arming: str
    policy: str
    recent_events: str
    local_time: str
    real: bool
    severity: str
    reason: str
    action: str


def _extract_json(text: str) -> dict:
    """Extract and parse the first JSON object from an LLM completion string."""
    s = (text or "").strip()
    m = re.search(r"\{.*\}", s, re.DOTALL)
    if m:
        s = m.group(0)
    return json.loads(s)


def _default_llm_invoke(prompt: str, cfg: dict) -> str:
    """Invoke the configured Ollama or NVIDIA OpenAI-compatible chat model with temperature=0."""
    provider = str(cfg.get("provider", "nvidia")).lower()
    timeout_s = float(cfg.get("timeout_s", 20.0))
    if provider == "ollama":
        from langchain_ollama import ChatOllama

        model_name = cfg.get("model") or "beam:cloud"
        llm = ChatOllama(
            model=model_name,
            temperature=0,
            format="json",
            base_url=cfg.get("base_url", "http://127.0.0.1:11434"),
        )
        return str(llm.invoke(prompt).content)

    from langchain_openai import ChatOpenAI

    api_key = os.getenv("NVIDIA_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Missing NVIDIA_API_KEY")
    base_url = os.getenv("NVIDIA_BASE_URL") or cfg.get("base_url", "https://integrate.api.nvidia.com/v1")
    model_name = os.getenv("NVIDIA_MODEL") or cfg.get("model", "nvidia/nemotron-3-ultra-550b-a55b")
    llm = ChatOpenAI(
        model=model_name,
        base_url=base_url,
        api_key=api_key,
        temperature=0,
        timeout=timeout_s,
        max_retries=0,
    )
    return str(llm.invoke(prompt).content)


def build_agent_graph(
    cfg: Optional[dict] = None,
    llm_fn: Optional[Callable[[str, dict], str]] = None,
):
    """Compile the metadata-only LangGraph triage flow: context -> decide -> notify/suppress."""
    agent_cfg = cfg or {}
    invoke_fn = llm_fn or _default_llm_invoke

    def context_node(state: AgentState) -> Dict[str, Any]:
        """Gather up to 5 recent device detections and formatted event time for LLM context."""
        anom = state["anomaly"]
        dev_id = state.get("device_id", "edge-01")
        try:
            evs = db.recent_events(limit=5, device_id=dev_id)
            ev_summary = ", ".join(f"{e['object_class']}x{e['count']}({e['avg_conf']:.2f})" for e in evs) or "none"
        except Exception:
            ev_summary = "none"
        # Fall back to a valid epoch reference when unit tests supply small relative timestamps
        t_str = datetime.fromtimestamp(anom.ts if anom.ts > 1e8 else 1700000000.0).strftime("%H:%M:%S")
        return {
            "policy": getattr(anom, "policy", "review"),
            "recent_events": ev_summary,
            "local_time": t_str,
        }

    def decide_node(state: AgentState) -> Dict[str, Any]:
        """Evaluate rule policy and query the LLM on metadata, failing open on any error."""
        anom = state["anomaly"]
        policy = state.get("policy", "review")

        if policy == "log_only":
            return {
                "real": False,
                "severity": anom.severity,
                "reason": "log_only policy",
            }

        if not agent_cfg.get("enabled", True):
            return {
                "real": True,
                "severity": anom.severity,
                "reason": "agent disabled (pass-through)",
            }

        prompt = (
            "You are a security triage agent coordinating home and public CCTV alerts. "
            "You NEVER see images; evaluate structured metadata only. "
            "Reply ONLY valid JSON with keys: "
            '{"real": bool, "severity": "info"|"warning"|"critical", "reason": "short one-line explanation"}.\n'
            f"Mode: {state.get('mode', anom.mode)} | Arming: {state.get('arming', 'armed_night')} | Time: {state.get('local_time')}\n"
            f"Rule: {anom.rule} | Policy: {policy} | Zone: {getattr(anom, 'zone', '') or 'global'}\n"
            f"Detail: {anom.detail} | Initial severity: {anom.severity}\n"
            f"Recent events on device {state.get('device_id')}: {state.get('recent_events')}"
        )

        try:
            raw = invoke_fn(prompt, agent_cfg)
            parsed = _extract_json(raw)
            is_real = bool(parsed.get("real", True))
            # Critical rules marked always_alert may upgrade severity/reason but cannot be suppressed
            if policy == "always_alert":
                is_real = True
            sev = str(parsed.get("severity", anom.severity)).lower()
            if sev not in ("info", "warning", "critical"):
                sev = anom.severity
            reason = str(parsed.get("reason", "verified by agent")).strip()
            return {"real": is_real, "severity": sev, "reason": reason}
        except Exception as exc:
            logger.warning("Agent LLM fail-open on %s: %s", anom.rule, exc)
            return {
                "real": True,
                "severity": anom.severity,
                "reason": f"fail-open ({type(exc).__name__})",
            }

    def route_edge(state: AgentState) -> str:
        """Route confirmed alerts to notify_node and suppressed alerts to suppress_node."""
        return "notify" if state.get("real", True) else "suppress"

    def notify_node(state: AgentState) -> Dict[str, Any]:
        """Persist a confirmed anomaly with agent reasoning and trigger local/webhook alerts."""
        anom = state["anomaly"]
        anom.severity = state.get("severity", anom.severity)
        reason = state.get("reason", "")
        db.insert_anomaly(
            ts=anom.ts,
            device_id=state.get("device_id", "edge-01"),
            rule=anom.rule,
            detail=f"{anom.detail} [agent: {reason}]" if reason else anom.detail,
            severity=anom.severity,
        )
        alerts.fire(anom, device_id=state.get("device_id", ""), reason=reason)
        return {"action": "notified"}

    def suppress_node(state: AgentState) -> Dict[str, Any]:
        """Log a suppressed anomaly as info in SQLite without sounding alerts."""
        anom = state["anomaly"]
        reason = state.get("reason", "suppressed")
        db.insert_anomaly(
            ts=anom.ts,
            device_id=state.get("device_id", "edge-01"),
            rule=anom.rule,
            detail=f"[SUPPRESSED] {anom.detail} ({reason})",
            severity="info",
        )
        return {"action": "suppressed"}

    graph = StateGraph(AgentState)
    graph.add_node("context", context_node)
    graph.add_node("decide", decide_node)
    graph.add_node("notify", notify_node)
    graph.add_node("suppress", suppress_node)
    graph.set_entry_point("context")
    graph.add_edge("context", "decide")
    graph.add_conditional_edges("decide", route_edge, {"notify": "notify", "suppress": "suppress"})
    graph.add_edge("notify", END)
    graph.add_edge("suppress", END)
    return graph.compile()


def review_anomaly(
    anomaly: Anomaly,
    device_id: str,
    mode: str = "public",
    arming: str = "armed_night",
    agent_cfg: Optional[dict] = None,
    llm_fn: Optional[Callable[[str, dict], str]] = None,
) -> Dict[str, Any]:
    """Build and synchronously execute the LangGraph triage workflow for one anomaly."""
    cfg = agent_cfg or {}
    compiled = build_agent_graph(cfg=cfg, llm_fn=llm_fn)
    initial: AgentState = {
        "device_id": device_id,
        "anomaly": anomaly,
        "mode": mode,
        "arming": arming,
    }
    return compiled.invoke(initial)


def submit_review(
    anomaly: Anomaly,
    device_id: str,
    mode: str = "public",
    arming: str = "armed_night",
    agent_cfg: Optional[dict] = None,
) -> None:
    """Dispatch anomaly triage onto the background worker pool or execute inline."""
    cfg = agent_cfg or {}
    if cfg.get("async_dispatch", True):
        _executor.submit(review_anomaly, anomaly, device_id, mode, arming, cfg, None)
    else:
        review_anomaly(anomaly, device_id, mode, arming, cfg, None)
