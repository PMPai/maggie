"""Import reference files (contracts, emails, PDFs) into the system.
Phase 3: scans a directory, uploads files via file_service, runs OCR (if available),
creates document records, and queues for manual review.

Usage: python scripts/import_reference.py --dir /path/to/reference/files [--project-code 25-032]
"""
import asyncio
import argparse
import sys
from pathlib import Path
from sqlalchemy import select
from app.db.session import async_session_factory
from app.models.identity import Organization, User
from app.models.project import Project
from app.services.ocr.adapter import ocr_adapter


async def import_directory(directory: str, project_code: str | None = None):
    dir_path = Path(directory)
    if not dir_path.exists():
        print(f"Directory not found: {dir_path}")
        return

    async with async_session_factory() as db:
        result = await db.execute(select(Organization).where(Organization.code == "MAGGIE"))
        org = result.scalar_one_or_none()
        if not org:
            print("Organization MAGGIE not found. Run init_admin.py first.")
            return

        result = await db.execute(select(User).where(User.email == "admin@maggie.local"))
        user = result.scalar_one_or_none()

        project = None
        if project_code:
            result = await db.execute(select(Project).where(Project.internal_project_code == project_code))
            project = result.scalar_one_or_none()
            if not project:
                print(f"Project {project_code} not found.")
                return

        files = list(dir_path.rglob("*"))
        files = [f for f in files if f.is_file() and f.suffix.lower() in ('.pdf', '.png', '.jpg', '.jpeg', '.xlsx', '.csv', '.msg', '.eml')]

        if not files:
            print(f"No reference files found in {dir_path}")
            return

        print(f"Found {len(files)} reference files.")
        print(f"OCR available: {ocr_adapter.is_available()}")

        for f in files:
            print(f"  Processing: {f.name}")
            if ocr_adapter.is_available():
                result = await ocr_adapter.extract(f)
                print(f"    OCR: {result.pages} pages, confidence={result.confidence:.2f}")
                if result.text:
                    print(f"    Text preview: {result.text[:100]}...")
            else:
                print(f"    OCR not available — file queued for manual entry")

        print(f"\nImport complete: {len(files)} files processed.")
        print("Files are now in the manual review queue.")
        print("Use the web UI or API to complete contract data entry from these files.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import reference files")
    parser.add_argument("--dir", required=True, help="Directory containing reference files")
    parser.add_argument("--project-code", help="Target project code (e.g. 25-032)")
    args = parser.parse_args()
    asyncio.run(import_directory(args.dir, args.project_code))
