import re
import unicodedata
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from .errors import SectionNotFoundError
from .models import Activity

_WHITESPACE = re.compile(r"\s+")
_COURSE_PREFIX = re.compile(r"^.+?\s+-\s+(.+)$")


def normalized_text(value: str) -> str:
    """Normaliza texto para uma comparação tolerante a caixa, acentos e espaços."""
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    return _WHITESPACE.sub(" ", value).strip().casefold()


def course_name(html: str) -> str | None:
    """Extrai do título do curso apenas o nome legível da disciplina."""
    soup = BeautifulSoup(html, "html.parser")
    selectors = (
        "#page-header .page-header-headings h1",
        ".page-header-headings h1",
        "#page-header h1",
        "h1",
    )
    for selector in selectors:
        heading = soup.select_one(selector)
        if not heading:
            continue
        title = _WHITESPACE.sub(" ", heading.get_text(" ", strip=True)).strip()
        if not title:
            continue
        match = _COURSE_PREFIX.match(title)
        return match.group(1).strip() if match else title
    return None


def _section_title(section: Tag) -> str:
    selectors = (
        ".sectionname",
        "[data-for='section_title']",
        ".section-title",
        "h2",
        "h3",
    )
    for selector in selectors:
        heading = section.select_one(selector)
        if heading:
            text = heading.get_text(" ", strip=True)
            if text:
                return text
    return ""


def list_sections(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    sections = soup.select("li.section, section.course-section, div.course-section")
    return [title for section in sections if (title := _section_title(section))]


def parse_section_activities(
    html: str,
    course_url: str,
    requested_section: str,
) -> tuple[str, list[Activity]]:
    soup = BeautifulSoup(html, "html.parser")
    sections = soup.select("li.section, section.course-section, div.course-section")
    wanted = normalized_text(requested_section)

    matches: list[tuple[Tag, str]] = []
    for section in sections:
        title = _section_title(section)
        normalized_title = normalized_text(title)
        if normalized_title == wanted or wanted in normalized_title:
            matches.append((section, title))

    if not matches:
        available = [
            title for section in sections if (title := _section_title(section))
        ]
        detail = ", ".join(available) if available else "nenhuma seção identificada"
        raise SectionNotFoundError(
            f'Seção "{requested_section}" não encontrada. Disponíveis: {detail}'
        )
    if len(matches) > 1:
        exact = [match for match in matches if normalized_text(match[1]) == wanted]
        if len(exact) == 1:
            matches = exact
        else:
            names = ", ".join(title for _, title in matches)
            raise SectionNotFoundError(
                f'O nome "{requested_section}" é ambíguo. Correspondências: {names}'
            )

    section, title = matches[0]
    activities: list[Activity] = []
    seen: set[str] = set()
    selectors = (
        ".activity a.aalink[href]",
        ".activityinstance > a[href]",
        ".activity a[href*='/mod/']",
    )
    for selector in selectors:
        for link in section.select(selector):
            url = urljoin(course_url, str(link.get("href")))
            if url in seen:
                continue
            name_node = link.select_one(".instancename")
            name = (name_node or link).get_text(" ", strip=True)
            # O Moodle adiciona um texto apenas para leitores de tela após o nome.
            accesshide = link.select_one(".accesshide")
            if accesshide:
                suffix = accesshide.get_text(" ", strip=True)
                if suffix and name.endswith(suffix):
                    name = name[: -len(suffix)].strip()
            if name:
                seen.add(url)
                activities.append(Activity(name=name, url=url))

    return title, activities


def extract_download_links(html: str, page_url: str) -> list[str]:
    """Extrai anexos servidos pelo Moodle de uma página de atividade."""
    soup = BeautifulSoup(html, "html.parser")
    urls: list[str] = []
    seen: set[str] = set()
    selectors = (
        "a[href*='pluginfile.php']",
        "a[href*='webservice/pluginfile.php']",
        "object[data*='pluginfile.php']",
        "iframe[src*='pluginfile.php']",
        "embed[src*='pluginfile.php']",
    )
    for selector in selectors:
        for node in soup.select(selector):
            attribute = (
                "href"
                if node.name == "a"
                else "data"
                if node.name == "object"
                else "src"
            )
            raw_url = node.get(attribute)
            if not raw_url:
                continue
            url = urljoin(page_url, str(raw_url))
            if url not in seen:
                seen.add(url)
                urls.append(url)
    return urls
