from __future__ import annotations

import mimetypes
import re
import unicodedata
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from .errors import AuthenticationError, MoodleDownloadError
from .models import Activity, DownloadedFile, DownloadReport, SkippedActivity
from .parser import course_name, extract_download_links, parse_section_activities

_INVALID_FILENAME = re.compile(r"[^\w.()\[\] -]+", re.UNICODE)
_CONTENT_DISPOSITION_FILENAME = re.compile(
    r"filename\*=(?:UTF-8'')?([^;]+)|filename=\"?([^\";]+)", re.IGNORECASE
)


class MoodleClient:
    def __init__(self, timeout: float = 30.0) -> None:
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "Chrome/145.0 Safari/537.36 moodle-section-dl/0.1"
                )
            }
        )

    def _get(self, url: str, *, stream: bool = False) -> requests.Response:
        try:
            response = self.session.get(url, timeout=self.timeout, stream=stream)
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            raise MoodleDownloadError(f"Falha ao acessar {url}: {exc}") from exc

    def login(self, course_url: str, username: str, password: str) -> str:
        """Autentica no CAS seguindo os redirecionamentos iniciados pelo Moodle."""
        response = self._get(course_url)
        if self._looks_like_course(response):
            return response.text

        # Quando o curso redireciona primeiro para enrol/index.php, o formulário
        # encontrado ainda pertence ao Moodle. Abrir seu action com GET inicia o
        # redirecionamento correto para o CAS; enviar as credenciais diretamente
        # a esse formulário produz uma falsa mensagem de usuário/senha errados.
        if not _is_cas_url(response.url):
            moodle_soup = BeautifulSoup(response.text, "html.parser")
            moodle_form = moodle_soup.find("form")
            if moodle_form and moodle_form.get("action"):
                response = self._get(
                    urljoin(response.url, str(moodle_form.get("action")))
                )

        soup = BeautifulSoup(response.text, "html.parser")
        form = soup.find("form", id="fm1") or soup.find("form")
        if not form or not form.get("action"):
            raise AuthenticationError(
                "O Moodle não exibiu a página do curso nem um formulário de login."
            )

        payload: dict[str, str] = {}
        for input_tag in form.select("input[name]"):
            name = input_tag.get("name")
            if isinstance(name, str):
                payload[name] = str(input_tag.get("value") or "")
        payload["username"] = username
        payload["password"] = password

        login_url = urljoin(response.url, str(form.get("action")))
        try:
            authenticated = self.session.post(
                login_url,
                data=payload,
                timeout=self.timeout,
                allow_redirects=True,
            )
            authenticated.raise_for_status()
        except requests.RequestException as exc:
            raise AuthenticationError(f"Falha durante o login: {exc}") from exc

        # Alguns fluxos do CAS concluem em uma página intermediária; pedir o curso
        # novamente também confirma que o cookie do Moodle foi criado.
        course = self._get(course_url)
        if not self._looks_like_course(course):
            raise AuthenticationError(
                "Login recusado ou curso inacessível. Confira usuário, senha e matrícula."
            )
        return course.text

    @staticmethod
    def _looks_like_course(response: requests.Response) -> bool:
        url = response.url.casefold()
        if "/login" in url or "sistemas.ufsc.br/login" in url:
            return False
        soup = BeautifulSoup(response.text, "html.parser")
        return bool(
            soup.select_one(
                "#page-course-view, li.section, section.course-section, div.course-section"
            )
        )

    def download_section(
        self,
        course_url: str,
        course_html: str,
        section_name: str,
        output_dir: Path,
        *,
        overwrite: bool = False,
    ) -> tuple[str, DownloadReport]:
        title, activities = parse_section_activities(
            course_html, course_url, section_name
        )
        course_dir = output_dir / course_directory_name(course_html, course_url)
        section_dir = course_dir / safe_filename(title, fallback="secao")
        section_dir.mkdir(parents=True, exist_ok=True)

        files: list[DownloadedFile] = []
        skipped: list[SkippedActivity] = []
        for activity in activities:
            activity_files = self._download_activity(activity, section_dir, overwrite)
            if activity_files:
                files.extend(activity_files)
            else:
                skipped.append(
                    SkippedActivity(
                        name=activity.name,
                        url=activity.url,
                        reason="atividade sem arquivo baixável",
                    )
                )
        return title, DownloadReport(tuple(files), tuple(skipped))

    def _download_activity(
        self, activity: Activity, section_dir: Path, overwrite: bool
    ) -> list[DownloadedFile]:
        response = self._get(activity.url, stream=True)
        content_type = (
            response.headers.get("Content-Type", "").split(";", 1)[0].casefold()
        )
        disposition = response.headers.get("Content-Disposition", "")

        if not _is_html(content_type) or "attachment" in disposition.casefold():
            return [self._save_response(response, activity, section_dir, overwrite)]

        # A resposta HTML é pequena e precisa ser consumida antes de procurar anexos.
        html = response.text
        links = extract_download_links(html, response.url)
        downloaded: list[DownloadedFile] = []
        for link in links:
            file_response = self._get(link, stream=True)
            file_type = file_response.headers.get("Content-Type", "").split(";", 1)[0]
            if _is_html(file_type):
                continue
            downloaded.append(
                self._save_response(file_response, activity, section_dir, overwrite)
            )
        return downloaded

    def _save_response(
        self,
        response: requests.Response,
        activity: Activity,
        section_dir: Path,
        overwrite: bool,
    ) -> DownloadedFile:
        filename = response_filename(response, activity.name)
        target = unique_target(section_dir / filename, overwrite=overwrite)
        temporary = target.with_name(f".{target.name}.part")
        size = 0
        try:
            with temporary.open("wb") as file:
                for chunk in response.iter_content(chunk_size=128 * 1024):
                    if chunk:
                        file.write(chunk)
                        size += len(chunk)
            temporary.replace(target)
        except OSError as exc:
            temporary.unlink(missing_ok=True)
            raise MoodleDownloadError(
                f"Não foi possível salvar {target}: {exc}"
            ) from exc
        return DownloadedFile(activity.name, response.url, target, size)


