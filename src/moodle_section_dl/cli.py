from __future__ import annotations

import argparse
import getpass
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from .client import MoodleClient
from .errors import MoodleDownloadError, SectionNotFoundError
from .parser import list_sections


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="moodle-section-dl",
        description="Baixa os arquivos de uma seção de um curso Moodle.",
    )
    parser.add_argument("course_url", help="URL da página do curso")
    selection = parser.add_mutually_exclusive_group(required=True)
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
    password = os.environ.get("UFSC_PASSWORD") or getpass.getpass("Senha: ")
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

        print(f'Procurando a seção "{args.section}"…')
        title, report = client.download_section(
            args.course_url,
            course_html,
            args.section,
            args.output.expanduser().resolve(),
            overwrite=args.overwrite,
        )
    except MoodleDownloadError as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 1

    print(f"\n{title}")
    for downloaded in report.files:
        print(f"  ✓ {downloaded.path} ({format_size(downloaded.size)})")
    for skipped in report.skipped:
        print(f"  – {skipped.name}: {skipped.reason}")
    print(
        f"\nConcluído: {len(report.files)} arquivo(s) baixado(s), "
        f"{len(report.skipped)} atividade(s) ignorada(s)."
    )
    return 0


def format_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KiB", "MiB", "GiB"):
        if value < 1024 or unit == "GiB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{size} B"


if __name__ == "__main__":
    raise SystemExit(main())
