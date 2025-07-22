import os
import json
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer, LTChar, LTTextBox
import re
from collections import Counter

input_dir = 'input'
output_dir = 'output'

# Helper function to recursively collect all LTChar objects from a container
from pdfminer.layout import LTChar, LTTextContainer

def collect_ltchars(container):
    chars = []
    if hasattr(container, '__iter__'):
        for obj in container:
            if isinstance(obj, LTChar):
                chars.append(obj)
            elif isinstance(obj, LTTextContainer) or hasattr(obj, '__iter__'):
                chars.extend(collect_ltchars(obj))
    return chars

def analyze_font_characteristics(pdf_path):
    """Analyze font sizes and characteristics across the document to establish thresholds"""
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
                    
                    # Italic detection
                    is_italic = any('italic' in name.lower() or 'oblique' in name.lower() for name in font_names if name)

                    # Whitespace-above analysis (difference in y0 from previous line)
                    whitespace_above = None
                    if hasattr(text_line, 'y0') and hasattr(text_line, 'y1'):
                        whitespace_above = text_line.y0  # Will be used in context of previous line

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
    """Determine font size thresholds for different heading levels"""
    # Get font sizes for potential headings (short lines, not too small)
    heading_candidates = [
        item for item in font_data 
        if item['length'] <= 100 and item['font_size'] >= 10
    ]
    
    if not heading_candidates:
        return {'h1': 16, 'h2': 14, 'h3': 12, 'body': 10}
    
    font_sizes = [item['font_size'] for item in heading_candidates]
    font_counter = Counter(font_sizes)
    unique_sizes = sorted(set(font_sizes), reverse=True)
    
    # Determine thresholds based on font size distribution
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
    
    # Estimate body text size
    all_sizes = [item['font_size'] for item in font_data]
    body_threshold = min(all_sizes) if all_sizes else 10
    
    return {
        'h1': h1_threshold,
        'h2': h2_threshold, 
        'h3': h3_threshold,
        'body': body_threshold
    }

# Helper function to detect heading level from numbering pattern
import re

def heading_level_from_numbering(text):
    text = text.strip()
    # H2: 1, 2, 3, ... or 1. or 2.
    if re.match(r'^\d+([\s\.]|$)', text):
        return 'H2'
    # H3: 1.1, 2.3, ... or 1.1. or 2.3.
    if re.match(r'^\d+\.\d+([\s\.]|$)', text):
        return 'H3'
    # H4: 1.1.1, 2.3.4, ...
    if re.match(r'^\d+\.\d+\.\d+([\s\.]|$)', text):
        return 'H4'
    return None

def is_likely_heading(text, font_size, is_bold, is_italic, whitespace_above, y_position, thresholds, page_height=800):
    """Determine if text is likely a heading based on various characteristics, now including numbering pattern."""
    text = text.strip()
    # Basic filters
    if len(text) < 2 or len(text) > 150:
        return False, None
    # Skip common non-heading patterns
    skip_patterns = [
        r'^\d+$',  # Just numbers
        r'^page \d+',  # Page numbers
        r'^\d{1,3}\.?\d*$',  # Decimal numbers
        r'^[ivxlcdm]+\.?$',  # Roman numerals
        r'^[a-z]\.$',  # Single letters with period
        r'\.{3,}',  # Multiple dots
        r'^©',  # Copyright
        r'^\s*\d+\s*$'  # Whitespace + numbers
    ]
    for pattern in skip_patterns:
        if re.match(pattern, text.lower()):
            return False, None
    # Determine heading level based on font size
    level_font = None
    if font_size >= thresholds['h1'] - 0.5:
        level_font = "H1"
    elif font_size >= thresholds['h2'] - 0.5:
        level_font = "H2" 
    elif font_size >= thresholds['h3'] - 0.5:
        level_font = "H3"
    # Determine heading level from numbering pattern
    level_pattern = heading_level_from_numbering(text)
    # Combine: prefer deeper level if they disagree
    level = level_font
    if level_pattern:
        if level_font == 'H1' and level_pattern in ['H2', 'H3', 'H4']:
            level = level_pattern
        elif level_font == 'H2' and level_pattern in ['H3', 'H4']:
            level = level_pattern
        elif level_font == 'H3' and level_pattern == 'H4':
            level = level_pattern
        else:
            # If pattern is shallower or equal, keep font-based
            pass
    # Additional scoring for heading likelihood
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
    if len(text.split()) <= 8:  # Reasonable heading length
        score += 1
    # Whitespace-above: boost if more whitespace than typical (e.g., > 20 units)
    if whitespace_above is not None and whitespace_above > page_height * 0.7:
        score += 1
    # Position-based scoring (headings often at top of page)
    if y_position > page_height * 0.8:
        score += 1
    return score >= 3, level

