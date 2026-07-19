# Document ingestion

## Supported formats

- PDF with an embedded text layer.
- DOCX Open XML documents without macros.
- UTF-8 TXT files, with or without a byte-order mark.

The default upload limit is 10 MB, the PDF limit is 100 pages, and extracted text is limited to 100,000 characters. Operators can adjust these bounds through the documented environment variables.

## Processing model

1. Read the upload in bounded chunks.
2. Normalize the filename to its basename.
3. Require an allowed extension and matching file signature.
4. Apply format-specific safety checks.
5. Extract normalized text, sections, and source references.
6. Detect instruction-like content as a warning without following it.
7. Calculate a SHA-256 fingerprint and extraction-confidence estimate.
8. Return the extraction and discard the original bytes.

PDF references contain page and line positions. DOCX references contain paragraph or table-row positions. TXT references contain line positions. If these references are supplied to a comparison, the API verifies that their combined text exactly matches the submitted document text.

## DOCX protections

DOCX archives are rejected when they contain unsafe paths, excessive entry counts, excessive decompressed size or compression ratios, missing Open XML document parts, or macro payloads. External relationships are never fetched and generate a visible warning.

## Limitations

- Scanned PDFs require OCR, which is not included yet.
- Complex multi-column PDF reading order depends on the PDF text layer.
- DOCX floating objects, images, headers, footers, comments, and tracked-change semantics are not extracted.
- Original uploaded files are not persisted by design. Saved jobs and resume versions retain normalized extracted text, source-reference metadata, and extraction warnings.
