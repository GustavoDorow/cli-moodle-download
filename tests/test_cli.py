from pathlib import Path

from moodle_section_dl import cli
from moodle_section_dl.models import DownloadReport


def test_main_loads_credentials_from_dotenv(tmp_path: Path, monkeypatch):
    (tmp_path / ".env").write_text(
        "UFSC_USERNAME=usuario_env\nUFSC_PASSWORD=senha_env\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("UFSC_USERNAME", raising=False)
    monkeypatch.delenv("UFSC_PASSWORD", raising=False)
    received: dict[str, str] = {}

    class FakeClient:
        def __init__(self, timeout: float):
            received["timeout"] = str(timeout)

        def login(self, course_url: str, username: str, password: str) -> str:
            received.update(username=username, password=password)
            return "<html></html>"

        def download_section(self, *args, **kwargs):
            return "Unidade 3", DownloadReport((), ())

    monkeypatch.setattr(cli, "MoodleClient", FakeClient)

    result = cli.main(
        ["https://moodle.example/course/view.php?id=1", "-s", "Unidade 3"]
    )

    assert result == 0
    assert received["username"] == "usuario_env"
    assert received["password"] == "senha_env"


def test_list_sections_prints_available_titles(tmp_path: Path, monkeypatch, capsys):
    (tmp_path / ".env").write_text(
        "UFSC_USERNAME=usuario_env\nUFSC_PASSWORD=senha_env\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("UFSC_USERNAME", raising=False)
    monkeypatch.delenv("UFSC_PASSWORD", raising=False)

    class FakeClient:
        def __init__(self, timeout: float):
            pass

        def login(self, course_url: str, username: str, password: str) -> str:
            return """
            <ul class="topics">
              <li class="section course-section"><h3 class="sectionname">Geral</h3></li>
              <li class="section course-section"><h3 class="sectionname">Unidade 3 - Gerência de Memória</h3></li>
            </ul>
            """

    monkeypatch.setattr(cli, "MoodleClient", FakeClient)

    result = cli.main(
        ["https://moodle.example/course/view.php?id=1", "--list-sections"]
    )

    assert result == 0
    output = capsys.readouterr().out
    assert "Seções disponíveis:" in output
    assert "  - Geral" in output
    assert "  - Unidade 3 - Gerência de Memória" in output
