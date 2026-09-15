"""Offline unit tests for the pilot agent track. No live model calls."""
import json

from econ_eval import runner
from econ_eval.agent_loop import TOOL_FENCE, _parse_args, run_agent
from econ_eval.graders import artifact
from econ_eval.models import Completion, Task


class ScriptedAdapter:
    """Replays scripted main responses; sub_map serves delegate sub-calls."""

    def __init__(self, model="fake-model", script=(), sub_map=None,
                 tokens_in=10, tokens_out=20):
        self.name = model
        self.model = model
        self.script = list(script)
        self.sub_map = sub_map or {}
        self.calls = 0
        self.sub_calls = 0
        self.tokens_in = tokens_in
        self.tokens_out = tokens_out

    def run(self, prompt):
        if prompt in self.sub_map:
            self.sub_calls += 1
            return Completion(self.sub_map[prompt], 3, 7, 0.01, self.model)
        assert self.script, "adapter called past end of script"
        self.calls += 1
        return Completion(self.script.pop(0), self.tokens_in, self.tokens_out, 0.01,
                          self.model)


def fence(name, body):
    return f"```tool {name}\n{body}\n```"


def agent_task(grader, **kw):
    return Task(id="agent-scratch", track="agent", prompt="do the thing",
                grader=grader, source="unit test", samples=1, **kw)


# --- protocol parsing ---

def test_parse_args_key_value_and_greedy_content():
    args = _parse_args("path: a.txt\ncontent:\nline1\nline2\n")
    assert args == {"path": "a.txt", "content": "line1\nline2"}
    assert _parse_args('{"path": "b.txt"}') == {"path": "b.txt"}
    assert _parse_args("") == {}


def test_tool_fence_regex_finds_named_block():
    text = "thinking\n" + fence("read_file", "path: x.txt") + "\ntrailing"
    found = list(TOOL_FENCE.finditer(text))
    assert [(m.group(1), m.group(2).strip()) for m in found] == [("read_file", "path: x.txt")]


def test_loop_write_then_final(tmp_path):
    a = ScriptedAdapter(script=[
        "first\n" + fence("write_file", "path: answer.txt\ncontent:\nhello"),
        "FINAL: wrote answer.txt with hello",
    ])
    comp = run_agent(a, "write hello", tmp_path, max_steps=5)
    assert (tmp_path / "answer.txt").read_text() == "hello"
    assert comp.text.startswith("FINAL")
    assert (comp.tokens_in, comp.tokens_out) == (20, 40)  # 2 calls summed
    assert comp.raw["reason"] == "final"
    assert [e["calls"] for e in comp.raw["trace"]] == [["write_file"], []]


def test_run_python_observation_flows_back(tmp_path):
    a = ScriptedAdapter(script=[
        fence("run_python", "code:\nprint(6*7)"),
        "FINAL: 42",
    ])
    comp = run_agent(a, "compute", tmp_path)
    obs = comp.raw["trace"][0]["observations"][0]["observation"]
    assert "exit=0" in obs and "42" in obs


def test_read_missing_file_reports_error(tmp_path):
    a = ScriptedAdapter(script=[
        fence("read_file", "path: nope.txt"),
        "FINAL: file is missing",
    ])
    comp = run_agent(a, "read", tmp_path)
    assert "ERROR" in comp.raw["trace"][0]["observations"][0]["observation"]
    assert comp.raw["reason"] == "final"


def test_path_escape_blocked(tmp_path):
    a = ScriptedAdapter(script=[
        fence("write_file", "path: ../evil.txt\ncontent:\nx"),
        "FINAL: done",
    ])
    run_agent(a, "escape", tmp_path / "wd")
    assert not (tmp_path / "evil.txt").exists()


def test_step_cap(tmp_path):
    a = ScriptedAdapter(script=[fence("read_file", "path: a.txt")] * 10)
    comp = run_agent(a, "loop forever", tmp_path, max_steps=3)
    assert a.calls == 3
    assert comp.raw["reason"] == "step_cap"


def test_no_tool_calls_ends_loop(tmp_path):
    a = ScriptedAdapter(script=["just prose, no tools, no final marker"])
    comp = run_agent(a, "prose", tmp_path)
    assert a.calls == 1
    assert comp.raw["reason"] == "no_tool_calls"


# --- delegate: one nested call, depth 1 ---

