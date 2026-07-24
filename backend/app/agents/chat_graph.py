from typing import TypedDict

from langgraph.graph import END, StateGraph

from app.agents.prompts import CHAT_SYSTEM_PROMPT


class ChatState(TypedDict, total=False):
    complaint_context: str
    history: list[dict]
    message: str
    messages: list[dict]


def assemble_context(state: ChatState) -> dict:
    system = CHAT_SYSTEM_PROMPT.format(context=state["complaint_context"])
    messages = [{"role": "system", "content": system}]
    messages.extend(state.get("history", []))
    messages.append({"role": "user", "content": state["message"]})
    return {"messages": messages}


def build_chat_graph():
    # Single node by design (see plan §4.2): a Q&A panel over one complaint doesn't
    # need a tool-calling loop. Still a real LangGraph, not a bare function call, so
    # both agents share one orchestration model.
    graph = StateGraph(ChatState)
    graph.add_node("assemble_context", assemble_context)
    graph.set_entry_point("assemble_context")
    graph.add_edge("assemble_context", END)
    return graph.compile()


chat_graph = build_chat_graph()


def build_chat_messages(complaint_context: str, history: list[dict], message: str) -> list[dict]:
    """Runs the context-assembly graph and returns messages ready for a streamed Groq
    call. Token-level streaming happens in the API layer: LangGraph's own streaming is
    per-node, not per-token, so real-time SSE forwards the underlying Groq stream directly."""
    result = chat_graph.invoke(
        {"complaint_context": complaint_context, "history": history, "message": message}
    )
    return result["messages"]
