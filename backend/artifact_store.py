from __future__ import annotations
import io
import json
import os
import sqlite3
import zipfile
from pathlib import Path
from typing import Optional

DB_PATH = Path(
    os.getenv(
        "TASK_STORE_DB_PATH",
        Path(__file__).resolve().parent / "workspace" / "tasks.db",
    )
)

ARTIFACTS_DIR = Path(
    os.getenv(
        "ARTIFACTS_DIR",
        Path(__file__).resolve().parent / "workspace" / "artifacts",
    )
)

INDEX_JSON_PATH = ARTIFACTS_DIR / "index.json"


def _make_minimal_xlsx() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            "</Types>",
        )
        z.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            "</Relationships>",
        )
        z.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets>'
            "</workbook>",
        )
        z.writestr(
            "xl/_rels/workbook.xml.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            "</Relationships>",
        )
        z.writestr(
            "xl/worksheets/sheet1.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            "<sheetData>"
            '<row r="1">'
            '<c r="A1" t="inlineStr"><is><t>Item</t></is></c>'
            '<c r="B1" t="inlineStr"><is><t>Amount</t></is></c>'
            "</row>"
            '<row r="2">'
            '<c r="A2" t="inlineStr"><is><t>Operational Expenses</t></is></c>'
            "<c r=\"B2\"><v>125000</v></c>"
            "</row>"
            "</sheetData>"
            "</worksheet>",
        )
    return buf.getvalue()


def _make_minimal_docx() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            "</Types>",
        )
        z.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            "</Relationships>",
        )
        z.writestr(
            "word/document.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            "<w:body><w:p><w:r><w:t>Standard Operating Procedure Document Template</w:t></w:r></w:p></w:body>"
            "</w:document>",
        )
    return buf.getvalue()


def _sync_index_json(records: list[dict]) -> None:
    try:
        ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        INDEX_JSON_PATH.write_text(json.dumps(records, indent=2), encoding="utf-8")
    except Exception:
        pass


def _get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS artifacts (
            artifact_id TEXT PRIMARY KEY,
            file_name TEXT NOT NULL,
            file_type TEXT NOT NULL,
            file_path TEXT NOT NULL
        )
        """
    )
    # Seed default artifacts if empty
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM artifacts")
    count = cursor.fetchone()[0]
    if count == 0:
        _seed_default_artifacts(conn)
    return conn


def _seed_default_artifacts(conn: sqlite3.Connection) -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    seeds = [
        (
            "art-sample-txt",
            "sample_notes.txt",
            "txt",
            "System verification and integration test notes.\nAll local airgapped services operational.\n".encode("utf-8"),
        ),
        (
            "art-sample-xlsx",
            "financial_analysis.xlsx",
            "xlsx",
            _make_minimal_xlsx(),
        ),
        (
            "art-doc-001",
            "deviation_report.pdf",
            "pdf",
            b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000010 00000 n \n0000000060 00000 n \n0000000117 00000 n \ntrailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n190\n%%EOF\n",
        ),
        (
            "art-sample-csv",
            "metrics_summary.csv",
            "csv",
            b"metric,value,unit\nlatency,42,ms\nthroughput,1500,rps\naccuracy,99.4,percent\n",
        ),
        (
            "art-sample-docx",
            "sop_template.docx",
            "docx",
            _make_minimal_docx(),
        ),
    ]

    records = []
    for art_id, file_name, file_type, file_content in seeds:
        file_path = ARTIFACTS_DIR / file_name
        file_path.write_bytes(file_content)
        conn.execute(
            """
            INSERT INTO artifacts (artifact_id, file_name, file_type, file_path)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(artifact_id) DO UPDATE SET
                file_name = excluded.file_name,
                file_type = excluded.file_type,
                file_path = excluded.file_path
            """,
            (art_id, file_name, file_type, str(file_path)),
        )
        records.append({
            "artifact_id": art_id,
            "file_name": file_name,
            "file_type": file_type,
            "file_path": str(file_path),
        })

    conn.commit()
    _sync_index_json(records)


def get_artifact(artifact_id: str) -> Optional[dict]:
    """Look up an artifact by artifact_id in the server-side lookup table."""
    conn = _get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT artifact_id, file_name, file_type, file_path FROM artifacts WHERE artifact_id = ?",
            (artifact_id,),
        )
        row = cursor.fetchone()
        if row:
            return {
                "artifact_id": row[0],
                "file_name": row[1],
                "file_type": row[2],
                "file_path": row[3],
            }
        return None
    finally:
        conn.close()


def register_artifact(
    artifact_id: str,
    file_name: str,
    file_type: str,
    file_path: str,
) -> None:
    """Register a new artifact in the server-side lookup table."""
    conn = _get_connection()
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO artifacts (artifact_id, file_name, file_type, file_path)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(artifact_id) DO UPDATE SET
                    file_name = excluded.file_name,
                    file_type = excluded.file_type,
                    file_path = excluded.file_path
                """,
                (artifact_id, file_name, file_type, file_path),
            )
        cursor = conn.cursor()
        cursor.execute("SELECT artifact_id, file_name, file_type, file_path FROM artifacts")
        rows = cursor.fetchall()
        records = [
            {"artifact_id": r[0], "file_name": r[1], "file_type": r[2], "file_path": r[3]}
            for r in rows
        ]
        _sync_index_json(records)
    finally:
        conn.close()
