import json
import sys
from pathlib import Path

import click

from backend.app.config import PROJECT_ROOT
from backend.app.parse import parse_docx
from backend.app.parse.schemas import document_to_dict
from backend.app.services.extract_service import (
    extract_from_docx_path,
    extract_from_file_id,
    persist_extract,
    persist_extract_from_path,
)
from backend.app.services.export_service import export_from_file_id, export_from_json, persist_export
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


@main.command("extract")
@click.argument("docx_path", required=False, type=click.Path(exists=True, dir_okay=False))
@click.option("--file-id", default=None, help="Extract from persisted parse_json by UUID.")
@click.option("--persist", is_flag=True, help="Save extraction to PostgreSQL.")
@click.option("--out", type=click.Path(dir_okay=False), default=None, help="Write JSON to file.")
def extract_cmd(
    docx_path: str | None,
    file_id: str | None,
    persist: bool,
    out: str | None,
) -> None:
    import uuid

    if persist and docx_path and not file_id:
        fid = persist_extract_from_path(docx_path)
        click.echo(f"Persisted extraction id={fid}")
        return

    if file_id:
        result, warnings, path_b = extract_from_file_id(uuid.UUID(file_id))
    elif docx_path:
        result, warnings, path_b = extract_from_docx_path(docx_path)
    else:
        click.echo("Provide docx_path or --file-id", err=True)
        sys.exit(1)

    if persist and file_id:
        persist_extract(uuid.UUID(file_id))
        click.echo(f"Updated extraction for id={file_id}")

    pe = result.get("product_elements") or {}
    fee = result.get("fee_rates") or []
    click.echo(
        f"fields={len(pe)} fee_rows={len(fee)} warnings={len(warnings)} "
        f"path_b_keys={len(path_b) if path_b else 0}"
    )
    if out:
        payload = {"extraction": result, "warnings": warnings, "path_b": path_b}
        Path(out).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        click.echo(f"Wrote {out}")
    else:
        preview = {
            "product_elements": {
                k: v.get("value") if isinstance(v, dict) else v
                for k, v in list(pe.items())[:8]
            },
            "fee_rates": fee[:3],
        }
        click.echo(json.dumps(preview, ensure_ascii=False, indent=2))


@main.command("export")
@click.option("--file-id", default=None, help="Export from DB extraction_result.")
@click.option("--from-json", "from_json", default=None, type=click.Path(exists=True, dir_okay=False))
@click.option("--persist", is_flag=True, help="Save paths and status to PostgreSQL.")
def export_cmd(file_id: str | None, from_json: str | None, persist: bool) -> None:
    import uuid

    warnings: list = []
    if from_json:
        fid = uuid.UUID(file_id) if file_id else uuid.uuid4()
        product_path, fee_path, lock_path, share_path, subscription_path, warnings = (
            export_from_json(from_json, fid)
        )
    elif file_id:
        if persist:
            product_path, fee_path, lock_path, share_path, subscription_path = (
                persist_export(uuid.UUID(file_id))
            )
            click.echo(f"product={product_path}")
            click.echo(f"fee={fee_path}")
            click.echo(f"lock={lock_path}")
            click.echo(f"share={share_path}")
            click.echo(f"subscription={subscription_path}")
            return
        product_path, fee_path, lock_path, share_path, subscription_path, warnings = (
            export_from_file_id(uuid.UUID(file_id))
        )
    else:
        click.echo("Provide --file-id or --from-json", err=True)
        sys.exit(1)

    click.echo(f"product={product_path}")
    click.echo(f"fee={fee_path}")
    click.echo(f"lock={lock_path}")
    click.echo(f"share={share_path}")
    click.echo(f"subscription={subscription_path}")
    click.echo(f"warnings={len(warnings)}")


if __name__ == "__main__":
    main()
