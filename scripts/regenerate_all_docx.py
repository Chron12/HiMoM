#!/usr/bin/env python3
"""Regenerate all .docx files from their .md sources."""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from generate_docx import md_to_docx

DOCS_DIR = os.path.join(os.path.dirname(__file__), '..', 'docs')

# Map of md files to (title, subtitle)
DOCS = {
    "user-guides/getting-started.md": ("Getting Started", "First-time Setup Guide"),
    "user-guides/daily-operations.md": ("Daily Operations", "Production Workflow Guide"),
    "user-guides/reporting.md": ("Reporting", "Analytics & Statistics Guide"),
    "user-guides/managing-inventory.md": ("Managing Inventory", "Inventory Tracking Guide"),
    "user-guides/troubleshooting.md": ("Troubleshooting", "Common Problems & Solutions"),
    "user-guides/quick-reference-card.md": ("Quick Reference Card", "One-Page Cheat Sheet"),
    "admin-guides/system-administration.md": ("System Administration", "Server & User Management"),
    "admin-guides/data-management.md": ("Data Management", "Backup & Maintenance Guide"),
    "admin-guides/configuration-guide.md": ("Configuration Guide", "Settings Reference"),
    "admin-guides/integration-guide.md": ("Integration Guide", "API & Service Connections"),
    "admin-guides/deployment-checklist.md": ("Deployment Checklist", "Installation & Update Procedures"),
    "technical/architecture-overview.md": ("Architecture Overview", "System Design & Components"),
    "technical/database-schema.md": ("Database Schema", "Complete Schema Reference"),
    "technical/codebase-guide.md": ("Codebase Guide", "Source Code Organization"),
    "technical/development-setup.md": ("Development Setup", "Local Environment Guide"),
    "technical/testing-guide.md": ("Testing Guide", "Test Strategy & Execution"),
    "api-reference/api-reference.md": ("API Reference", "REST API Documentation"),
    "api-reference/webhooks-and-events.md": ("Webhooks & Events", "Event System Documentation"),
}

def main():
    success = 0
    errors = 0
    for md_rel, (title, subtitle) in DOCS.items():
        md_path = os.path.join(DOCS_DIR, md_rel)
        docx_path = md_path.replace('.md', '.docx')
        if os.path.exists(md_path):
            try:
                md_to_docx(md_path, docx_path, title, subtitle)
                success += 1
            except Exception as e:
                print(f"  ERROR: {md_rel}: {e}")
                errors += 1
        else:
            print(f"  SKIP: {md_rel} (not found)")

    # Also regenerate index docx
    index_md = os.path.join(DOCS_DIR, 'document-index.md')
    index_docx = os.path.join(DOCS_DIR, 'document-index.docx')
    if os.path.exists(index_md):
        try:
            md_to_docx(index_md, index_docx, "Document Index", "Complete Documentation Catalog")
            success += 1
        except Exception as e:
            print(f"  ERROR: document-index.md: {e}")
            errors += 1

    print(f"\nDone: {success} generated, {errors} errors")


if __name__ == '__main__':
    main()
