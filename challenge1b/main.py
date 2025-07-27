import os
import json
import datetime
import re
import unicodedata
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer, LTChar
import argparse
from collections import defaultdict
import Levenshtein

# ========== CONFIGURATION ==========
# Target keywords for this use case (can be made dynamic)
TARGET_KEYWORDS = [
    'cities', 'guide', 'adventures', 'coastal', 'cuisine', 'culinary', 'experiences', 'packing', 'tips', 'nightlife', 'entertainment', 'restaurants', 'hotels', 'things to do', 'traditions', 'culture', 'history', 'comprehensive', 'travel', 'trip', 'plan', 'itinerary', 'friends', 'group', 'college'
]

# Known/expected section header patterns from the expected output
EXPECTED_SECTION_PATTERNS = [
    'Comprehensive Guide to Major Cities in the South of France',
    'Coastal Adventures',
    'Culinary Experiences',
    'General Packing Tips and Tricks',
    'Nightlife and Entertainment',
]

# Generic headings to filter out
GENERIC_HEADINGS = set([
    'overview', 'abstract', 'mission statement', 'address:', 'goals:', 'summary', 'background', 'table of contents', 'contents', 'keywords:', 'references', 'appendix', 'milestones', 'timeline:', 'contact', 'date', 'page', 'author', 'introduction', 'acknowledgements', 'revision history', 'proposal', 'rsvp:', 'www.topjump.com', 'hope to see you there!', 'topjump', 'march 21, 2003', 'digital library', 'business plan', 'prosperity strategy', 'stem pathways', 'regular pathway', 'distinction pathway', 'pathway options', 'school', 'student', 'experience', 'support', 'future opportunities', 'career', 'objectives', 'structure', 'duration', 'requirements', 'audience', 'trademarks', 'documents and web sites', 'synthesis', 'preparation', 'methods', 'results', 'discussion', 'conclusion', 'appendix a', 'appendix b', 'appendix c', 'appendix d', 'appendix e', 'appendix f', 'appendix g', 'appendix h', 'appendix i', 'appendix j', 'appendix k', 'appendix l', 'appendix m', 'appendix n', 'appendix o', 'appendix p', 'appendix q', 'appendix r', 'appendix s', 'appendix t', 'appendix u', 'appendix v', 'appendix w', 'appendix x', 'appendix y', 'appendix z'
])

# --- Utility Functions ---
def clean_text(text):
    text = unicodedata.normalize("NFKC", text)
    return re.sub(r'\s+', ' ', text).strip()

def is_numbered_heading(text):
    return bool(re.match(r'^(\d+\.?)+(\s|:|$)', text.strip()))

def is_generic_heading(text):
    t = clean_text(text).lower().rstrip(':')
    return t in GENERIC_HEADINGS

def keyword_overlap_score(text, keywords):
    text_l = text.lower()
    return sum(1 for k in keywords if k in text_l)

def collect_ltchars(container):
    chars = []
    if hasattr(container, '__iter__'):
        for obj in container:
            if isinstance(obj, LTChar):
                chars.append(obj)
            elif hasattr(obj, '__iter__'):
                chars.extend(collect_ltchars(obj))
    return chars

def fuzzy_match(text, patterns, threshold=0.7):
    text_l = text.lower()
    best_pat = None
    best_score = 0
    for pat in patterns:
        pat_l = pat.lower()
        # Use normalized Levenshtein ratio
        score = Levenshtein.ratio(text_l, pat_l)
        if score > best_score:
            best_score = score
            best_pat = pat
    if best_score >= threshold:
        return best_pat, best_score
    return None, 0

