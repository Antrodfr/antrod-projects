#!/bin/bash
# extract-sources.sh — Extracts text from PDF, DOCX, MD, TXT files
# Usage: bash extract-sources.sh <file1> <file2> <folder> ...
# Output: creates _cv_sources/ directory with .txt files

set -e

OUTPUT_DIR="_cv_sources"
mkdir -p "$OUTPUT_DIR"

extract_pdf() {
    local file="$1"
    local out="$OUTPUT_DIR/$(basename "$file" .pdf).txt"
    
    if command -v python3 &>/dev/null && python3 -c "import pymupdf" 2>/dev/null; then
        python3 -c "
import pymupdf, sys
doc = pymupdf.open('$file')
for page in doc:
    print(page.get_text())
" > "$out"
    elif command -v pdftotext &>/dev/null; then
        pdftotext "$file" "$out"
    else
        echo "ERROR: No PDF extractor found. Install pymupdf (pip3 install pymupdf) or pdftotext." >&2
        return 1
    fi
    echo "Extracted: $file → $out"
}

extract_docx() {
    local file="$1"
    local out="$OUTPUT_DIR/$(basename "$file" .docx).txt"
    
    if [[ "$(uname)" == "Darwin" ]] && command -v textutil &>/dev/null; then
        textutil -convert txt -stdout "$file" > "$out"
    elif command -v pandoc &>/dev/null; then
        pandoc "$file" -t plain -o "$out"
    else
        echo "ERROR: No DOCX extractor found. Install pandoc or use macOS textutil." >&2
        return 1
    fi
    echo "Extracted: $file → $out"
}

extract_text() {
    local file="$1"
    local ext="${file##*.}"
    local out="$OUTPUT_DIR/$(basename "$file" ".$ext").txt"
    cp "$file" "$out"
    echo "Copied: $file → $out"
}

process_file() {
    local file="$1"
    local ext="${file##*.}"
    ext=$(echo "$ext" | tr '[:upper:]' '[:lower:]')
    
    case "$ext" in
        pdf)  extract_pdf "$file" ;;
        docx) extract_docx "$file" ;;
        md|txt|markdown) extract_text "$file" ;;
        *)    echo "SKIP: Unsupported file type: $file" >&2 ;;
    esac
}

process_path() {
    local path="$1"
    if [[ -d "$path" ]]; then
        # Recursively process all supported files in directory and subdirectories
        while IFS= read -r -d '' file; do
            process_file "$file"
        done < <(find "$path" -type f \( \
            -iname "*.pdf" -o -iname "*.docx" -o \
            -iname "*.md" -o -iname "*.txt" -o -iname "*.markdown" \
        \) -print0 | sort -z)
    elif [[ -f "$path" ]]; then
        process_file "$path"
    else
        echo "SKIP: Not found: $path" >&2
    fi
}

if [[ $# -eq 0 ]]; then
    echo "Usage: bash extract-sources.sh <file1> <file2> <folder> ..."
    echo "Supported formats: PDF, DOCX, MD, TXT"
    exit 1
fi

echo "=== CV Source Extractor ==="
for arg in "$@"; do
    process_path "$arg"
done
echo "=== Done. Extracted files in $OUTPUT_DIR/ ==="
