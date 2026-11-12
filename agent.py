"""LangChain agent with two tools (calculator, web search) and visible reasoning steps."""
import os
import sys

from dotenv import load_dotenv
from langchain.agents import create_agent
from langgraph.errors import GraphRecursionError

from tools import calculator, web_search

load_dotenv()
# langchain-google-genai reads GOOGLE_API_KEY; reuse GEMINI_API_KEY if that is what is set.
if os.getenv("GEMINI_API_KEY") and not os.getenv("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

SYSTEM_PROMPT = """You are a careful research assistant with two tools:
- calculator: exact arithmetic. Always use it for calculations with big numbers, ratios,
  percentages, powers or roots. Never do such maths in your head.
- web_search: current or factual information that may have changed.

Rules:
1. Answer directly, without tools, when the question is general knowledge or conversation.
2. Before calling a tool, write one short sentence saying why you need it.
3. For multi-step questions, work step by step: search first, then calculate from what you found.
4. If a tool fails or returns nothing, say so honestly. Never invent numbers or sources.
5. Finish with a short, clear final answer that mentions where the figures came from."""

MAX_STEPS = 15   # safety limit on the reasoning loop


def build_agent(model=None):
    """model can be a 'google_genai:...' string or a chat model object (used in tests)."""
    return create_agent(
        model=model or f"google_genai:{MODEL}",
        tools=[calculator, web_search],
        system_prompt=SYSTEM_PROMPT,
    )


def text_of(content):
    """Message content can be a string or a list of blocks; return the plain text."""
    if isinstance(content, str):
        return content.strip()
    parts = []
    for block in content or []:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "".join(parts).strip()


def run(question, agent=None, verbose=True):
    """Run the agent and return (final_answer, steps). Every step is printed as it happens."""
    agent = agent or build_agent()
    steps, final = [], ""

    def log(line):
        steps.append(line)
        if verbose:
            print(line, flush=True)

    log(f"QUESTION: {question}")
    n_tools = 0
    try:
        for update in agent.stream(
            {"messages": [{"role": "user", "content": question}]},
            config={"recursion_limit": MAX_STEPS * 2},
            stream_mode="updates",
        ):
            for node, data in update.items():
                for msg in (data or {}).get("messages", []):
                    kind = type(msg).__name__
                    if kind == "AIMessage":
                        text = text_of(msg.content)
                        if getattr(msg, "tool_calls", None):
                            if text:
                                log(f"THOUGHT: {text}")
                            for call in msg.tool_calls:
                                n_tools += 1
                                log(f"TOOL CALL #{n_tools}: {call['name']}({call['args']})")
                        elif text:
                            final = text
                    elif kind == "ToolMessage":
                        out = text_of(msg.content)
                        log(f"TOOL RESULT ({msg.name}): {out[:600]}{'...' if len(out) > 600 else ''}")
    except GraphRecursionError:
        final = "I could not finish within the step limit. Please try a simpler question."
        log("ERROR: step limit reached")
    except Exception as e:   # model/API failure: report it, do not crash
        final = "Sorry, something went wrong while running the agent. Please try again."
        log(f"ERROR: {type(e).__name__}: {e}")

    if not n_tools:
        log("(no tools were used for this question)")
    log(f"FINAL ANSWER: {final}")
    return final, steps


if __name__ == "__main__":
    if len(sys.argv) > 1:
        run(" ".join(sys.argv[1:]))
    else:
        print("Ask a question (empty line to quit).")
        while True:
            q = input("\n> ").strip()
            if not q:
                break
            run(q)