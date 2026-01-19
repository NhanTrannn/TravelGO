#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Download ML models from Google Drive
Run this script after cloning the repository to get the weather prediction models.
"""

import os
import sys
import requests
from pathlib import Path

# Google Drive file IDs
MODELS_DRIVE_ID = (
    "1aq2B1BpPP0VWUOjgJu_zG4dF1-cDPrb1"  # weather_models.zip on Google Drive
)

# Alternative: Individual region files
REGION_DRIVE_IDS = {
    "southern": "YOUR_SOUTHERN_ID",
    "south_central_coast": "YOUR_SOUTH_CENTRAL_COAST_ID",
    "red_river_delta": "YOUR_RED_RIVER_DELTA_ID",
    "north_central": "YOUR_NORTH_CENTRAL_ID",
    "northeast": "YOUR_NORTHEAST_ID",
    "northwest": "YOUR_NORTHWEST_ID",
    "central_highlands": "YOUR_CENTRAL_HIGHLANDS_ID",
}


def download_from_gdrive(file_id: str, destination: str):
    """
    Download a file from Google Drive

    Args:
        file_id: Google Drive file ID
        destination: Local path to save the file
    """
    URL = "https://drive.google.com/uc?export=download"

    session = requests.Session()

    # First request to get confirmation token for large files
    response = session.get(URL, params={"id": file_id}, stream=True)

    # Check for confirmation token (required for large files)
    token = None
    for key, value in response.cookies.items():
        if key.startswith("download_warning"):
            token = value
            break

    if token:
        params = {"id": file_id, "confirm": token}
        response = session.get(URL, params=params, stream=True)

    # Save the file
    total_size = int(response.headers.get("content-length", 0))
    block_size = 8192
    downloaded = 0

    print(f"📥 Downloading to {destination}...")

    with open(destination, "wb") as f:
        for chunk in response.iter_content(chunk_size=block_size):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    percent = (downloaded / total_size) * 100
                    print(f"\r   Progress: {percent:.1f}%", end="", flush=True)

    print(f"\n✅ Downloaded: {destination}")
    return True


def extract_zip(zip_path: str, extract_to: str):
    """Extract zip file"""
    import zipfile

    print(f"📦 Extracting {zip_path}...")
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(extract_to)
    print(f"✅ Extracted to {extract_to}")

    # Remove zip file after extraction
    os.remove(zip_path)
    print(f"🗑️  Removed {zip_path}")


def main():
    # Get project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    models_dir = project_root / "saved_models"

    print("=" * 60)
    print("🌤️  SaoLa AI - Weather Models Downloader")
    print("=" * 60)

    # Check if models already exist
    if models_dir.exists():
        pkl_files = list(models_dir.glob("**/*.pkl"))
        if pkl_files:
            print(f"\n⚠️  Found {len(pkl_files)} model files already exist.")
            response = input("Do you want to re-download? (y/N): ")
            if response.lower() != "y":
                print("Cancelled.")
                return

    # Create models directory
    models_dir.mkdir(parents=True, exist_ok=True)

    # Download models
    print("\n📡 Downloading models from Google Drive...")

    if MODELS_DRIVE_ID != "YOUR_GOOGLE_DRIVE_FILE_ID":
        # Download all models as zip
        zip_path = project_root / "models.zip"
        download_from_gdrive(MODELS_DRIVE_ID, str(zip_path))
        extract_zip(str(zip_path), str(models_dir))
    else:
        print("\n❌ Error: Google Drive IDs not configured!")
        print("\nTo configure:")
        print("1. Upload your models to Google Drive")
        print("2. Get the file ID from the share link")
        print("3. Update MODELS_DRIVE_ID in this script")
        print("\nExample share link:")
        print("  https://drive.google.com/file/d/1ABC123xyz/view")
        print("  → File ID is: 1ABC123xyz")
        return

    print("\n" + "=" * 60)
    print("✅ Models downloaded successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