def _is_html(content_type: str) -> bool:
    return content_type.casefold() in {"text/html", "application/xhtml+xml"}


def _is_cas_url(url: str) -> bool:
    hostname = (urlparse(url).hostname or "").casefold()
    return hostname == "sistemas.ufsc.br" or hostname.endswith(".sistemas.ufsc.br")


def safe_filename(value: str, *, fallback: str = "arquivo") -> str:
    value = unicodedata.normalize("NFC", value)
    value = value.replace("/", "-").replace("\\", "-").strip(" .")
    value = _INVALID_FILENAME.sub("_", value)
    return value[:180].rstrip(" .") or fallback


def course_directory_name(course_html: str, course_url: str) -> str:
    """Cria o nome da pasta da disciplina a partir do título da página."""
    name = course_name(course_html)
    if name:
        hyphenated = re.sub(r"\s+", "-", name.strip())
        return safe_filename(hyphenated, fallback="curso")

    course_id = re.search(r"(?:[?&]id=)(\d+)", course_url)
    return f"curso-{course_id.group(1)}" if course_id else "curso"


def response_filename(response: requests.Response, activity_name: str) -> str:
    disposition = response.headers.get("Content-Disposition", "")
    match = _CONTENT_DISPOSITION_FILENAME.search(disposition)
    raw_name = ""
    if match:
        raw_name = unquote((match.group(1) or match.group(2)).strip().strip('"'))
    if not raw_name:
        raw_name = unquote(Path(urlparse(response.url).path).name)

    content_type = response.headers.get("Content-Type", "").split(";", 1)[0]
    if not raw_name or raw_name.casefold() in {"view.php", "pluginfile.php"}:
        raw_name = activity_name
    if not Path(raw_name).suffix:
        extension = mimetypes.guess_extension(content_type) or ""
        raw_name += extension
    return safe_filename(raw_name)


def unique_target(path: Path, *, overwrite: bool) -> Path:
    if overwrite or not path.exists():
        return path
    counter = 2
    while True:
        candidate = path.with_name(f"{path.stem} ({counter}){path.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1
