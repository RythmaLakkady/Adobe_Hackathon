# Approach Explanation

## Overview

This solution acts as an intelligent document analyst, extracting and prioritizing the most relevant sections from a collection of PDFs based on a specific persona and their job-to-be-done. It is designed to be generic and robust across diverse document types, personas, and tasks.

## Methodology

1. **PDF Parsing & Outline Extraction**

   - For each PDF, the system extracts a structured outline (titles, headings, page numbers) using a robust, rule-based parser (adapted from Challenge 1A).
   - Section content is also extracted for deeper analysis.

2. **Semantic Relevance Scoring**

   - Each section/heading is scored for relevance to the persona and job-to-be-done using a local embedding model (e.g., MiniLM from sentence-transformers, <1GB).
   - The system computes semantic similarity between the persona/job description and each section, optionally combining this with keyword overlap and heading level weighting.

3. **Prioritization & Extraction**

   - Sections are ranked by relevance. The top-N most relevant sections are selected, with metadata (document, page, title, rank).
   - For each, the most relevant sub-section or paragraph is also extracted and summarized.

4. **Output Formatting**
   - The output is a structured JSON containing metadata, extracted sections, and sub-section analysis, as per the challenge specification.

## Constraints Handling

- **CPU-only**: All processing is local and efficient.
- **Model size ≤ 1GB**: Only small, local embedding models are used.
- **Processing time ≤ 60s**: The pipeline is optimized for speed and parallelism.
- **No internet access**: All dependencies and models are local.

## Generalization

- The system is modular and data-driven, with no hardcoded rules for specific document types or personas. It is designed to generalize to new domains, personas, and jobs-to-be-done.