# List of generic/boilerplate headings to ignore unless they are the only heading
GENERIC_HEADINGS = set([
    'overview', 'abstract', 'mission statement', 'address:', 'goals:', 'summary', 'background', 'table of contents', 'contents', 'keywords:', 'references', 'appendix', 'milestones', 'timeline:', 'contact', 'date', 'page', 'author', 'introduction', 'acknowledgements', 'revision history', 'proposal', 'rsvp:', 'www.topjump.com', 'hope to see you there!', 'topjump', 'march 21, 2003', 'digital library', 'business plan', 'prosperity strategy', 'stem pathways', 'regular pathway', 'distinction pathway', 'pathway options', 'school', 'student', 'experience', 'support', 'future opportunities', 'career', 'objectives', 'structure', 'duration', 'requirements', 'audience', 'trademarks', 'documents and web sites', 'synthesis', 'preparation', 'methods', 'results', 'discussion', 'conclusion', 'appendix a', 'appendix b', 'appendix c', 'appendix d', 'appendix e', 'appendix f', 'appendix g', 'appendix h', 'appendix i', 'appendix j', 'appendix k', 'appendix l', 'appendix m', 'appendix n', 'appendix o', 'appendix p', 'appendix q', 'appendix r', 'appendix s', 'appendix t', 'appendix u', 'appendix v', 'appendix w', 'appendix x', 'appendix y', 'appendix z'
])

def clean_heading_text(text):
    # Remove extra whitespace, join lines, and normalize
    return re.sub(r'\s+', ' ', text).strip()

def merge_multiline_headings(headings):
    # Merge consecutive headings on the same page, same level, close y_position, and similar font
    if not headings:
        return []
    merged = []
    prev = None
    for h in headings:
        text = clean_heading_text(h['text'])
        if prev and h['page'] == prev['page'] and h['level'] == prev['level']:
            # Merge if y_position is close (e.g., < 30 units apart)
            if abs(h.get('y_position', 0) - prev.get('y_position', 0)) < 30:
                prev['text'] += ' ' + text
                continue
        merged.append(h.copy())
        prev = merged[-1]
    return merged

def filter_generic_headings(headings):
    # Remove generic/boilerplate headings unless they are the only heading on the page
    filtered = []
    page_to_headings = {}
    for h in headings:
        page_to_headings.setdefault(h['page'], []).append(h)
    for h in headings:
        text = clean_heading_text(h['text']).lower().rstrip(':')
        if text in GENERIC_HEADINGS and len(page_to_headings[h['page']]) > 1:
            continue
        filtered.append(h)
    return filtered

def deduplicate_headings(headings):
    # Remove duplicate headings (same text, level, and page)
    seen = set()
    deduped = []
    for h in headings:
        key = (clean_heading_text(h['text']).lower(), h['level'], h['page'])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(h)
    return deduped

def normalize_page_number(page):
    # Convert to 0-based page number if needed
    return max(0, page - 1)

