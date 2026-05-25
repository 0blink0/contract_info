import json
import sys
from pathlib import Path

import click

from backend.app.config import PROJECT_ROOT
from backend.app.parse import parse_docx
from backend.app.parse.schemas import document_to_dict
from backend.app.services.parse_service import persist_parse


@click.group()
def main() -> None:
    """Contract info extraction CLI."""


@main.command("parse")
@click.argument("docx_path", type=click.Path(exists=True, dir_okay=False))
@click.option("--persist", is_flag=True, help="Save file and parse result to PostgreSQL.")
@click.option("--out", type=click.Path(dir_okay=False), default=None, help="Write JSON to file.")
def parse_cmd(docx_path: str, persist: bool, out: str | None) -> None:
    path = Path(docx_path)
    if persist:
        file_id = persist_parse(str(path))
        click.echo(f"Persisted contract_file id={file_id}")
        return

    document = parse_docx(str(path.resolve()))
    data = document_to_dict(document)
    if out:
        out_path = Path(out)
        out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        click.echo(f"Wrote {out_path}")
    else:
        click.echo(
            f"source={data['source_file']} "
            f"outline={len(data['outline'])} blocks={len(data['blocks'])}"
        )
        preview = json.dumps(
            {
                "outline": data["outline"][:5],
                "metadata": data["metadata"],
            },
            ensure_ascii=False,
            indent=2,
        )
        click.echo(preview)


if __name__ == "__main__":
    main()
