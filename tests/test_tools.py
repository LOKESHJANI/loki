from loki import config
from loki.tools import system


class FakeRun:
    def __init__(self, returncode=0, stderr=""):
        self.calls, self.returncode, self.stderr = [], returncode, stderr

    def __call__(self, cmd, **kwargs):
        self.calls.append(cmd)
        return type("R", (), {"returncode": self.returncode, "stderr": self.stderr, "stdout": ""})()


def test_open_url_uses_named_browser(monkeypatch):
    run = FakeRun()
    monkeypatch.setattr(system.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(system.subprocess, "run", run)
    assert system.open_url("linkedin.com", browser="Google Chrome") == "Opened https://linkedin.com in Google Chrome"
    assert run.calls == [["open", "-a", "Google Chrome", "https://linkedin.com"]]


def test_open_url_falls_back_to_preferred_browser(monkeypatch):
    run = FakeRun()
    monkeypatch.setattr(system.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(system.subprocess, "run", run)
    monkeypatch.setattr(config.settings, "browser", "Safari")
    assert "in Safari" in system.open_url("https://youtube.com")


def test_open_url_reports_failure_honestly(monkeypatch):
    monkeypatch.setattr(system.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(system.subprocess, "run", FakeRun(returncode=1, stderr="Unable to find application"))
    assert system.open_url("x.com", browser="Netscape").startswith("Could not open")


def test_load_dotenv_respects_existing_env(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text('# comment\nLOKI_TEST_A="Google Chrome"\nLOKI_TEST_B=from_file\n')
    monkeypatch.delenv("LOKI_TEST_A", raising=False)
    monkeypatch.setenv("LOKI_TEST_B", "from_shell")
    config.load_dotenv(env)
    import os

    assert os.environ["LOKI_TEST_A"] == "Google Chrome"
    assert os.environ["LOKI_TEST_B"] == "from_shell"
    monkeypatch.delenv("LOKI_TEST_A")
