#backend/workers/sectioning.py
"""
Celery task: split a raw 10-K/10-Q text blob into *true* SEC sections
(Item 1, Item 1A, Item 7, …) and upload a JSONLines artefact.

Output key:
    <uuid>_<filename>.sections.jsonl
JSONL schema (one line per section):
    {"section": "ITEM 1.", "text": "<full body text of that item>", "page_range": [start_page, end_page]}
"""

import re, json, tempfile, boto3
from pathlib import Path
from typing import List, Dict, Tuple
from app.config import settings
from celery_app import celery_app
from celery import signature

# ──────────────────────────────────────────────────────────────
# 1.  Enhanced splitter logic with page tracking
# ──────────────────────────────────────────────────────────────
ITEM_RE = re.compile(r"(ITEM\s+\d+[A-Za-z]?\.)", re.IGNORECASE)

def find_section_pages(page_data: List[Dict], section_title: str) -> Tuple[int, int]:
    """Find the page range for a given section."""
    start_page = None
    end_page = None
    
    for page in page_data:
        page_text = page["text"]
        if section_title in page_text.upper():
            if start_page is None:
                start_page = page["page_num"]
            end_page = page["page_num"]
    
    return start_page or 1, end_page or len(page_data)

def extract_cross_references(text: str) -> List[Dict]:
    """Extract cross-references like 'see Item 1A' or 'refer to Note 8'."""
    patterns = [
        r'see\s+(Item\s+\d+[A-Za-z]?)',
        r'refer\s+to\s+(Item\s+\d+[A-Za-z]?)',
        r'Note\s+(\d+)',
        r'Part\s+[IVX]+\s+Item\s+(\d+[A-Za-z]?)',
        r'Item\s+(\d+[A-Za-z]?)\s+of\s+this\s+Annual\s+Report'
    ]
    
    references = []
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            references.append({
                "source_text": match.group(0),
                "target_section": match.group(1),
                "position": match.start(),
                "context": text[max(0, match.start()-50):match.end()+50]
            })
    return references

def detect_subsections(text: str, item_number: str) -> List[Dict]:
    """
    Detect subsections within an ITEM section using structural cues.
    Returns list of subsections with their titles and content.
    """
    subsections = []
    
    # Common subsection patterns in 10-K filings
    subsection_patterns = [
        # Bold/capitalized headings (simulate bold with caps + punctuation)
        r'\n([A-Z][A-Z\s&,-]{10,80})\n',
        # Numbered subsections
        r'\n(\d+\.\s+[A-Za-z][A-Za-z\s&,-]{5,60})\n',
        # Lettered subsections  
        r'\n([a-z]\.\s+[A-Za-z][A-Za-z\s&,-]{5,60})\n',
        # Common regulatory subsection titles
        r'\n((?:Programs?\s+and\s+)?Incentives?[A-Za-z\s&,-]*)\n',
        r'\n(Tax\s+Credits?[A-Za-z\s&,-]*)\n',
        r'\n(Regulations?[A-Za-z\s&,-]*)\n',
        r'\n(Government\s+Programs?[A-Za-z\s&,-]*)\n',
        r'\n(Environmental[A-Za-z\s&,-]*)\n',
        r'\n(Competition[A-Za-z\s&,-]*)\n',
        r'\n(Employees?[A-Za-z\s&,-]*)\n',
        r'\n(Properties[A-Za-z\s&,-]*)\n',
        r'\n(Legal\s+Proceedings[A-Za-z\s&,-]*)\n',
        r'\n(Risk\s+Factors[A-Za-z\s&,-]*)\n',
        r'\n(Management[A-Za-z\s&,-]*)\n',
        r'\n(Operations[A-Za-z\s&,-]*)\n',
        # Table of contents style headings
        r'\n([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+and\s+[A-Z][a-z]+)*)\s*\.{3,}',
    ]
    
    # Find all potential subsection markers
    markers = []
    for pattern in subsection_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
            title = match.group(1).strip()
            # Clean up title (remove dots, extra spaces)
            title = re.sub(r'\.{3,}.*', '', title).strip()
            title = re.sub(r'\s+', ' ', title)
            
            # Skip very short or very long titles
            if 5 <= len(title) <= 80:
                markers.append({
                    'title': title,
                    'start': match.start(),
                    'end': match.end(),
                    'pattern': pattern
                })
    
    # Sort markers by position and remove duplicates/overlaps
    markers.sort(key=lambda x: x['start'])
    filtered_markers = []
    for marker in markers:
        # Skip if too close to previous marker (likely duplicate)
        if not filtered_markers or marker['start'] - filtered_markers[-1]['start'] > 50:
            filtered_markers.append(marker)
    
    # If no subsections found, return the entire section as one subsection
    if not filtered_markers:
        return [{
            'title': f"{item_number} - Full Content",
            'content': text.strip(),
            'start_pos': 0,
            'end_pos': len(text)
        }]
    
    # Create subsections based on markers
    for i, marker in enumerate(filtered_markers):
        start_pos = marker['start']
        end_pos = filtered_markers[i + 1]['start'] if i + 1 < len(filtered_markers) else len(text)
        
        # Extract content for this subsection
        content = text[start_pos:end_pos].strip()
        
        # Skip very short subsections (likely false positives)
        if len(content) > 100:
            subsections.append({
                'title': marker['title'],
                'content': content,
                'start_pos': start_pos,
                'end_pos': end_pos
            })
    
    return subsections

