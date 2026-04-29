"""
Resume Parser: Extract structured data from resume PDFs.
Uses pdfplumber for text extraction and regex for field parsing.
"""

import re
import os

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False


def extract_text_from_pdf(pdf_path):
    """Extract all text from a PDF file."""
    if not HAS_PDFPLUMBER:
        raise ImportError("pdfplumber is required. Install with: pip install pdfplumber")

    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text


def parse_resume(pdf_path):
    """
    Parse a resume PDF into structured data.
    Returns a dict with extracted fields.
    """
    text = extract_text_from_pdf(pdf_path)
    lines = text.strip().split("\n")

    result = {
        "name": "",
        "department": "",
        "year_of_study": 0,
        "cgpa": 0.0,
        "10th_marks": 0.0,
        "10th_board": "",
        "12th_marks": 0.0,
        "12th_board": "",
        "skills": [],
        "certifications": [],
        "projects": [],
        "internships": [],
        "research_papers": [],
    }

    # Name is typically the first non-empty line
    if lines:
        result["name"] = lines[0].strip()

    # Parse subtitle line (department, year, CGPA)
    for line in lines[:5]:
        dept_match = re.search(r'(CSE|ECE|EEE|MECH|CIVIL|IT|AIDS|AIML|MBA|BCA)', line)
        if dept_match:
            result["department"] = dept_match.group(1)

        year_match = re.search(r'Year\s*(\d)', line)
        if year_match:
            result["year_of_study"] = int(year_match.group(1))

        cgpa_match = re.search(r'CGPA:\s*([\d.]+)', line)
        if cgpa_match:
            result["cgpa"] = float(cgpa_match.group(1))

    # Parse education section
    for line in lines:
        # 10th marks
        if "Class X" in line and "XII" not in line:
            board_match = re.search(r'(CBSE|State|ICSE|Matriculation)', line)
            marks_match = re.search(r'([\d.]+)%', line)
            if board_match:
                result["10th_board"] = board_match.group(1)
            if marks_match:
                result["10th_marks"] = float(marks_match.group(1))

        # 12th marks
        if "Class XII" in line:
            board_match = re.search(r'(CBSE|State|ICSE|HSC)', line)
            marks_match = re.search(r'([\d.]+)%', line)
            if board_match:
                result["12th_board"] = board_match.group(1)
            if marks_match:
                result["12th_marks"] = float(marks_match.group(1))

    # Parse skills
    current_section = ""
    for line in lines:
        line_stripped = line.strip()
        if line_stripped in ("TECHNICAL SKILLS", "SKILLS"):
            current_section = "skills"
            continue
        elif line_stripped in ("CERTIFICATIONS", "CERTIFICATES"):
            current_section = "certs"
            continue
        elif line_stripped in ("PROJECTS",):
            current_section = "projects"
            continue
        elif line_stripped in ("INTERNSHIPS", "EXPERIENCE"):
            current_section = "internships"
            continue
        elif line_stripped in ("RESEARCH PUBLICATIONS", "PAPERS"):
            current_section = "papers"
            continue
        elif line_stripped.isupper() and len(line_stripped) > 3:
            current_section = ""  # New unknown section
            continue

        if current_section == "skills":
            # Parse "Advanced: Python, SQL, ..." format
            skill_match = re.match(r'(Advanced|Intermediate|Beginner):\s*(.+)', line_stripped)
            if skill_match:
                proficiency = skill_match.group(1)
                skill_names = [s.strip() for s in skill_match.group(2).split(",")]
                for sn in skill_names:
                    # Remove verified annotation
                    sn = re.sub(r'\s*\(\d+ verified\)', '', sn).strip()
                    if sn:
                        result["skills"].append({
                            "skill_name": sn,
                            "proficiency": proficiency,
                        })

        elif current_section == "certs":
            cert_match = re.match(r'(.+?)\s*—\s*(.+?)\s*\((\d{4})\)\s*\[(.+?)\]', line_stripped)
            if cert_match:
                result["certifications"].append({
                    "cert_name": cert_match.group(1).strip(),
                    "issuing_body": cert_match.group(2).strip(),
                    "year_obtained": int(cert_match.group(3)),
                    "tier": cert_match.group(4).strip(),
                })

    return result


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        result = parse_resume(pdf_path)
        import json
        print(json.dumps(result, indent=2))
    else:
        print("Usage: python resume_parser.py <path_to_resume.pdf>")
