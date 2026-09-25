"""
CapitalFit — Zip Packaging Utility
Bundles the entire repository into capitalfit_release.zip for direct GitHub upload or deployment.
"""

import os
import zipfile

EXCLUDE_DIRS = {"__pycache__", ".pytest_cache", ".git", "venv", ".venv"}
EXCLUDE_FILES = {"capitalfit_release.zip", ".DS_Store"}

def package_project():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    output_zip = os.path.join(root_dir, "capitalfit_release.zip")

    print(f"Packaging CapitalFit codebase into: {output_zip}")

    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(root_dir):
            # Prune excluded directories
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

            for file in files:
                if file in EXCLUDE_FILES or file.endswith(".pyc"):
                    continue
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, root_dir)
                zipf.write(file_path, arcname)
                print(f"  + Added: {arcname}")

    print(f"\nSuccessfully created release zip: {output_zip} ({os.path.getsize(output_zip) / 1024:.1f} KB)")

if __name__ == "__main__":
    package_project()
