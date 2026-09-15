"""Agentic tool loop for the `agent` track.

The model interacts with a per-sample working directory through fenced
tool calls. Each assistant message may contain one or more blocks of the
form::

    ```tool <name>
    <args>
    ```

``<args>`` is JSON (an object) or ``key: value`` lines. The ``content:``
and ``code:`` / ``prompt:`` keys consume the rest of the block, so they
can span multiple lines. Available tools:

- ``read_file``: ``path:`` relative path -> file content.
- ``write_file``: ``path:`` + ``content:`` -> writes the file.
- ``run_python``: ``code:`` (or ``path:`` to a file in the workdir),
  optional ``timeout_s:`` -> stdout/stderr of a sandboxed subprocess run
  in the workdir, same pattern as the code_exec grader.
- ``delegate``: ``prompt:`` (or the whole block body) -> one nested
  ``adapter.run`` sub-call. Depth 1: the subagent reply is returned as
  an observation and never parsed for further tool calls.

The loop ends when the model emits a line starting with ``FINAL`` or
when ``max_steps`` adapter calls are used up. Token/latency usage is
summed over all calls (including the delegate sub-call) and the full
tool trace is recorded in ``Completion.raw["trace"]``.
"""
from __future__ import annotations

import json
import re
import subprocess
import tempfile
import time
from pathlib import Path

from econ_eval.models import Completion

TOOL_FENCE = re.compile(r"```tool\s+(\S+)[^\S\n]*\n(.*?)```", re.DOTALL)
FINAL_RE = re.compile(r"^\s*FINAL\b", re.MULTILINE)
MAX_OBSERVATION = 4000
RUN_TIMEOUT_S = 20

SYSTEM = """\
You are solving a task inside a sandboxed working directory. You can act \
with fenced tool calls, one or more per message:

```tool read_file
path: <relative path>
```

```tool write_file
path: <relative path>
content:
<file content, may span lines>
```

```tool run_python
code:
<python code, standard library only>
```
(optional `timeout_s: <seconds>` line before `code:`; or `path:` to run a \
file in the workdir instead of inline code)

```tool delegate
prompt: <one-shot sub-question for a helper model>
```
The helper makes a single model call with no tools; use it at most once \
per task for a second opinion or a small derivation.

After each message I will reply with the tool observations. Inspect files, \
write code and data, run it, iterate. When you are done, reply with a line \
starting with FINAL followed by a short summary of what you did and the \
result. Do not emit tool calls after FINAL.\
"""


def _parse_args(body: str) -> dict:
    body = body.strip()
    if not body:
        return {}
    try:
        parsed = json.loads(body)
        if isinstance(parsed, dict):
            return {str(k): v for k, v in parsed.items()}
    except (json.JSONDecodeError, ValueError):
        pass
    args: dict = {}
    rest_lines: list[str] = []
    greedy_key: str | None = None
    greedy_first: str = ""
    for line in body.splitlines():
        if greedy_key is not None:
            rest_lines.append(line)
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$", line)
        if m and m.group(1) in ("content", "code", "prompt"):
            greedy_key = m.group(1)
            greedy_first = m.group(2)
        elif m:
            args[m.group(1)] = m.group(2).strip()
        elif line.strip():
            rest_lines.append(line)
    if greedy_key is not None:
        args[greedy_key] = "\n".join(([greedy_first] if greedy_first else []) + rest_lines).strip("\n")
    elif rest_lines:
        args["_body"] = "\n".join(rest_lines).strip()
    return args


def _safe_path(workdir: Path, rel: str) -> Path:
    p = (workdir / rel).resolve()
    if p != workdir.resolve() and workdir.resolve() not in p.parents:
        raise ValueError(f"path escapes workdir: {rel!r}")
    return p


def _truncate(s: str, limit: int = MAX_OBSERVATION) -> str:
    return s if len(s) <= limit else s[:limit] + f"\n... [truncated {len(s) - limit} chars]"


