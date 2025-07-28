# Adobe R1A - PDF Analysis and Processing Solutions

This repository contains two distinct PDF processing challenges, each designed to solve different document analysis problems using lightweight, rule-based approaches.

## Project Overview

### Challenge 1A: PDF Outline Extraction

**Objective**: Extract structured outlines (headings hierarchy and document titles) from PDF files.

**Key Features**:

- Analyzes font characteristics (size, bold, italic) to identify heading levels
- Uses numbering patterns to classify heading hierarchy (H1, H2, H3, etc.)
- Filters out generic/boilerplate content
- Merges multi-line headings and removes duplicates
- Outputs structured JSON with document title and outline

### Challenge 1B: Persona-Based Section Extraction

**Objective**: Extract the most relevant document sections based on user persona and job requirements.

**Key Features**:

- Analyzes documents using fuzzy pattern matching and font-based detection
- Scores sections based on relevance to persona and job-to-be-done
- Performs intelligent content refinement and sub-section analysis
- Provides ranked results with importance scoring
- Designed for HR professionals creating fillable forms for onboarding and compliance

## Common Technologies

Both challenges utilize:

- **Python 3.10** with Alpine/Slim base images
- **pdfminer.six** for PDF parsing and layout analysis
- **Docker** for containerization and deployment
- **Rule-based algorithms** (no machine learning models)
- **Offline processing** (no internet connectivity required)

## Quick Start

### Prerequisites

- Docker installed on your system
- PDF files to process

### Challenge 1A - Outline Extraction

1. **Navigate to challenge1a directory**:

   ```bash
   cd challenge1a/
   ```

2. **Build the Docker image**:

   ```bash
   docker build --platform linux/amd64 -t adobechallenge1a:teamarray .
   ```

3. **Run the solution**:
   ```bash
   docker run --rm \
     -v /absolute/path/to/challenge1a/input:/app/input \
     -v /absolute/path/to/challenge1a/output:/app/output \
     --network none \
     adobechallenge1a:teamarray
   ```

**Output**: For each `filename.pdf` in `input/`, creates `filename.json` in `output/` with extracted outline and title.

### Challenge 1B - Section Extraction

1. **Navigate to challenge1b directory**:

   ```bash
   cd challenge1b/
   ```

2. **Build the Docker image**:

   ```bash
   docker build --platform linux/amd64 -t adobechallenge1b:teamarray .
   ```

3. **Run the solution**:
   ```bash
   docker run --rm \
     -v /absolute/path/to/challenge1b:/app \
     --network none \
     adobechallenge1b:teamarray
   ```

**Input**: Requires `input.json` with document list, persona, and job description.
**Output**: Creates `output.json` with ranked relevant sections and analysis.

## Architecture Highlights

### Lightweight Design

- **Small Docker Images**: Both solutions maintain compact image sizes for fast deployment
- **No ML Dependencies**: Rule-based algorithms ensure predictable performance and resource usage
- **Offline Operation**: Complete functionality without internet connectivity

### Rule-Based Intelligence

- **Font Analysis**: Statistical analysis of font sizes, styles, and positioning
- **Pattern Recognition**: Fuzzy matching for expected content patterns
- **Heuristic Scoring**: Multi-factor relevance scoring based on keywords, content quality, and structure

### Production Ready

- **Containerized Deployment**: Docker-based solutions for consistent environments
- **Error Handling**: Graceful handling of malformed PDFs and edge cases
- **Scalable Processing**: Efficient batch processing of multiple documents

## File Structure

```
Adobe_R1A/
├── README.md                    # This file
├── challenge1a/                 # Outline extraction solution
│   ├── Dockerfile
│   ├── main.py                  # Core outline extraction logic
│   ├── requirements.txt
│   ├── README.md                # Challenge-specific documentation
│   ├── input/                   # PDF input directory
│   └── output/                  # JSON output directory
└── challenge1b/                 # Section extraction solution
    ├── Dockerfile
    ├── main.py                  # Core section analysis logic
    ├── requirements.txt
    ├── README.md                # Challenge-specific documentation
    ├── input.json               # Configuration and document list
    ├── output.json              # Analysis results
    └── PDFs/                    # PDF document directory
```

## Development Notes

### Memory Constraints

Both solutions are designed to work within memory constraints, with Docker images kept under 1GB for efficient deployment.

### Extensibility

The rule-based approach allows for easy customization:

- Modify keyword sets for different domains
- Adjust scoring weights for different priorities
- Add new pattern recognition rules without retraining

### Performance

Optimized for fast processing through:

- Efficient PDF parsing with minimal memory footprint
- Statistical font analysis instead of complex ML inference
- Streamlined text processing pipelines

## Support

For detailed implementation information, refer to the individual README files in each challenge directory:

- `challenge1a/README.md` - Outline extraction details
- `challenge1b/README.md` - Section extraction methodology

---

**Note**: Both solutions prioritize interpretability, efficiency, and reliability over complex ML approaches, making them suitable for production environments requiring consistent and explainable results.
