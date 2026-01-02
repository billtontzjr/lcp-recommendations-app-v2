"""
Causation Parser - Parses user's uploaded causation analysis document.

The user performs causation analysis externally (using a Claude project with
Dr. Tontz's built-in methodology). This parser reads that analysis document
and extracts the causation determinations.

Output structure:
{
    "causal_body_parts": [
        {
            "body_part": "Cervical Spine",
            "diagnoses": ["C5-6 disc herniation", "cervical radiculopathy"],
            "classification": "causal",
            "notes": "New onset post-MVA, meets Freeman criteria"
        }
    ],
    "excluded_body_parts": [
        {
            "body_part": "Right Knee",
            "reason": "Pre-existing condition without aggravation",
            "classification": "not_causal"
        }
    ],
    "aggravations": [
        {
            "body_part": "Lumbar Spine",
            "diagnoses": ["L4-5 stenosis"],
            "pre_existing_notes": "Documented on 2019 MRI",
            "aggravation_evidence": "Required ESI series post-accident (none in prior 3 years)"
        }
    ]
}
"""

import re
import os
from docx import Document
import fitz  # PyMuPDF for PDF parsing


def parse_causation_document(file_path: str) -> dict:
    """
    Parse a causation analysis document (DOCX or PDF).

    Args:
        file_path: Path to the uploaded causation analysis document

    Returns:
        Dictionary containing parsed causation data
    """
    ext = os.path.splitext(file_path)[1].lower()

    if ext == '.docx':
        text = extract_text_from_docx(file_path)
    elif ext == '.pdf':
        text = extract_text_from_pdf(file_path)
    else:
        raise ValueError(f"Unsupported file format: {ext}. Please upload .docx or .pdf")

    return parse_causation_text(text)