def split_into_sections_with_pages(page_data: List[Dict]) -> dict[str, Dict]:
    """
    Return enhanced sections with page information, cross-references, and subsections.
    """
    # Combine all text for section detection
    full_text = "\n".join(page["text"] for page in page_data)
    
    matches = list(ITEM_RE.finditer(full_text))
    if not matches:
        return {"FULL_TEXT": {
            "text": full_text,
            "page_range": [1, len(page_data)],
            "cross_references": [],
            "subsections": []
        }}

    sections: dict[str, Dict] = {}
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        title = m.group(1).strip().upper()
        body = full_text[start:end].strip()
        
        # Find page range for this section
        start_page, end_page = find_section_pages(page_data, title)
        
        # Extract cross-references
        cross_refs = extract_cross_references(body)
        
        # Detect subsections within this ITEM
        subsections = detect_subsections(body, title)
        
        sections[title] = {
            "text": body,
            "page_range": [start_page, end_page],
            "cross_references": cross_refs,
            "subsections": subsections
        }
    
    return sections

def split_into_sections(text: str) -> dict[str, str]:
    """
    Legacy function for backward compatibility.
    Return {"ITEM 1.": "...", "ITEM 1A.": "...", ...}.
    """
    matches = list(ITEM_RE.finditer(text))
    if not matches:
        return {"FULL_TEXT": text}

    sections: dict[str, str] = {}
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        title = m.group(1).strip().upper()
        body = text[start:end].strip()
        sections[title] = body
    return sections

# ──────────────────────────────────────────────────────────────
# 2.  S3 / MinIO client
# ──────────────────────────────────────────────────────────────
s3 = boto3.client(
    "s3",
    endpoint_url=settings.s3_endpoint,
    aws_access_key_id=settings.s3_access_key,
    aws_secret_access_key=settings.s3_secret_key,
)

# ──────────────────────────────────────────────────────────────
# 3.  Enhanced Celery task
# ──────────────────────────────────────────────────────────────
@celery_app.task(name="workers.sectioning.split_sections",
                 bind=True, max_retries=3)
def split_sections(self, txt_key: str, filename: str, pages_key: str = None):
    """
    Parameters
    ----------
    txt_key   : key of raw .txt object in processed-filings bucket
    filename  : original filing name (for logging only)
    pages_key : key of page-structured data (optional, for enhanced processing)
    """
    # 1) fetch raw text saved by ingestion
    obj = s3.get_object(Bucket="processed-filings", Key=txt_key)
    raw_text = obj["Body"].read().decode()

    # 2) Enhanced processing if page data is available
    if pages_key:
        try:
            pages_obj = s3.get_object(Bucket="processed-filings", Key=pages_key)
            page_data = json.loads(pages_obj["Body"].read().decode())
            sections = split_into_sections_with_pages(page_data)
            print(f"[SECTION] Enhanced processing with page data for {filename}")
        except Exception as e:
            print(f"[SECTION] Fallback to legacy processing: {e}")
            sections = split_into_sections(raw_text)
    else:
        sections = split_into_sections(raw_text)

    # 3) write JSONL to a temp file
    jsonl_key = txt_key.replace(".txt", ".sections.jsonl")
    with tempfile.NamedTemporaryFile("w", delete=False) as tmp:
        for title, section_data in sections.items():
            if isinstance(section_data, dict):
                # Enhanced format with page info, cross-references, and subsections
                tmp.write(json.dumps({
                    "section": title,
                    "text": section_data["text"],
                    "page_range": section_data["page_range"],
                    "cross_references": section_data["cross_references"],
                    "subsections": section_data.get("subsections", [])
                }) + "\n")
            else:
                # Legacy format for backward compatibility
                tmp.write(json.dumps({"section": title, "text": section_data}) + "\n")
        tmp_path = tmp.name

    # 4) upload to MinIO
    s3.upload_file(tmp_path, "processed-filings", jsonl_key)
    
    # Log cross-reference and subsection summary
    total_refs = sum(len(s.get("cross_references", [])) for s in sections.values() if isinstance(s, dict))
    total_subsections = sum(len(s.get("subsections", [])) for s in sections.values() if isinstance(s, dict))
    print(f"[SECTION] {filename}: {len(sections)} sections, {total_subsections} subsections, {total_refs} cross-references → {jsonl_key}")
    
    signature(
        "workers.embedding.embed_sections",
        kwargs={"sections_key": jsonl_key, "filename": filename},
    ).apply_async()