def test_delegate_single_use_sums_usage_and_no_recursion(tmp_path):
    sub_reply = fence("write_file", "path: pwned.txt\ncontent:\nx")
    a = ScriptedAdapter(
        script=[fence("delegate", "prompt: SUBQ"), "FINAL: got help"],
        sub_map={"SUBQ": sub_reply},
    )
    comp = run_agent(a, "delegate me", tmp_path)
    assert a.sub_calls == 1
    assert not (tmp_path / "pwned.txt").exists()  # sub output never parsed
    assert (comp.tokens_in, comp.tokens_out) == (2 * 10 + 3, 2 * 20 + 7)
    assert sub_reply in comp.raw["trace"][0]["observations"][0]["observation"]


def test_delegate_second_use_refused(tmp_path):
    a = ScriptedAdapter(
        script=[fence("delegate", "prompt: SUBQ"),
                fence("delegate", "prompt: SUBQ"),
                "FINAL: done"],
        sub_map={"SUBQ": "help"},
    )
    comp = run_agent(a, "twice", tmp_path)
    assert a.sub_calls == 1
    assert "already used" in comp.raw["trace"][1]["observations"][0]["observation"]


# --- artifact grader ---

def numeric_grader(**kw):
    g = {"type": "artifact", "mode": "numeric-on-file",
         "file": "result.txt", "reference": 8412034, "tolerance_pct": 0.5}
    g.update(kw)
    return g


def test_artifact_numeric_pass_and_fail(tmp_path):
    (tmp_path / "result.txt").write_text("gdp 8412034\n")
    t = agent_task(numeric_grader())
    assert artifact.grade(t, "FINAL", tmp_path).passed is True
    t2 = agent_task(numeric_grader(reference=9000000))
    assert artifact.grade(t2, "FINAL", tmp_path).passed is False


def test_artifact_numeric_pattern_and_missing(tmp_path):
    (tmp_path / "result.txt").write_text("value=42.5 units\n")
    t = agent_task(numeric_grader(file="result.txt", reference=42.5,
                                  pattern=r"value=([\d.]+)"))
    assert artifact.grade(t, "FINAL", tmp_path).passed is True
    t_missing = agent_task(numeric_grader(file="absent.txt", reference=1))
    assert artifact.grade(t_missing, "FINAL", tmp_path).passed is False
    t_nomatch = agent_task(numeric_grader(reference=1, pattern=r"zzz=(\d+)"))
    assert artifact.grade(t_nomatch, "FINAL", tmp_path).passed is False


def assertions_grader(assertions):
    return {"type": "artifact", "mode": "assertions-on-file",
            "assertions": assertions}


def test_artifact_assertions_pass_and_fail(tmp_path):
    (tmp_path / "data.csv").write_text("a,b\n1,2\n")
    good = agent_task(assertions_grader(
        "import csv\nrows=list(csv.DictReader(open('data.csv')))\nassert rows==[{'a':'1','b':'2'}]"))
    assert artifact.grade(good, "FINAL", tmp_path).passed is True
    bad = agent_task(assertions_grader("assert False, 'boom'"))
    g = artifact.grade(bad, "FINAL", tmp_path)
    assert g.passed is False and "boom" in g.detail


def test_artifact_unknown_mode_fails():
    t = agent_task({"type": "artifact", "mode": "magic"})
    assert artifact.grade(t, "FINAL", "/tmp").passed is False


def test_grade_sample_dispatches_artifact(tmp_path):
    (tmp_path / "result.txt").write_text("ANSWER 100\n")
    t = agent_task(numeric_grader(reference=100))
    assert runner.grade_sample(t, "FINAL", judge=None, workdir=tmp_path).passed is True


# --- runner: agent track end to end (still offline) ---

def test_runner_agent_track_grades_workdir(tmp_path):
    t = agent_task(assertions_grader("assert open('answer.txt').read() == 'hello'"))
    a = ScriptedAdapter(script=[
        fence("write_file", "path: answer.txt\ncontent:\nhello"),
        "FINAL: wrote it",
    ])
    tr, db = tmp_path / "tr.jsonl", tmp_path / "s.sqlite"
    made = runner.run([t], {"fake": a}, judge=None, n=1,
                      transcripts_path=tr, db_path=db)
    assert made == 1
    row = json.loads(tr.read_text().splitlines()[0])
    assert row["passed"] is True and row["trace"][0]["calls"] == ["write_file"]
    made2 = runner.run([t], {"fake": a}, judge=None, n=1,
                       transcripts_path=tr, db_path=db)
    assert made2 == 0  # cached like every other track
