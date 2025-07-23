import os
import json
import argparse
from datetime import datetime
from collections import Counter
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer, LTChar
import re
import nltk

# Download stopwords if not present
try:
    from nltk.corpus import stopwords
    STOPWORDS = set(stopwords.words('english'))
except LookupError:
    nltk.download('stopwords')
    from nltk.corpus import stopwords
    STOPWORDS = set(stopwords.words('english'))

def preprocess(text):
    # More aggressive tokenization
    tokens = [w.lower() for w in re.findall(r'\b\w+\b', text)]
    tokens = [w for w in tokens if w not in STOPWORDS and len(w) > 2]
    return set(tokens)

def extract_keywords(persona, job):
    persona_kw = preprocess(persona)
    job_kw = preprocess(job)
    return persona_kw.union(job_kw)

def match_score(section_text, keywords):
    # Improved scoring system
    tokens = preprocess(section_text)
    base_score = len(tokens & keywords)  # intersection
    # Bonus points for title-like words
    bonus_words = {'guide', 'cuisine', 'food', 'restaurant', 'recipe', 'traditional', 'local'}
    bonus_score = len(tokens & bonus_words)
    return base_score + (bonus_score * 2)  # Weight bonus words more heavily

def collect_ltchars(container):
    chars = []
    if hasattr(container, '__iter__'):
        for obj in container:
            if isinstance(obj, LTChar):
                chars.append(obj)
            elif hasattr(obj, '__iter__'):
                chars.extend(collect_ltchars(obj))
    return chars

def analyze_font_characteristics(pdf_path):
    font_data = []
    for page_layout in extract_pages(pdf_path):
        for element in page_layout:
            if isinstance(element, LTTextContainer):
                for text_line in element:
                    line_text = text_line.get_text().strip()
                    if not line_text or len(line_text) < 3:
                        continue
                    font_sizes = []
                    font_names = []
                    for char in getattr(text_line, 'objs', []):
                        if isinstance(char, LTChar):
                            font_sizes.append(char.size)
                            font_names.append(char.fontname if hasattr(char, 'fontname') else '')
                    is_italic = any('italic' in name.lower() or 'oblique' in name.lower() for name in font_names if name)
                    whitespace_above = None
                    if hasattr(text_line, 'y0') and hasattr(text_line, 'y1'):
                        whitespace_above = text_line.y0
                    if font_sizes:
                        avg_font = sum(font_sizes) / len(font_sizes)
                        is_bold = any('bold' in name.lower() for name in font_names if name)
                        font_data.append({
                            'text': line_text,
                            'font_size': avg_font,
                            'is_bold': is_bold,
                            'is_italic': is_italic,
                            'length': len(line_text),
                            'y_position': getattr(text_line, 'y0', 0),
                            'whitespace_above': whitespace_above
                        })
    return font_data

def determine_heading_thresholds(font_data):
    heading_candidates = [
        item for item in font_data 
        if item['length'] <= 100 and item['font_size'] >= 10
    ]
    if not heading_candidates:
        return {'h1': 16, 'h2': 14, 'h3': 12, 'body': 10}
    font_sizes = [item['font_size'] for item in heading_candidates]
    unique_sizes = sorted(set(font_sizes), reverse=True)
    if len(unique_sizes) >= 3:
        h1_threshold = unique_sizes[0]
        h2_threshold = unique_sizes[1] 
        h3_threshold = unique_sizes[2]
    elif len(unique_sizes) == 2:
        h1_threshold = unique_sizes[0]
        h2_threshold = unique_sizes[1]
        h3_threshold = unique_sizes[1] - 1
    else:
        largest_size = max(font_sizes) if font_sizes else 14
        h1_threshold = largest_size
        h2_threshold = largest_size - 2
        h3_threshold = largest_size - 4
    all_sizes = [item['font_size'] for item in font_data]
    body_threshold = min(all_sizes) if all_sizes else 10
    return {
        'h1': h1_threshold,
        'h2': h2_threshold, 
        'h3': h3_threshold,
        'body': body_threshold
    }

def heading_level_from_numbering(text):
    text = text.strip()
    if re.match(r'^\d+([\s\.]|$)', text):
        return 'H2'
    if re.match(r'^\d+\.\d+([\s\.]|$)', text):
        return 'H3'
    if re.match(r'^\d+\.\d+\.\d+([\s\.]|$)', text):
        return 'H4'
    return None

def is_likely_heading(text, font_size, is_bold, is_italic, whitespace_above, y_position, thresholds, page_height=800):
    text = text.strip()
    if len(text) < 2 or len(text) > 150:
        return False, None
    skip_patterns = [
        r'^\d+$', r'^page \d+', r'^\d{1,3}\.?\d*$', r'^[ivxlcdm]+\.?$', r'^[a-z]\.$', r'\.{3,}', r'^©', r'^\s*\d+\s*$'
    ]
    for pattern in skip_patterns:
        if re.match(pattern, text.lower()):
            return False, None
    level_font = None
    if font_size >= thresholds['h1'] - 0.5:
        level_font = "H1"
    elif font_size >= thresholds['h2'] - 0.5:
        level_font = "H2" 
    elif font_size >= thresholds['h3'] - 0.5:
        level_font = "H3"
    level_pattern = heading_level_from_numbering(text)
    level = level_font
    if level_pattern:
        if level_font == 'H1' and level_pattern in ['H2', 'H3', 'H4']:
            level = level_pattern
        elif level_font == 'H2' and level_pattern in ['H3', 'H4']:
            level = level_pattern
        elif level_font == 'H3' and level_pattern == 'H4':
            level = level_pattern
    score = 0
    if level:
        score += 3
    if is_bold:
        score += 2
    if is_italic:
        score += 1
    if text[0].isupper():
        score += 1
    if not text.endswith('.'):
        score += 1
    if len(text.split()) <= 8:
        score += 1
    if whitespace_above is not None and whitespace_above > page_height * 0.7:
        score += 1
    if y_position > page_height * 0.8:
        score += 1
    return score >= 3, level

