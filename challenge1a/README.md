# Challenge 1A Solution

## Approach

This solution extracts a structured outline (headings and title) from PDF files. It uses font size, bold/italic style, and numbering patterns to identify headings and their levels. The process is fully rule-based and does not use any machine learning models, ensuring fast and lightweight execution.

**Key steps:**

- Analyze font characteristics (size, bold, italic) for each line in the PDF.
- Use font size thresholds and numbering patterns to classify headings (H1, H2, H3, etc.).
- Filter out generic or boilerplate headings.
- Merge multi-line headings and deduplicate.
- Extract the document title from the largest headings on the first page.
- Output a JSON file with the title and outline for each PDF.

## Models or Libraries Used

- **pdfminer.six**: For parsing and analyzing PDF files and extracting text and layout information.
- **Python Standard Library**: (`os`, `json`, `re`, `collections`)

No machine learning models are used. The solution is fully offline and lightweight.

## How to Build and Run

### 1. Build the Docker Image

From the `challenge1a` directory, run:

```
docker build --platform linux/amd64 -t adobechallenge1a:teamarray .
```

### 2. Run the Solution

From the same directory, run:

```
docker run --rm -v /absolute/path/to/challenge1a/input:/app/input -v /absolute/path/to/challenge1a/output:/app/output --network none adobechallenge1a:teamarray
```

- Replace `/absolute/path/to/challenge1a` with the full path to your `challenge1a` folder.
- The container will process all PDFs in `/app/input` and write corresponding `.json` files to `/app/output`.

### 3. Output

- For each `filename.pdf` in `input/`, a `filename.json` will be created in `output/` with the extracted outline and title.

---

**Note:**

- No internet connection is required.
- The solution does not use any models or files larger than 200MB.
- Only `pdfminer.six` is required as a dependency.
