from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import questionary
from dotenv import load_dotenv
from prompt_toolkit.layout.processors import PasswordProcessor

from .client import MoodleClient
from .errors import MoodleDownloadError, SectionNotFoundError
from .models import DownloadReport
from .parser import list_sections


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="moodle-section-dl",
        description="Baixa os arquivos de uma seção de um curso Moodle.",
    )
    parser.add_argument("course_url", help="URL da página do curso")
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument(
        "--section",
        "-s",
        help="nome completo ou trecho único do título da seção",
    )
    selection.add_argument(
        "--list-sections",
        action="store_true",
        help="lista as seções disponíveis e não baixa arquivos",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("downloads"),
        help="diretório de destino (padrão: ./downloads)",
    )
    parser.add_argument(
        "--username",
        "-u",
        default=os.environ.get("UFSC_USERNAME"),
        help="idUFSC (ou use UFSC_USERNAME)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="sobrescreve arquivos com o mesmo nome",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="timeout HTTP em segundos (padrão: 30)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    load_dotenv(Path.cwd() / ".env")
    args = build_parser().parse_args(argv)
    username = args.username or input("idUFSC: ").strip()
    password = os.environ.get("UFSC_PASSWORD") or prompt_password()
    if not username or not password:
        print("erro: usuário e senha são obrigatórios", file=sys.stderr)
        return 2

    client = MoodleClient(timeout=args.timeout)
    try:
        print("Autenticando no Moodle da UFSC…")
        course_html = client.login(args.course_url, username, password)
        if args.list_sections:
            sections = list_sections(course_html)
            if not sections:
                raise SectionNotFoundError("Nenhuma seção foi encontrada no curso.")
            print("\nSeções disponíveis:")
            for section in sections:
                print(f"  - {section}")
            return 0

        if args.section:
            selected_sections = [args.section]
        else:
            sections = list_sections(course_html)
            if not sections:
                raise SectionNotFoundError("Nenhuma seção foi encontrada no curso.")
            selected_sections = choose_sections(sections)
            if not selected_sections:
                print("Nenhuma seção selecionada.")
                return 0

        total_files = 0
        total_skipped = 0
        for selected_section in selected_sections:
            print(f'Procurando a seção "{selected_section}"…')
            title, report = client.download_section(
                args.course_url,
                course_html,
                selected_section,
                args.output.expanduser().resolve(),
                overwrite=args.overwrite,
            )
            print_report(title, report)
            total_files += len(report.files)
            total_skipped += len(report.skipped)
    except MoodleDownloadError as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 1

    print(
        f"\nConcluído: {total_files} arquivo(s) baixado(s), "
        f"{total_skipped} atividade(s) ignorada(s), "
        f"{len(selected_sections)} seção(ões) processada(s)."
    )
    return 0


def choose_sections(sections: list[str]) -> list[str]:
    answer = questionary.checkbox(
        "Selecione as seções para baixar:",
        choices=sections,
        instruction="(↑/↓ navegar, Espaço marcar, Enter confirmar)",
    ).ask()
    return list(answer) if answer else []


def prompt_password() -> str:
    """Solicita a senha exibindo uma bolinha para cada caractere digitado."""
    answer = questionary.text(
        "Senha:",
        input_processors=[PasswordProcessor(char="●")],
    ).ask()
    return answer or ""


def print_report(title: str, report: DownloadReport) -> None:
    print(f"\n{title}")
    for downloaded in report.files:
        print(f"  ✓ {downloaded.path} ({format_size(downloaded.size)})")
    for skipped in report.skipped:
        print(f"  – {skipped.name}: {skipped.reason}")


def format_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KiB", "MiB", "GiB"):
        if value < 1024 or unit == "GiB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{size} B"


if __name__ == "__main__":
    raise SystemExit(main())
