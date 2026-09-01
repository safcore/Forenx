# Synthetic AI Investigation Scenario (Phase 9)

This directory contains **synthetic** artifacts used to demonstrate AI-assisted
investigation over deterministic ForenX outputs. Nothing here was collected from
real people or live systems.

## Scenario facts (synthetic)

- Case ID: `CASE-AI-SYN`
- Evidence ID: `EV-AI-SYN`
- File: `suspicious_notes.txt`
- Known integrity: SHA-256 is computed live from the file during demos/tests
- Keyword indicators present: `confidential`, `bitcoin`, `phishing`
- Benign content also present (meeting notes / grocery items)
- Chain of custody should be recorded as valid when demonstrated via CustodyService

## Expected assistive conclusions

Assistive / fallback analysis may observe:

- integrity PASS for the current file digest
- keyword matches including suspicious lexicon hits
- optional timeline density from filesystem timestamps
- custody validity only when a verified chain is supplied

Assistive output is **advisory only** and is not independent forensic evidence.
