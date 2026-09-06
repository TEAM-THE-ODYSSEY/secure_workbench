from pathlib import Path
import csv
import json

SUPPORTED = {".txt",".md",".json",".csv",".pdf",".docx",".pptx",".xlsx",
             ".png",".jpg",".jpeg",".webp",".bmp",".tif",".tiff"}

def _text(path):
    return path.read_text(encoding="utf-8", errors="replace")

def extract(path):
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(str(p))
    ext = p.suffix.lower()
    if ext not in SUPPORTED:
        raise ValueError(f"Unsupported file type: {ext}")

    if ext == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(str(p))
        text = "\n\n".join(f"[PAGE {i}]\n{page.extract_text() or ''}"
                            for i, page in enumerate(reader.pages, 1))
    elif ext == ".docx":
        from docx import Document
        d = Document(str(p))
        parts = [x.text for x in d.paragraphs if x.text.strip()]
        for table in d.tables:
            parts += [" | ".join(c.text.strip() for c in row.cells)
                      for row in table.rows]
        text = "\n".join(parts)
    elif ext == ".pptx":
        from pptx import Presentation
        prs = Presentation(str(p))
        slides = []
        for i, slide in enumerate(prs.slides, 1):
            parts = [s.text.strip() for s in slide.shapes
                     if hasattr(s, "text") and s.text.strip()]
            slides.append(f"[SLIDE {i}]\n" + "\n".join(parts))
        text = "\n\n".join(slides)
    elif ext == ".xlsx":
        from openpyxl import load_workbook
        wb = load_workbook(p, read_only=True, data_only=True)
        out = []
        for ws in wb.worksheets:
            out.append(f"[SHEET {ws.title}]")
            for row in ws.iter_rows(values_only=True):
                out.append(" | ".join("" if v is None else str(v) for v in row))
        text = "\n".join(out)
    elif ext == ".csv":
        with p.open("r", encoding="utf-8", errors="replace", newline="") as f:
            text = "\n".join(" | ".join(row) for row in csv.reader(f))
    elif ext == ".json":
        try:
            text = json.dumps(json.loads(_text(p)), indent=2)
        except json.JSONDecodeError:
            text = _text(p)
    elif ext in {".png",".jpg",".jpeg",".webp",".bmp",".tif",".tiff"}:
        text = "[IMAGE FILE] Visual understanding must be handled by a configured multimodal model."
    else:
        text = _text(p)

    return {"filename": p.name, "path": str(p.resolve()), "extension": ext, "text": text}
