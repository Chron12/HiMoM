#!/usr/bin/env python3
"""Replace [SCREENSHOT: ...] placeholders with actual image references."""

import re
import os

DOCS_DIR = os.path.join(os.path.dirname(__file__), '..', 'docs')

# Mapping: substring in placeholder description → screenshot filename
# Screenshots are in docs/screenshots/, so paths are relative from each doc's location
SCREENSHOT_MAP = [
    # Login / Auth
    ("login page", "login-page.png"),
    ("password field, Remember Me", "login-page.png"),
    ("Forgot Password page", "forgot-password.png"),
    ("recovery key input", "forgot-password.png"),

    # Dashboard
    ("full Production Dashboard", "dashboard.png"),
    ("Production Dashboard at the start", "dashboard.png"),
    ("Dashboard displaying correctly", "dashboard.png"),
    ("navigation bar with all buttons", "dashboard.png"),
    ("batch card showing the stage badge", "dashboard.png"),
    ("batches showing different stage badges", "dashboard.png"),
    ("low-stock alert banner on the dashboard", "dashboard.png"),
    ("low-stock alert banner on the Production Dashboard", "dashboard.png"),
    ("dismiss button on an inventory alert", "dashboard.png"),

    # Edit Batch
    ("Edit Batch page with the production count", "edit-batch-counts.png"),
    ("stage dropdown on the Edit Batch", "edit-batch-top.png"),
    ("production time section", "edit-batch-counts.png"),
    ("centrifuge settings section on the Edit Batch", "edit-batch-centrifuge-settings.png"),
    ("centrifuge recommendation card", "edit-batch-centrifuge.png"),
    ("weight log section", "edit-batch-full.png"),
    ("production rate section", "edit-batch-full.png"),
    ("detailed Edit Batch page", "edit-batch-full.png"),
    ("successful count save", "edit-batch-counts.png"),
    ("batch card showing the Archive button", "archive.png"),

    # Analytics
    ("full Analytics/Stats page", "analytics-full.png"),
    ("summary cards at the top of the Stats", "analytics-summary-cards.png"),
    ("production over time chart", "analytics-full.png"),
    ("production by size chart", "analytics-strain-performance.png"),
    ("production rate trend", "analytics-strain-performance.png"),
    ("time period selector", "analytics-summary-cards.png"),

    # Archive
    ("Archive page showing a list", "archive.png"),
    ("search bar or filter options on the Archive", "archive.png"),

    # Audit
    ("Audit page showing a list of recent changes", "audit.png"),

    # Settings
    ("Change Password section", "settings-change-password.png"),
    ("change password", "settings-change-password.png"),
    ("API Key section", "settings-full.png"),
    ("API key visible and a copy button", "settings-full.png"),
    ("Pushover notification configuration", "settings-full.png"),
    ("Pushover configuration section", "settings-full.png"),

    # Paper Inventory
    ("Paper Inventory page showing current levels", "paper-inventory.png"),
    ("inventory card for one size", "paper-inventory.png"),
    ("inventory update fields", "paper-inventory.png"),
    ("admin inventory page with threshold", "paper-inventory.png"),

    # Finished Goods
    ("Finished Goods page showing a list", "finished-goods.png"),
    ("search bar on the Finished Goods", "finished-goods.png"),
    ("detail view of a single finished goods", "finished-goods.png"),
    ("SKU breakdown table", "finished-goods.png"),

    # Wholesale
    ("Wholesale page showing available strains", "wholesale.png"),
    ("create hold form", "wholesale.png"),
    ("release/delete button", "wholesale.png"),

    # Recovery key
    ("password reset confirmation", "settings-recovery-key.png"),
    ("Recovery Key", "settings-recovery-key.png"),
]

def get_screenshot_path(description, doc_subdir):
    """Find matching screenshot for a description, return relative path."""
    desc_lower = description.lower()
    for pattern, filename in SCREENSHOT_MAP:
        if pattern.lower() in desc_lower:
            screenshot_path = os.path.join(DOCS_DIR, 'screenshots', filename)
            if os.path.exists(screenshot_path):
                # Calculate relative path from doc's directory to screenshots/
                if doc_subdir:
                    return f"../screenshots/{filename}"
                else:
                    return f"screenshots/{filename}"
    return None


def process_file(filepath):
    """Replace screenshot placeholders in a single file."""
    with open(filepath, 'r') as f:
        content = f.read()

    # Determine subdirectory depth for relative paths
    rel_path = os.path.relpath(filepath, DOCS_DIR)
    doc_subdir = os.path.dirname(rel_path)

    replacements = 0
    skipped = []

    def replace_placeholder(match):
        nonlocal replacements
        description = match.group(1)
        img_path = get_screenshot_path(description, doc_subdir)
        if img_path:
            replacements += 1
            # Use markdown image syntax
            alt_text = description.strip()
            return f"![{alt_text}]({img_path})"
        else:
            skipped.append(description.strip())
            return match.group(0)  # Keep original placeholder

    new_content = re.sub(r'\[SCREENSHOT:\s*(.+?)\]', replace_placeholder, content)

    if replacements > 0:
        with open(filepath, 'w') as f:
            f.write(new_content)

    return replacements, skipped


def main():
    total_replaced = 0
    total_skipped = []

    for root, dirs, files in os.walk(DOCS_DIR):
        for filename in files:
            if filename.endswith('.md'):
                filepath = os.path.join(root, filename)
                replaced, skipped = process_file(filepath)
                if replaced > 0 or skipped:
                    rel = os.path.relpath(filepath, DOCS_DIR)
                    print(f"  {rel}: {replaced} replaced, {len(skipped)} skipped")
                    total_replaced += replaced
                    total_skipped.extend(skipped)

    print(f"\nTotal: {total_replaced} placeholders replaced")
    print(f"Skipped: {len(total_skipped)} placeholders (no matching screenshot)")
    if total_skipped:
        print("\nSkipped placeholders:")
        for desc in total_skipped:
            print(f"  - {desc}")


if __name__ == '__main__':
    main()
