import json
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

from econ_eval.adapters.opus import OpusAdapter
from econ_eval.adapters.glm import GLMAdapter, DeepSeekAdapter


def test_opus_parses_cli_json():
    envelope = json.dumps({"result": "the answer is 4",
                           "usage": {"input_tokens": 10, "output_tokens": 5}})
    fake = SimpleNamespace(returncode=0, stdout=envelope, stderr="")
    with patch("econ_eval.adapters.opus.subprocess.run", return_value=fake):
        c = OpusAdapter().run("what is 2+2?")
    assert c.text == "the answer is 4"
    assert c.tokens_in == 10 and c.tokens_out == 5
    assert c.model == "claude-opus-4-8"
    assert c.latency_s >= 0


def test_opus_raises_on_cli_error():
    fake = SimpleNamespace(returncode=1, stdout="", stderr="boom")
    with patch("econ_eval.adapters.opus.subprocess.run", return_value=fake):
        import pytest
        with pytest.raises(RuntimeError):
            OpusAdapter().run("x")


def test_glm_identity():
    a = GLMAdapter()
    assert a.model == "glm-5.2"
    assert a.base_url == "https://api.z.ai/api/anthropic"
    assert a.key_env == "ZAI_API_KEY"


def test_deepseek_identity():
    a = DeepSeekAdapter()
    assert a.model == "deepseek-v4-flash"
    assert a.key_env == "DEEPSEEK_API_KEY"


def test_zai_run_parses_message(monkeypatch):
    a = GLMAdapter()
    fake_msg = SimpleNamespace(
        content=[SimpleNamespace(type="text", text="hello world")],
        usage=SimpleNamespace(input_tokens=7, output_tokens=3),
        id="msg_1",
    )
    fake_client = MagicMock()
    fake_client.messages.create.return_value = fake_msg
    monkeypatch.setattr(a, "_client", lambda: fake_client)
    c = a.run("hi")
    assert c.text == "hello world"
    assert c.tokens_in == 7 and c.tokens_out == 3
    assert c.model == "glm-5.2"


def test_opus_parses_stream_array():
    arr = json.dumps([
        {"type": "system", "subtype": "init"},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "partial"}],
                                          "usage": {"input_tokens": 999, "output_tokens": 1}}},
        {"type": "result", "result": "ANSWER: 42",
         "usage": {"input_tokens": 12000, "output_tokens": 7}},
    ])
    fake = SimpleNamespace(returncode=0, stdout=arr, stderr="")
    with patch("econ_eval.adapters.opus.subprocess.run", return_value=fake):
        c = OpusAdapter().run("q")
    assert c.text == "ANSWER: 42"
    assert c.tokens_in == 12000 and c.tokens_out == 7