def extract_text_from_docx(file_path: str) -> str:
    """Extract text from a DOCX file."""
    doc = Document(file_path)
    paragraphs = []
    for para in doc.paragraphs:
        paragraphs.append(para.text)
    return '\n'.join(paragraphs)


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from a PDF file."""
    doc = fitz.open(file_path)
    text_parts = []
    for page in doc:
        text_parts.append(page.get_text())
    doc.close()
    return '\n'.join(text_parts)


def parse_causation_text(text: str) -> dict:
    """
    Parse the causation analysis text and extract structured data.

    The parser looks for:
    1. Body parts/diagnoses marked as causally related
    2. Body parts/diagnoses marked as NOT causally related
    3. Classification details (causal, aggravation, exacerbation, etc.)
    """
    result = {
        "causal_body_parts": [],
        "excluded_body_parts": [],
        "aggravations": [],
        "raw_text": text,  # Keep raw text for AI to use if structured parsing fails
        "parse_confidence": "high"
    }

    text_lower = text.lower()

    # Common body parts to look for
    body_parts = [
        "cervical spine", "thoracic spine", "lumbar spine", "thoracolumbar spine",
        "cervical", "thoracic", "lumbar",
        "right shoulder", "left shoulder", "shoulder",
        "right elbow", "left elbow", "elbow",
        "right wrist", "left wrist", "wrist",
        "right hip", "left hip", "hip",
        "right knee", "left knee", "knee",
        "right ankle", "left ankle", "ankle",
        "right foot", "left foot", "foot"
    ]

    # LOOK FOR EXPLICIT EXCLUSION SECTIONS ONLY
    # These are section headers that explicitly list excluded conditions
    exclusion_section_patterns = [
        r'(?:conditions?\s+)?(?:not\s+included|excluded)(?:\s+(?:in|from))?\s+(?:causation|lcp|opinion)',
        r'(?:conditions?\s+)?excluded\s+from\s+causation',
        r'unable\s+to\s+render\s+(?:an?\s+)?opinion',
        r'excluded\s+from\s+(?:this\s+)?(?:causation\s+)?opinion',
    ]

    # Find exclusion section
    exclusion_section_start = -1
    for pattern in exclusion_section_patterns:
        match = re.search(pattern, text_lower)
        if match:
            exclusion_section_start = match.start()
            break

    # If we found an exclusion section, look for body parts within it
    if exclusion_section_start >= 0:
        # Get text from exclusion section to end (or next major section)
        exclusion_text = text_lower[exclusion_section_start:]
        # Limit to reasonable section size (next 2000 chars or until SUMMARY/METHODS)
        next_section = re.search(r'\n(?:summary|methods|bibliography|conclusion)', exclusion_text[100:])
        if next_section:
            exclusion_text = exclusion_text[:100 + next_section.start()]
        else:
            exclusion_text = exclusion_text[:2000]

        # Find body parts mentioned in the exclusion section
        for bp in body_parts:
            if bp.lower() in exclusion_text:
                normalized_bp = normalize_body_part(bp)
                if not any(e.get("body_part") == normalized_bp for e in result["excluded_body_parts"]):
                    result["excluded_body_parts"].append({
                        "body_part": normalized_bp,
                        "classification": "not_causal",
                        "reason": "Listed in 'Conditions Excluded from Causation Opinion' section",
                        "section_context": exclusion_text[:500]
                    })

    # Also look for explicit "unable to render opinion" statements
    unable_patterns = [
        r'unable\s+to\s+render\s+(?:an?\s+)?(?:causation\s+)?opinion[^.]*?(right|left)?\s*(knee|shoulder|hip|elbow|wrist|ankle|foot)',
        r'(right|left)?\s*(knee|shoulder|hip|elbow|wrist|ankle|foot)[^.]*unable\s+to\s+render',
    ]

    for pattern in unable_patterns:
        matches = re.finditer(pattern, text_lower)
        for match in matches:
            matched_text = match.group(0)
            for bp in body_parts:
                if bp.lower() in matched_text:
                    normalized_bp = normalize_body_part(bp)
                    if not any(e.get("body_part") == normalized_bp for e in result["excluded_body_parts"]):
                        result["excluded_body_parts"].append({
                            "body_part": normalized_bp,
                            "classification": "not_causal",
                            "reason": "Unable to render causation opinion per analysis",
                            "section_context": matched_text[:200]
                        })

    # LOOK FOR CAUSAL SECTIONS - "causally related" or "new traumatic conditions"
    causal_section_patterns = [
        r'(?:causally\s+related|new\s+traumatic\s+conditions?|permanent\s+aggravations?)',
        r'summary\s+of\s+causation\s+opinions?',
    ]

    for pattern in causal_section_patterns:
        match = re.search(pattern, text_lower)
        if match:
            # Get surrounding context
            start = max(0, match.start() - 100)
            end = min(len(text_lower), match.end() + 1500)
            causal_text = text_lower[start:end]

            # Find body parts mentioned in causal context
            for bp in body_parts:
                bp_lower = bp.lower()
                if bp_lower in causal_text:
                    # Make sure this body part isn't in the exclusion list
                    normalized_bp = normalize_body_part(bp)
                    is_excluded = any(e.get("body_part") == normalized_bp for e in result["excluded_body_parts"])
                    already_causal = any(e.get("body_part") == normalized_bp for e in result["causal_body_parts"])

                    if not is_excluded and not already_causal:
                        result["causal_body_parts"].append({
                            "body_part": normalized_bp,
                            "classification": "causal",
                            "diagnoses": [],
                            "section_context": causal_text[:500]
                        })

    # If we found nothing, mark as low confidence and let AI handle it
    if not result["causal_body_parts"] and not result["excluded_body_parts"]:
        result["parse_confidence"] = "low"

    # Deduplicate entries
    result["causal_body_parts"] = deduplicate_entries(result["causal_body_parts"])
    result["excluded_body_parts"] = deduplicate_entries(result["excluded_body_parts"])

    return result


def split_into_sections(text: str) -> dict:
    """Split document into sections based on headers."""
    sections = {}

    # Common section patterns
    header_patterns = [
        r'(?:^|\n)(#{1,3}\s+.+?)(?=\n)',  # Markdown headers
        r'(?:^|\n)([A-Z][A-Za-z\s]+:)',    # SECTION NAME:
        r'(?:^|\n)(\d+\.\s*[A-Z][A-Za-z\s]+)',  # 1. Section Name
        r'(?:^|\n)((?:Cervical|Thoracic|Lumbar|Thoracolumbar)\s*Spine)',  # Body part sections
        r'(?:^|\n)((?:Right|Left)?\s*(?:Shoulder|Elbow|Wrist|Hip|Knee|Ankle|Foot))',  # Joint sections
    ]

    # Find all section headers
    all_matches = []
    for pattern in header_patterns:
        matches = list(re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE))
        all_matches.extend([(m.start(), m.group(1).strip()) for m in matches])

    # Sort by position
    all_matches.sort(key=lambda x: x[0])

    # Extract text between headers
    for i, (pos, title) in enumerate(all_matches):
        end_pos = all_matches[i + 1][0] if i + 1 < len(all_matches) else len(text)
        section_text = text[pos:end_pos]
        sections[title] = section_text

    # If no sections found, treat whole document as one section
    if not sections:
        sections["full_document"] = text

    return sections


def normalize_body_part(body_part: str) -> str:
    """Normalize body part names."""
    bp_lower = body_part.lower().strip()

    mappings = {
        "cervical": "Cervical Spine",
        "cervical spine": "Cervical Spine",
        "thoracic": "Thoracic Spine",
        "thoracic spine": "Thoracic Spine",
        "lumbar": "Lumbar Spine",
        "lumbar spine": "Lumbar Spine",
        "thoracolumbar": "Thoracolumbar Spine",
        "thoracolumbar spine": "Thoracolumbar Spine",
        "shoulder": "Shoulder",
        "right shoulder": "Right Shoulder",
        "left shoulder": "Left Shoulder",
        "elbow": "Elbow",
        "right elbow": "Right Elbow",
        "left elbow": "Left Elbow",
        "wrist": "Wrist",
        "right wrist": "Right Wrist",
        "left wrist": "Left Wrist",
        "hip": "Hip",
        "right hip": "Right Hip",
        "left hip": "Left Hip",
        "knee": "Knee",
        "right knee": "Right Knee",
        "left knee": "Left Knee",
        "ankle": "Ankle",
        "right ankle": "Right Ankle",
        "left ankle": "Left Ankle",
        "foot": "Foot",
        "right foot": "Right Foot",
        "left foot": "Left Foot",
    }

    return mappings.get(bp_lower, body_part.title())


def extract_diagnoses_for_body_part(text: str, body_part: str) -> list:
    """Extract specific diagnoses mentioned for a body part."""
    diagnoses = []

    # Common diagnosis patterns
    diagnosis_patterns = [
        # Disc conditions
        r'(?:C\d-\d|L\d-\d|T\d-\d)\s*(?:disc|disk)?\s*(?:herniation|bulge|protrusion|extrusion)',
        r'(?:disc|disk)\s*(?:herniation|bulge|protrusion|extrusion)\s*(?:at)?\s*(?:C\d-\d|L\d-\d)',
        r'herniated\s*(?:disc|disk)',
        # Radiculopathy
        r'(?:cervical|lumbar|thoracic)?\s*radiculopathy',
        # Stenosis
        r'(?:spinal|foraminal|central)?\s*stenosis',
        # Facet
        r'facet\s*(?:syndrome|arthropathy|disease)',
        # Labral
        r'(?:SLAP|labral)\s*(?:tear|lesion)',
        # Rotator cuff
        r'rotator\s*cuff\s*(?:tear|tendinopathy|tendinitis)',
        # Meniscal
        r'meniscal?\s*(?:tear|injury)',
        r'(?:medial|lateral)\s*meniscus\s*tear',
        # Fractures
        r'(?:compression|vertebral)?\s*fracture',
        # Sprains/strains
        r'(?:sprain|strain)',
        # Myelopathy
        r'myelopathy',
        # Spondylolisthesis
        r'spondylolisthesis',
    ]

    for pattern in diagnosis_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            if isinstance(match, str) and match.strip():
                diagnoses.append(match.strip())

    return list(set(diagnoses))  # Remove duplicates


def extract_exclusion_reason(text: str, body_part: str) -> str:
    """Extract the reason for exclusion."""
    text_lower = text.lower()

    if "pre-existing" in text_lower or "preexisting" in text_lower:
        return "Pre-existing condition without aggravation"
    if "exacerbation" in text_lower:
        return "Temporary exacerbation - expected to return to baseline"
    if "sprain" in text_lower or "strain" in text_lower:
        return "Sprain/strain - self-limited injury"
    if "temporal" in text_lower and "not" in text_lower:
        return "Does not meet temporal relationship criteria"
    if "alternative" in text_lower or "unrelated" in text_lower:
        return "Alternative explanation more likely"

    return "Does not meet causation criteria"


def extract_pre_existing_notes(text: str) -> str:
    """Extract notes about pre-existing condition."""
    # Look for patterns indicating pre-existing history
    patterns = [
        r'(?:pre-existing|preexisting|prior)\s+.{0,100}',
        r'documented\s+(?:on|in)\s+\d{4}',
        r'history\s+of\s+.{0,50}',
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0)[:200]  # Limit to 200 chars

    return ""


def fallback_parse(text: str, result: dict) -> dict:
    """
    Fallback parsing when structured approach fails.
    Look for summary sections or conclusion statements.
    """
    text_lower = text.lower()

    # Look for explicit causation statements
    causal_matches = re.findall(
        r'(?:causally\s+related|causal\s+relationship)[\s:]+([^.]+)',
        text, re.IGNORECASE
    )

    for match in causal_matches:
        result["causal_body_parts"].append({
            "body_part": "See context",
            "diagnoses": [],
            "classification": "causal",
            "section_context": match
        })

    # Look for exclusion statements
    excluded_matches = re.findall(
        r'(?:not\s+causally\s+related|excluded|no\s+causal\s+relationship)[\s:]+([^.]+)',
        text, re.IGNORECASE
    )

    for match in excluded_matches:
        result["excluded_body_parts"].append({
            "body_part": "See context",
            "classification": "not_causal",
            "reason": match
        })

    return result


def deduplicate_entries(entries: list) -> list:
    """Remove duplicate entries based on body part."""
    seen = set()
    unique = []
    for entry in entries:
        bp = entry.get("body_part", "").lower()
        if bp not in seen:
            seen.add(bp)
            unique.append(entry)
    return unique


def get_causal_body_parts(causation_data: dict) -> list:
    """Get list of body parts that are causally related."""
    causal = []
    for entry in causation_data.get("causal_body_parts", []):
        bp = entry.get("body_part", "")
        if bp and bp not in causal:
            causal.append(bp)
    return causal


def get_excluded_body_parts(causation_data: dict) -> list:
    """Get list of body parts that are excluded."""
    excluded = []
    for entry in causation_data.get("excluded_body_parts", []):
        bp = entry.get("body_part", "")
        if bp and bp not in excluded:
            excluded.append(bp)
    return excluded


def is_body_part_causal(causation_data: dict, body_part: str) -> bool:
    """Check if a specific body part is causally related."""
    bp_lower = body_part.lower()

    # Check against causal body parts
    for entry in causation_data.get("causal_body_parts", []):
        entry_bp = entry.get("body_part", "").lower()
        if bp_lower in entry_bp or entry_bp in bp_lower:
            return True

    # Also check if it's in the excluded list (return False)
    for entry in causation_data.get("excluded_body_parts", []):
        entry_bp = entry.get("body_part", "").lower()
        if bp_lower in entry_bp or entry_bp in bp_lower:
            return False

    # If not explicitly mentioned either way, default to checking raw text
    return None  # Ambiguous


def get_causation_summary(causation_data: dict) -> str:
    """Generate a summary of causation findings for the AI prompt."""
    summary_parts = []

    causal = get_causal_body_parts(causation_data)
    excluded = get_excluded_body_parts(causation_data)

    if causal:
        summary_parts.append(f"CAUSALLY RELATED (include in LCP): {', '.join(causal)}")

    if excluded:
        excluded_with_reasons = []
        for entry in causation_data.get("excluded_body_parts", []):
            bp = entry.get("body_part", "")
            reason = entry.get("reason", "excluded")
            excluded_with_reasons.append(f"{bp} ({reason})")
        summary_parts.append(f"NOT CAUSALLY RELATED (exclude from LCP): {'; '.join(excluded_with_reasons)}")

    for entry in causation_data.get("aggravations", []):
        bp = entry.get("body_part", "")
        pre = entry.get("pre_existing_notes", "")
        summary_parts.append(f"AGGRAVATION: {bp} - {pre}")

    if causation_data.get("parse_confidence") == "low":
        summary_parts.append("\nNOTE: Low confidence in structured parsing. Raw causation text provided below.")
        summary_parts.append(f"\nRAW CAUSATION TEXT:\n{causation_data.get('raw_text', '')[:2000]}")

    return '\n'.join(summary_parts)