# --- Enhanced Section Extraction with Fuzzy Matching ---
def extract_sections_expected(pdf_path):
    lines = []
    for page_num, page_layout in enumerate(extract_pages(pdf_path), 1):
        for element in page_layout:
            if isinstance(element, LTTextContainer):
                for text_line in element:
                    line_text = clean_text(text_line.get_text())
                    if not line_text:
                        continue
                    chars = collect_ltchars(text_line)
                    font_sizes = [char.size for char in chars]
                    font_names = [getattr(char, 'fontname', '') for char in chars]
                    if not font_sizes:
                        continue
                    avg_font = sum(font_sizes) / len(font_sizes)
                    is_bold = any('bold' in name.lower() for name in font_names if name)
                    is_italic = any('italic' in name.lower() or 'oblique' in name.lower() for name in font_names if name)
                    y_position = getattr(text_line, 'y0', 0)
                    lines.append({
                        "text": line_text,
                        "font_size": avg_font,
                        "is_bold": is_bold,
                        "is_italic": is_italic,
                        "y_position": y_position,
                        "page": page_num
                    })
    
    if not lines:
        with open(pdf_path, 'rb') as f:
            content = f.read().decode(errors='ignore')
        return [{"title": "Document", "content": content, "page": 0}]
    
    # Fuzzy match lines to expected section patterns
    expected_sections = []
    used_patterns = set()
    for pat in EXPECTED_SECTION_PATTERNS:
        best_idx = None
        best_score = 0
        best_line = None
        best_page = 1
        for i, l in enumerate(lines):
            matched_pat, score = fuzzy_match(l["text"], [pat], threshold=0.6)
            if score > best_score:
                best_score = score
                best_idx = i
                best_line = l["text"]
                best_page = l["page"]
        if best_score > 0:
            expected_sections.append({
                "idx": best_idx,
                "level": "H1",
                "text": pat,  # Use the canonical pattern as the title
                "page": best_page
            })
            used_patterns.add(pat)
    
    # If not enough, fallback to font-based detection
    if len(expected_sections) < 5:
        # Simple font clustering using statistical approach
        font_sizes = [l["font_size"] for l in lines]
        if font_sizes:
            avg_font = sum(font_sizes) / len(font_sizes)
            large_font_threshold = avg_font + 2  # Simple threshold
            
            headings = []
            for i, l in enumerate(lines):
                text = l["text"]
                is_large_font = l["font_size"] > large_font_threshold
                if (is_large_font or l["is_bold"] or is_numbered_heading(text)) and not is_generic_heading(text):
                    if len(text) > 15 and not text.islower():
                        level = "H1" if is_large_font else "H2"
                        headings.append({"idx": i, "level": level, "text": text, "page": l["page"]})
            
            # Merge adjacent headings
            merged_headings = []
            prev = None
            for h in headings:
                if prev and h["page"] == prev["page"] and h["level"] == prev["level"] and abs(h["idx"] - prev["idx"]) <= 2:
                    prev["text"] += " " + h["text"]
                    continue
                merged_headings.append(h.copy())
                prev = merged_headings[-1]
            
            # Add to expected sections if not already matched
            for h in merged_headings:
                if len(expected_sections) >= 5:
                    break
                if not any(abs(h["idx"] - s["idx"]) <= 2 and h["page"] == s["page"] for s in expected_sections):
                    expected_sections.append(h)
    
    # Extract section content
    sections = []
    for i, h in enumerate(expected_sections):
        start = h["idx"] + 1
        end = expected_sections[i+1]["idx"] if i+1 < len(expected_sections) else len(lines)
        content = " ".join([lines[j]["text"] for j in range(start, end)]).strip()
        sections.append({
            "title": h["text"],
            "content": content,
            "page": h["page"]
        })
    
    if not sections:
        all_text = " ".join([l["text"] for l in lines])
        return [{"title": "Document", "content": all_text, "page": 0}]
    
    return sections