def _exec_tool(adapter, workdir: Path, name: str, args: dict) -> tuple[str, Completion | None]:
    """Execute one tool call. Returns (observation, sub-Completion or None).

    The sub-Completion is non-None only for ``delegate``; the caller folds
    its usage into the loop totals.
    """
    try:
        if name == "read_file":
            rel = str(args.get("path", args.get("_body", ""))).strip()
            if not rel:
                return "ERROR: read_file needs `path:`", None
            return _truncate(_safe_path(workdir, rel).read_text()), None
        if name == "write_file":
            rel = str(args.get("path", "")).strip()
            if not rel:
                return "ERROR: write_file needs `path:` and `content:`", None
            if "content" not in args:
                return "ERROR: write_file needs `content:`", None
            p = _safe_path(workdir, rel)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(str(args["content"]))
            return f"wrote {p.stat().st_size} bytes to {rel}", None
        if name == "run_python":
            timeout_s = int(args.get("timeout_s", RUN_TIMEOUT_S))
            if args.get("path"):
                target = _safe_path(workdir, str(args["path"]).strip())
                if not target.exists():
                    return f"ERROR: no such file: {args['path']}", None
                cmd = ["uv", "run", "python", str(target)]
            else:
                code = args.get("code", args.get("_body", ""))
                if not str(code).strip():
                    return "ERROR: run_python needs `code:` or `path:`", None
                with tempfile.NamedTemporaryFile(
                    "w", suffix=".py", dir=workdir, delete=False
                ) as f:
                    f.write(str(code))
                    target = Path(f.name)
                cmd = ["uv", "run", "python", str(target)]
            t0 = time.monotonic()
            try:
                proc = subprocess.run(
                    cmd, capture_output=True, text=True,
                    timeout=timeout_s, cwd=workdir,
                )
            except subprocess.TimeoutExpired:
                return "timeout", None
            dt = time.monotonic() - t0
            out = (proc.stdout or "") + (proc.stderr or "")
            return _truncate(f"exit={proc.returncode} time={dt:.1f}s\n{out.strip()}"), None
        if name == "delegate":
            subprompt = str(args.get("prompt", args.get("_body", ""))).strip()
            if not subprompt:
                return "ERROR: delegate needs `prompt:`", None
            sub = adapter.run(subprompt)
            return _truncate(sub.text), sub
        return f"ERROR: unknown tool {name!r} (want read_file, write_file, run_python, delegate)", None
    except ValueError as e:
        return f"ERROR: {e}", None
    except OSError as e:
        return f"ERROR: {e}", None


def run_agent(adapter, prompt: str, workdir, max_steps: int = 12) -> Completion:
    """Run the tool loop and return a Completion with summed usage."""
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)

    transcript = ""
    trace: list[dict] = []
    tokens_in = tokens_out = 0
    latency = 0.0
    last_text = ""
    reason = "step_cap"
    delegate_used = False

    for step in range(max_steps):
        full_prompt = (
            f"{SYSTEM}\nTASK:\n{prompt}\n"
            + (f"\nTRANSCRIPT SO FAR:\n{transcript}" if transcript else "")
            + f"\nSTEP {step + 1}/{max_steps}: reply with tool calls, or FINAL."
        )
        resp = adapter.run(full_prompt)
        tokens_in += resp.tokens_in
        tokens_out += resp.tokens_out
        latency += resp.latency_s
        last_text = resp.text
        calls = [(m.group(1), _parse_args(m.group(2))) for m in TOOL_FENCE.finditer(resp.text)]
        entry: dict = {"step": step + 1, "output": resp.text[:2000], "calls": [c for c, _ in calls]}
        if FINAL_RE.search(resp.text):
            reason = "final"
            trace.append(entry)
            break
        if not calls:
            reason = "no_tool_calls"
            trace.append(entry)
            break
        observations = []
        for cname, cargs in calls:
            if cname == "delegate":
                if delegate_used:
                    obs, sub = "ERROR: delegate already used (one subagent per task)", None
                else:
                    delegate_used = True
                    obs, sub = _exec_tool(adapter, workdir, cname, cargs)
            else:
                obs, sub = _exec_tool(adapter, workdir, cname, cargs)
            if sub is not None:  # delegate sub-call usage joins the totals
                tokens_in += sub.tokens_in
                tokens_out += sub.tokens_out
                latency += sub.latency_s
            observations.append({"tool": cname, "observation": obs[:2000]})
        entry["observations"] = observations
        trace.append(entry)
        transcript += f"\n--- step {step + 1} assistant ---\n{resp.text}\n"
        for o in observations:
            transcript += f"\n--- {o['tool']} observation ---\n{o['observation']}\n"
    else:
        reason = "step_cap"

    return Completion(
        text=last_text,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        latency_s=latency,
        model=adapter.model,
        raw={"trace": trace, "steps": len(trace), "reason": reason, "workdir": str(workdir)},
    )
