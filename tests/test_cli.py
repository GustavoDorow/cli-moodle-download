from pathlib import Path

from moodle_section_dl import cli
from moodle_section_dl.models import DownloadReport


def test_main_prompts_for_credentials_when_env_is_missing(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("UFSC_USERNAME", raising=False)
    monkeypatch.delenv("UFSC_PASSWORD", raising=False)
    monkeypatch.setattr("builtins.input", lambda prompt: "usuario_digitado")
    monkeypatch.setattr(cli, "prompt_password", lambda: "senha_digitada")
    received: dict[str, str] = {}

    class FakeClient:
        def __init__(self, timeout: float):
            pass

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
    assert received == {
        "username": "usuario_digitado",
        "password": "senha_digitada",
    }


def test_password_prompt_masks_each_character_with_a_dot(monkeypatch):
    received: dict[str, object] = {}

    class FakeQuestion:
        def ask(self):
            return "senha_digitada"

    def fake_text(message: str, **kwargs):
        received.update(message=message, **kwargs)
        return FakeQuestion()

    monkeypatch.setattr(cli.questionary, "text", fake_text)

    assert cli.prompt_password() == "senha_digitada"
    assert received["message"] == "Senha:"
    processors = received["input_processors"]
    assert isinstance(processors, list)
    assert len(processors) == 1
    assert processors[0].char == "●"


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


def test_url_only_opens_interactive_selection(tmp_path: Path, monkeypatch, capsys):
    (tmp_path / ".env").write_text(
        "UFSC_USERNAME=usuario_env\nUFSC_PASSWORD=senha_env\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("UFSC_USERNAME", raising=False)
    monkeypatch.delenv("UFSC_PASSWORD", raising=False)
    downloaded: list[str] = []

    class FakeClient:
        def __init__(self, timeout: float):
            pass

        def login(self, course_url: str, username: str, password: str) -> str:
            return """
            <ul class="topics">
              <li class="section course-section"><h3 class="sectionname">Geral</h3></li>
              <li class="section course-section"><h3 class="sectionname">Unidade 3</h3></li>
            </ul>
            """

        def download_section(
            self, course_url, course_html, section_name, output_dir, *, overwrite
        ):
            downloaded.append(section_name)
            return section_name, DownloadReport((), ())

    monkeypatch.setattr(cli, "MoodleClient", FakeClient)
    monkeypatch.setattr(
        cli,
        "choose_sections",
        lambda sections: [sections[1]],
    )

    result = cli.main(["https://moodle.example/course/view.php?id=1"])

    assert result == 0
    assert downloaded == ["Unidade 3"]
    assert "1 seção(ões) processada(s)" in capsys.readouterr().out
