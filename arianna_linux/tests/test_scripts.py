import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from arianna_linux.letsgo import choose_script, run_script
from arianna_linux.bridge import decide_and_run


def test_choose_script_deterministic():
    assert choose_script("hello") == choose_script("hello")


def test_run_script_executes_code():
    out = run_script('print("hi")')
    assert out.strip() == "hi"


def test_decide_and_run_returns_output():
    result = decide_and_run("test message")
    assert isinstance(result, str)
    assert result
    assert not re.search(r"error", result, re.IGNORECASE)
