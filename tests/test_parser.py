import pytest

from moodle_section_dl.errors import SectionNotFoundError
from moodle_section_dl.parser import (
    course_name,
    extract_download_links,
    list_sections,
    parse_section_activities,
)

COURSE_HTML = """
<div id="page-course-view">
  <ul>
    <li class="section main clearfix" data-sectionid="2">
      <h3 class="sectionname">Unidade 2 - Processos</h3>
    </li>
    <li class="section main clearfix" data-sectionid="3">
      <h3 class="sectionname">Unidade 3 - Gerência de Memória</h3>
      <ul class="section img-text">
        <li class="activity resource modtype_resource">
          <div class="activityinstance">
            <a class="aalink" href="/mod/resource/view.php?id=101">
              <span class="instancename">Memória física <span class="accesshide">Arquivo</span></span>
            </a>
          </div>
        </li>
        <li class="activity folder modtype_folder">
          <div class="activityinstance">
            <a class="aalink" href="https://moodle.example/mod/folder/view.php?id=102">
              <span class="instancename">Slides extras</span>
            </a>
          </div>
        </li>
      </ul>
    </li>
  </ul>
</div>
"""


def test_extracts_subject_name_from_course_heading():
    html = """
    <header id="page-header">
      <div class="page-header-headings">
        <h1>INE5608-04238A (20262) - Análise e Projeto de Sistemas</h1>
      </div>
    </header>
    """

    assert course_name(html) == "Análise e Projeto de Sistemas"


def test_lists_and_selects_section_ignoring_accents_and_case():
    assert list_sections(COURSE_HTML)[:2] == [
        "Unidade 2 - Processos",
        "Unidade 3 - Gerência de Memória",
    ]

    title, activities = parse_section_activities(
        COURSE_HTML,
        "https://moodle.example/course/view.php?id=1",
        "gerencia de memoria",
    )

    assert title == "Unidade 3 - Gerência de Memória"
    assert [(item.name, item.url) for item in activities] == [
        ("Memória física", "https://moodle.example/mod/resource/view.php?id=101"),
        ("Slides extras", "https://moodle.example/mod/folder/view.php?id=102"),
    ]


def test_reports_available_sections_when_section_is_missing():
    with pytest.raises(SectionNotFoundError, match="Unidade 2 - Processos"):
        parse_section_activities(COURSE_HTML, "https://moodle.example", "Unidade 9")


def test_extracts_unique_pluginfile_links_from_activity_page():
    html = """
    <a href="/pluginfile.php/1/mod_folder/content/0/a.pdf">A</a>
    <a href="/pluginfile.php/1/mod_folder/content/0/a.pdf">A novamente</a>
    <object data="/pluginfile.php/1/mod_resource/content/1/b.pdf"></object>
    <a href="https://example.org/not-a-file">fora</a>
    """
    assert extract_download_links(
        html, "https://moodle.example/mod/folder/view.php"
    ) == [
        "https://moodle.example/pluginfile.php/1/mod_folder/content/0/a.pdf",
        "https://moodle.example/pluginfile.php/1/mod_resource/content/1/b.pdf",
    ]