def clean_heading_text(text):
    return re.sub(r'\s+', ' ', text).strip()

def extract_outline_and_sections(pdf_path):
    font_data = analyze_font_characteristics(pdf_path)
    thresholds = determine_heading_thresholds(font_data)
    outline = []
    headings = []
    sections = []
    section_map = []
    current_section = None
    current_section_text = []
    current_section_page = 1
    page_texts = {}
    for page_num, page_layout in enumerate(extract_pages(pdf_path), 1):
        page_height = page_layout.height
        prev_y = None
        page_lines = []
        for element in page_layout:
            if isinstance(element, LTTextContainer):
                for text_line in element:
                    line_text = text_line.get_text().strip()
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
                    whitespace_above = None
                    if prev_y is not None:
                        whitespace_above = y_position - prev_y
                    prev_y = y_position
                    is_heading, level = is_likely_heading(
                        line_text, avg_font, is_bold, is_italic, whitespace_above, y_position, thresholds, page_height
                    )
                    if is_heading and level:
                        heading_entry = {
                            "level": level,
                            "text": line_text,
                            "page": page_num,
                        }
                        headings.append(heading_entry)
                        # Save previous section
                        if current_section:
                            sections.append({
                                "section_title": current_section,
                                "page": current_section_page,
                                "section_text": " ".join(current_section_text)
                            })
                        current_section = line_text
                        current_section_text = []
                        current_section_page = page_num
                    else:
                        current_section_text.append(line_text)
                    page_lines.append(line_text)
        page_texts[page_num] = "\n".join(page_lines)
    # Save last section
    if current_section:
        sections.append({
            "section_title": current_section,
            "page": current_section_page,
            "section_text": " ".join(current_section_text)
        })
    # Clean headings for outline
    outline = [
        {"level": h["level"], "text": clean_heading_text(h["text"]), "page": h["page"]}
        for h in headings
    ]
    return outline, sections

def analyze_subsections(section_text, keywords, parent_section, doc_name, page):
    subsections = []
    # Split into meaningful chunks
    paras = [p.strip() for p in section_text.split('\n') if len(p.strip()) > 30]
    
    for para in paras:
        score = match_score(para, keywords)
        if score > 0:
            subsections.append({
                "document": doc_name,
                "refined_text": para[:200] + "..." if len(para) > 200 else para,  # Limit length
                "page_number": page,
                "score": score
            })
    return subsections

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_dir', type=str, default='input')
    parser.add_argument('--persona', type=str, required=True)
    parser.add_argument('--job', type=str, required=True)
    parser.add_argument('--output', type=str, default='output.json')
    args = parser.parse_args()

    input_dir = args.input_dir
    persona = args.persona
    job = args.job
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, args.output)

    keywords = extract_keywords(persona, job)
    # Add domain-specific keywords
    if 'food' in persona.lower() or 'culinary' in job.lower():
        keywords.update({'cuisine', 'food', 'restaurant', 'dish', 'recipe', 'traditional'})
    
    all_sections = []
    all_subsections = []
    doc_names = []

    for filename in os.listdir(input_dir):
        if not filename.lower().endswith('.pdf'):
            continue
        pdf_path = os.path.join(input_dir, filename)
        doc_names.append(filename)
        outline, sections = extract_outline_and_sections(pdf_path)
        for sec in sections:
            score = match_score(sec['section_text'], keywords)
            sec_entry = {
                "document": filename,
                "section_title": sec['section_title'],
                "page": sec['page'],
                "section_text": sec['section_text'],
                "score": score
            }
            all_sections.append(sec_entry)
            subs = analyze_subsections(sec['section_text'], keywords, sec['section_title'], filename, sec['page'])
            all_subsections.extend(subs)

    ranked_sections = sorted(all_sections, key=lambda x: x['score'], reverse=True)
    ranked_subsections = sorted(all_subsections, key=lambda x: x['score'], reverse=True)

    for i, sec in enumerate(ranked_sections, 1):
        sec['importance_rank'] = i
    for i, sub in enumerate(ranked_subsections, 1):
        sub['importance_rank'] = i

    output = {
        "metadata": {
            "input_documents": doc_names,
            "persona": persona,
            "job_to_be_done": job,
            "processing_timestamp": datetime.now().isoformat()
        },
        "extracted_sections": [
            {
                "document": sec["document"],
                "page_number": sec["page"],
                "section_title": sec["section_title"],
                "importance_rank": sec["importance_rank"]
            }
            for sec in ranked_sections if sec['score'] > 0  # Changed from > 2
        ],
        "subsection_analysis": [
            {
                "document": sub["document"],
                "refined_text": sub["subsection_text"],
                "page_number": sub["page"]
            }
            for sub in ranked_subsections if sub['score'] > 0  # Changed from > 2
        ]
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Done! Output written to {output_file}")

if __name__ == "__main__":
    main()