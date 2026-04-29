import pdfplumber

_nlp = None

def get_nlp():
    global _nlp
    if _nlp is None:
        try:
            import spacy
            _nlp = spacy.load("en_core_web_sm")
        except Exception as e:
            print(f"Warning: spacy model not available: {e}")
            _nlp = False
    return _nlp if _nlp else None


def load_known_skills(supabase):
    res = supabase.table("skills_graph").select("skill_name").execute()
    return [row["skill_name"].lower() for row in (res.data or []) if row.get("skill_name")]


def extract_text_from_pdf(file_bytes: bytes) -> str:
    import io
    text_data = []
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                text_data.append(page_text)
        text = "\n".join(text_data)
        if text.strip():
            return text
    except Exception as ex:
        print(f"pdfplumber extraction failed: {ex}")

    # Fallback to PyPDF2 if pdfplumber fails or extracts nothing
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(io.BytesIO(file_bytes))
        text_data = []
        for page in reader.pages:
            text_data.append(page.extract_text() or "")
        text = "\n".join(text_data)
        if text.strip():
            return text
    except Exception as ex:
        print(f"PyPDF2 extraction failed: {ex}")

    # Fallback by decoding raw bytes (may not work for non-text PDFs)
    try:
        text = file_bytes.decode('utf-8', errors='ignore')
        if text.strip():
            return text
    except Exception as ex:
        print(f"Raw decode fallback failed: {ex}")

    return ""


def parse_resume(text: str, known_skills: list) -> dict:
    text_lower = text.lower()
    found_skills = [s for s in known_skills if s in text_lower]

    projects = []
    lines = text.split("\n")
    in_projects = False
    for line in lines:
        if "project" in line.lower() and not in_projects:
            in_projects = True
            continue
        if in_projects:
            line_text = line.strip()
            if len(line_text) > 10:
                projects.append(line_text)
            if len(projects) >= 5:
                break

    return {
        "skills": list(dict.fromkeys(found_skills)),
        "projects": projects,
    }