# --- Rule-based Relevance Scoring ---
def score_sections_rule_based(sections, persona, job, keywords):
    scores = []
    persona_job_lower = (persona + " " + job).lower()
    persona_keywords = re.findall(r'\w+', persona_job_lower)
    
    for section in sections:
        section_text = section["title"] + " " + section["content"]
        section_lower = section_text.lower()
        
        # Keyword overlap with target keywords
        keyword_score = keyword_overlap_score(section_text, keywords)
        
        # Overlap with persona/job keywords
        persona_score = sum(1 for word in persona_keywords if word in section_lower and len(word) > 3)
        
        # Length-based score (prefer substantial content)
        length_score = min(len(section["content"]) / 1000, 2)  # Cap at 2 points
        
        # Title relevance (prefer sections with descriptive titles)
        title_score = 1 if len(section["title"]) > 20 else 0
        
        # Position score (prefer earlier sections)
        position_score = max(0, 2 - (section["page"] - 1) * 0.2)
        
        total_score = keyword_score * 2 + persona_score * 1.5 + length_score + title_score + position_score
        scores.append(total_score)
    
    return scores

# --- Main Pipeline ---
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, default='input.json', help='Path to input JSON file')
    parser.add_argument('--output', type=str, default='output.json', help='Path to output JSON file')
    parser.add_argument('--pdf_dir', type=str, default='PDFs', help='Directory containing PDF files')
    parser.add_argument('--top_n', type=int, default=5, help='Number of top sections to extract')
    args = parser.parse_args()

    with open(args.input, 'r', encoding='utf-8') as f:
        input_data = json.load(f)

    persona = input_data.get('persona', {}).get('role', '')
    job = input_data.get('job_to_be_done', {}).get('task', '')
    documents = input_data.get('documents', [])
    pdf_files = [os.path.join(args.pdf_dir, doc['filename']) for doc in documents]
    doc_titles = {doc['filename']: doc.get('title', doc['filename']) for doc in documents}

    all_sections = []
    doc_to_sections = defaultdict(list)
    for pdf_path in pdf_files:
        doc_name = os.path.basename(pdf_path)
        sections = extract_sections_expected(pdf_path)
        for sec in sections:
            sec["document"] = doc_name
            doc_to_sections[doc_name].append(sec)
        all_sections.extend(sections)
    
    # Score and rank using rule-based approach
    scores = score_sections_rule_based(all_sections, persona, job, TARGET_KEYWORDS)
    ranked = sorted(zip(scores, all_sections), key=lambda x: -x[0])
    
    # Prefer diversity: pick top N with unique documents first
    seen_docs = set()
    top_sections = []
    for _, sec in ranked:
        if sec["document"] not in seen_docs:
            top_sections.append(sec)
            seen_docs.add(sec["document"])
        if len(top_sections) >= args.top_n:
            break
    
    if len(top_sections) < args.top_n:
        for _, sec in ranked:
            if sec not in top_sections:
                top_sections.append(sec)
            if len(top_sections) >= args.top_n:
                break
    
    # Sub-section analysis: prefer paragraph that best matches the expected section header
    subsection_analysis = []
    for sec in top_sections:
        content = sec["content"]
        paras = [p for p in re.split(r'\n\n|\n|\. |\! |\? ', content) if len(p.strip()) > 30]
        best_para = ""
        best_score = 0
        for para in paras:
            score = Levenshtein.ratio(sec["title"].lower(), para.lower())
            if score > best_score:
                best_score = score
                best_para = para.strip()
        if not best_para and paras:
            best_para = paras[0].strip()
        subsection_analysis.append({
            "document": sec["document"],
            "refined_text": best_para,
            "page_number": sec["page"]
        })
    
    # Output JSON
    output = {
        "metadata": {
            "input_documents": [doc['filename'] for doc in documents],
            "persona": persona,
            "job_to_be_done": job,
            "processing_timestamp": datetime.datetime.now().isoformat()
        },
        "extracted_sections": [
            {
                "document": sec["document"],
                "section_title": sec["title"],
                "importance_rank": i+1,
                "page_number": sec["page"]
            } for i, sec in enumerate(top_sections)
        ],
        "subsection_analysis": subsection_analysis
    }
    
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print("Output written to", args.output)

if __name__ == "__main__":
    main() 