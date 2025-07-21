import os
import json
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer, LTChar

input_dir = 'input'
output_dir = 'output'

def extract_outline(pdf_path):
    outline = []
    title = ""
    candidate_headings = []

    for page_num, page_layout in enumerate(extract_pages(pdf_path), 1):
        print(f"\n--- Page {page_num} ---")
        for element in page_layout:
            if isinstance(element, LTTextContainer):
                for text_line in element:
                    line_text = text_line.get_text().strip()
                    font_sizes = [char.size for char in getattr(text_line, 'objs', []) if isinstance(char, LTChar)]
                    if font_sizes:
                        avg_font = sum(font_sizes) / len(font_sizes)
                        print(f"DEBUG: '{line_text}' | Avg font: {avg_font:.2f} | Length: {len(line_text)}")
                    if line_text and len(line_text) < 60 and font_sizes:
                        avg_font = sum(font_sizes) / len(font_sizes)
                        if avg_font >= 10:  
                            level = "H1"
                            candidate_headings.append({"level": level, "text": line_text, "page": page_num})
        print(f"Headings found on page {page_num}: {len(candidate_headings)}")
    # Guess first heading as title
    if candidate_headings:
        title = candidate_headings[0]['text']
    return {"title": title, "outline": candidate_headings}

def main():
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    pdf_files = [f for f in os.listdir(input_dir) if f.lower().endswith('.pdf')]
    for filename in pdf_files:
        full_path = os.path.join(input_dir, filename)
        result = extract_outline(full_path)
        output_filename = os.path.splitext(filename)[0] + ".json"
        with open(os.path.join(output_dir, output_filename), "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()