def improved_extract_title(headings):
    # Merge the top N lines with the largest font on the first page for the title
    if not headings:
        return "Untitled Document"
    # Find all H1s on the first page
    h1s = [h for h in headings if h['level'] == 'H1' and h['page'] == 1]
    if h1s:
        # Merge their text for the title
        title = ' '.join([clean_heading_text(h['text']) for h in h1s])
        return title.strip()
    # Fallback: merge all headings on page 1
    page1 = [h for h in headings if h['page'] == 1]
    if page1:
        title = ' '.join([clean_heading_text(h['text']) for h in page1])
        return title.strip()
    # Fallback: first heading
    return clean_heading_text(headings[0]['text'])

def extract_outline(pdf_path):
    """Extract structured outline from PDF with improved logic"""
    print(f"Processing: {pdf_path}")
    font_data = analyze_font_characteristics(pdf_path)
    thresholds = determine_heading_thresholds(font_data)
    print(f"Font thresholds: {thresholds}")
    outline = []
    raw_headings = []
    any_lines_found = False
    for page_num, page_layout in enumerate(extract_pages(pdf_path), 1):
        page_height = page_layout.height
        prev_y = None
        for element in page_layout:
            if isinstance(element, LTTextContainer):
                lines_found_in_box = False
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
                            "page": normalize_page_number(page_num),
                            "y_position": y_position
                        }
                        raw_headings.append(heading_entry)
                    any_lines_found = True
                    lines_found_in_box = True
                if not lines_found_in_box:
                    box_text = element.get_text().strip()
                    if not box_text:
                        continue
                    chars = collect_ltchars(element)
                    font_sizes = [char.size for char in chars]
                    font_names = [getattr(char, 'fontname', '') for char in chars]
                    if not font_sizes:
                        continue
                    avg_font = sum(font_sizes) / len(font_sizes)
                    is_bold = any('bold' in name.lower() for name in font_names if name)
                    is_italic = any('italic' in name.lower() or 'oblique' in name.lower() for name in font_names if name)
                    y_position = getattr(element, 'y0', 0)
                    whitespace_above = None
                    if prev_y is not None:
                        whitespace_above = y_position - prev_y
                    prev_y = y_position
                    is_heading, level = is_likely_heading(
                        box_text, avg_font, is_bold, is_italic, whitespace_above, y_position, thresholds, page_height
                    )
                    if is_heading and level:
                        heading_entry = {
                            "level": level,
                            "text": box_text,
                            "page": normalize_page_number(page_num),
                            "y_position": y_position
                        }
                        raw_headings.append(heading_entry)
                    any_lines_found = True
    # Merge multi-line headings
    merged_headings = merge_multiline_headings(raw_headings)
    # Filter out generic/boilerplate headings
    filtered_headings = filter_generic_headings(merged_headings)
    # De-duplicate
    deduped_headings = deduplicate_headings(filtered_headings)
    # Remove y_position from output
    final_headings = [
        {"level": h["level"], "text": clean_heading_text(h["text"]), "page": h["page"]}
        for h in deduped_headings
    ]
    # Improved title extraction
    title = improved_extract_title(final_headings)
    # Remove title from outline if it appears as first heading
    if final_headings and clean_heading_text(final_headings[0]['text']) == clean_heading_text(title):
        final_headings = final_headings[1:]
    print(f"\nExtracted {len(final_headings)} headings")
    print(f"Title: {title}")
    return {"title": title, "outline": final_headings}

def main():
    """Main function to process all PDFs in input directory"""
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    
    pdf_files = [f for f in os.listdir(input_dir) if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        print(f"No PDF files found in {input_dir} directory")
        return
    
    for filename in pdf_files:
        print(f"\n{'='*50}")
        print(f"Processing: {filename}")
        print(f"{'='*50}")
        
        full_path = os.path.join(input_dir, filename)
        
        try:
            result = extract_outline(full_path)
            
            output_filename = os.path.splitext(filename)[0] + ".json"
            output_path = os.path.join(output_dir, output_filename)
            
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            print(f"\nOutput saved to: {output_path}")
            print(f"Title: {result['title']}")
            print(f"Found {len(result['outline'])} headings")
            
        except Exception as e:
            print(f"Error processing {filename}: {str(e)}")

if __name__ == "__main__":
    main()
