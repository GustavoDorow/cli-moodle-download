from pathlib import Path

from requests import Response

from moodle_section_dl.client import (
    MoodleClient,
    course_directory_name,
    response_filename,
    safe_filename,
    unique_target,
)


def make_response(url: str, content_type: str, disposition: str = "") -> Response:
    response = Response()
    response.url = url
    response.headers["Content-Type"] = content_type
    if disposition:
        response.headers["Content-Disposition"] = disposition
    return response


def test_filename_prefers_content_disposition_and_decodes_utf8():
    response = make_response(
        "https://moodle.example/pluginfile.php/1/file",
        "application/pdf",
        "attachment; filename*=UTF-8''Mem%C3%B3ria%20virtual.pdf",
    )
    assert response_filename(response, "Aula") == "Memória virtual.pdf"


def test_filename_falls_back_to_activity_and_content_type():
    response = make_response(
        "https://moodle.example/mod/resource/view.php?id=2", "application/pdf"
    )
    assert (
        response_filename(response, "Projeto / paginação") == "Projeto - paginação.pdf"
    )


def test_safe_filename_blocks_path_traversal():
    assert safe_filename("../../Unidade\\arquivo?.pdf") == "-..-Unidade-arquivo_.pdf"


def test_course_directory_uses_subject_name_with_hyphens():
    html = """
    <div id="page-header"><h1>
      INE5608-04238A (20262) - Análise e Projeto de Sistemas
    </h1></div>
    """
    assert course_directory_name(
        html, "https://presencial.moodle.ufsc.br/course/view.php?id=54910"
    ) == "Análise-e-Projeto-de-Sistemas"


def test_course_directory_falls_back_to_course_id():
    assert course_directory_name(
        "<html></html>",
        "https://presencial.moodle.ufsc.br/course/view.php?id=54910",
    ) == "curso-54910"


def test_unique_target_adds_counter(tmp_path: Path):
    original = tmp_path / "slide.pdf"
    original.write_bytes(b"existing")
    assert unique_target(original, overwrite=False).name == "slide (2).pdf"
    assert unique_target(original, overwrite=True) == original


class FakeMoodleClient(MoodleClient):
    def __init__(self, responses: dict[str, Response]) -> None:
        super().__init__()
        self.responses = responses

    def _get(self, url: str, *, stream: bool = False) -> Response:
        return self.responses[url]


def content_response(
    url: str,
    content_type: str,
    body: bytes,
    disposition: str = "",
) -> Response:
    response = make_response(url, content_type, disposition)
    response.status_code = 200
    response._content = body
    response._content_consumed = True
    return response


def html_response(url: str, body: str, status: int = 200) -> Response:
    return content_response(url, "text/html", body.encode())


class LoginSession:
    def __init__(self, get_responses: list[Response], post_response: Response):
        self.headers: dict[str, str] = {}
        self.get_responses = iter(get_responses)
        self.post_response = post_response
        self.post_url = ""
        self.post_data: dict[str, str] = {}

    def get(self, url: str, **kwargs) -> Response:
        return next(self.get_responses)

    def post(self, url: str, data: dict[str, str], **kwargs) -> Response:
        self.post_url = url
        self.post_data = data
        return self.post_response


def test_login_opens_moodle_form_before_submitting_credentials_to_cas():
    course_url = "https://presencial.moodle.ufsc.br/course/view.php?id=52983"
    enrol_page = html_response(
        "https://presencial.moodle.ufsc.br/enrol/index.php?id=52983",
        '<form action="https://presencial.moodle.ufsc.br/login/index.php"></form>',
    )
    cas_page = html_response(
        "https://sistemas.ufsc.br/login?service=moodle",
        """
        <form id="fm1" action="login">
          <input name="username">
          <input name="password">
          <input type="hidden" name="execution" value="token-cas">
        </form>
        """,
    )
    post_response = html_response(course_url, "<html>retorno do CAS</html>")
    course_page = html_response(
        course_url,
        '<div id="page-course-view"><li class="section"></li></div>',
    )
    session = LoginSession([enrol_page, cas_page, course_page], post_response)
    client = MoodleClient()
    client.session = session

    html = client.login(course_url, "usuario", "senha")

    assert "page-course-view" in html
    assert session.post_url == "https://sistemas.ufsc.br/login"
    assert session.post_data == {
        "username": "usuario",
        "password": "senha",
        "execution": "token-cas",
    }


def test_download_section_handles_direct_file_folder_and_interactive_activity(
    tmp_path: Path,
):
    course_url = "https://moodle.example/course/view.php?id=1"
    direct_url = "https://moodle.example/mod/resource/view.php?id=11"
    folder_url = "https://moodle.example/mod/folder/view.php?id=12"
    quiz_url = "https://moodle.example/mod/quiz/view.php?id=13"
    attachment_url = (
        "https://moodle.example/pluginfile.php/12/mod_folder/content/0/b.pdf"
    )
    course_html = f"""
    <div id="page-header"><h1>INE5608 (20262) - Sistemas Operacionais</h1></div>
    <div id="page-course-view"><li class="section">
      <h3 class="sectionname">Unidade 3</h3>
      <div class="activity"><a class="aalink" href="{direct_url}"><span class="instancename">A</span></a></div>
      <div class="activity"><a class="aalink" href="{folder_url}"><span class="instancename">Pasta</span></a></div>
      <div class="activity"><a class="aalink" href="{quiz_url}"><span class="instancename">Quiz</span></a></div>
    </li></div>
    """
    folder_html = f'<a href="{attachment_url}">B</a>'.encode()
    client = FakeMoodleClient(
        {
            direct_url: content_response(
                "https://moodle.example/pluginfile.php/11/a.pdf",
                "application/pdf",
                b"pdf-a",
            ),
            folder_url: content_response(folder_url, "text/html", folder_html),
            attachment_url: content_response(
                attachment_url,
                "application/pdf",
                b"pdf-b",
            ),
            quiz_url: content_response(quiz_url, "text/html", b"<form>quiz</form>"),
        }
    )

    title, report = client.download_section(
        course_url, course_html, "Unidade 3", tmp_path
    )

    assert title == "Unidade 3"
    assert [item.path.name for item in report.files] == ["a.pdf", "b.pdf"]
    assert all(
        item.path.parent == tmp_path / "Sistemas-Operacionais" / "Unidade 3"
        for item in report.files
    )
    assert [item.path.read_bytes() for item in report.files] == [b"pdf-a", b"pdf-b"]
    assert [item.name for item in report.skipped] == ["Quiz"]
