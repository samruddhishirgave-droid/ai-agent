"""Tools for the agent: a safe calculator and a web search.

Each tool catches its own errors and returns a readable message instead of raising,
so one failed tool call never crashes the whole agent run.
"""
import ast
import math
import operator
import os

from langchain.tools import tool

# ---------- calculator (safe: no eval of arbitrary code) ----------
_BINOPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod, ast.Pow: operator.pow,
}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_FUNCS = {
    "sqrt": math.sqrt, "log": math.log, "log10": math.log10, "log2": math.log2,
    "sin": math.sin, "cos": math.cos, "tan": math.tan, "abs": abs, "round": round,
    "floor": math.floor, "ceil": math.ceil,
}
_CONSTS = {"pi": math.pi, "e": math.e}


def _eval(node):
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.Name) and node.id in _CONSTS:
        return _CONSTS[node.id]
    if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
        left, right = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 1000:
            raise ValueError("Exponent too large (limit is 1000).")
        return _BINOPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return _UNARY[type(node.op)](_eval(node.operand))
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id in _FUNCS and not node.keywords):
        return _FUNCS[node.func.id](*[_eval(a) for a in node.args])
    raise ValueError("Unsupported expression. Use numbers, + - * / // % **, parentheses, "
                     "pi, e and functions like sqrt(), log(), round().")


def safe_calculate(expression: str) -> str:
    """Plain function (easy to test on its own). Returns the result or an error message."""
    try:
        expr = expression.replace(",", "").replace("^", "**").strip()
        if not expr or len(expr) > 300:
            return "Error: expression is empty or too long."
        result = _eval(ast.parse(expr, mode="eval"))
        if isinstance(result, float):
            result = round(result, 10)
        return str(result)
    except ZeroDivisionError:
        return "Error: division by zero."
    except (ValueError, SyntaxError, TypeError, OverflowError) as e:
        return f"Error: {e}"
    except Exception as e:  # never let a tool crash the agent
        return f"Error: could not calculate ({type(e).__name__})."


@tool
def calculator(expression: str) -> str:
    """Evaluate an arithmetic expression exactly and return the result.
    Use this for ANY calculation with large numbers, percentages, ratios, powers or roots,
    instead of calculating in your head. Example input: '48372 * 9184 + 2**20'.
    Supports + - * / // % ** parentheses, pi, e and sqrt(), log(), round()."""
    return safe_calculate(expression)


# ---------- web search ----------
# Search providers, tried in this order until one returns results:
#   1. Tavily   (free API key, most reliable; used only if TAVILY_API_KEY is set)
#   2. ddgs     (no key; several engines, but some networks block them)
#   3. Wikipedia (no key; works on almost every network, but not real-time news)
import json
import re
import urllib.parse
import urllib.request

BACKENDS = ["auto", "duckduckgo", "bing", "brave", "yahoo"]


def _format(results, source):
    lines = [f"(search source: {source})"]
    for i, r in enumerate(results, 1):
        lines.append(f"[{i}] {r['title']}\n{r['snippet']}\nURL: {r['url']}")
    return "\n\n".join(lines)


def _tavily(query, n):
    from tavily import TavilyClient
    data = TavilyClient(api_key=os.environ["TAVILY_API_KEY"]).search(query, max_results=n)
    return [{"title": r.get("title", ""), "snippet": (r.get("content") or "")[:400], "url": r.get("url", "")}
            for r in data.get("results", [])]


def _ddgs(query, n):
    from ddgs import DDGS
    for backend in BACKENDS:
        try:
            res = DDGS(timeout=10).text(query, max_results=n, backend=backend)
        except Exception:          # ddgs raises "No results found" instead of returning []
            continue
        if res:
            return [{"title": r.get("title", ""), "snippet": r.get("body", ""), "url": r.get("href", "")}
                    for r in res]
    return []


def _wikipedia(query, n):
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
        {"action": "query", "list": "search", "srsearch": query, "format": "json", "srlimit": n})
    req = urllib.request.Request(url, headers={"User-Agent": "ai-agent-demo/1.0 (learning project)"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    out = []
    for r in data.get("query", {}).get("search", []):
        out.append({"title": r["title"], "snippet": re.sub(r"<[^>]+>", "", r.get("snippet", "")),
                    "url": f"https://en.wikipedia.org/?curid={r['pageid']}"})
    return out


def run_search(query: str, max_results: int = 5) -> str:
    """Plain function (easy to test on its own). Never raises for 'no results'."""
    if os.getenv("SIMULATE_SEARCH_FAILURE") == "1":      # testing aid for the failure demo
        raise RuntimeError("simulated search outage")
    providers = []
    if os.getenv("TAVILY_API_KEY"):
        providers.append(("Tavily", _tavily))
    providers += [("DuckDuckGo/ddgs", _ddgs), ("Wikipedia", _wikipedia)]
    errors = []
    for name, fn in providers:
        try:
            results = fn(query, max_results)
        except Exception as e:
            errors.append(f"{name}: {type(e).__name__}")
            continue
        if results:
            return _format(results, name)
    detail = f" (tried: {', '.join(errors)})" if errors else ""
    return "No results found for this query" + detail + "."


@tool
def web_search(query: str) -> str:
    """Search the web for current or factual information (news, prices, populations,
    recent events, anything that may have changed). Input is a short search query.
    Returns the top results with title, snippet and URL. If it finds nothing or fails,
    it says so; in that case tell the user you could not verify the answer."""
    try:
        return run_search(query)
    except Exception as e:  # network error, rate limit, library error ...
        return (f"Search failed ({type(e).__name__}: {e}). "
                "Try a different query once, or tell the user the search is unavailable.")