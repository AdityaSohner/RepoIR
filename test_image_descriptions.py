"""
test_image_descriptions.py
--------------------------
Test module: for each image path in IMAGE_PATHS --
  1. Generate a vision description via local llava:7b (Ollama)
  2. Append the result to image_descriptions.txt in the root folder
  3. Run the full ingestion pipeline: embed + store into FAISS + SQLite DB

Run from the root directory:
    env\\Scripts\\python test_image_descriptions.py
"""

import os
import sys
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.ai.extractors.vision_describer import VisionDescriber
from app.ai.pipeline.ingestion_pipeline import IngestionPipeline
from app.config import DEFAULT_USER_ID

# -- PASTE YOUR IMAGE PATHS HERE ----------------------------------------------
IMAGE_PATHS = [
    r"C:\Users\adity\Downloads\ChatGPT Image Aug 24, 2026, 03_51_57 PM.png",
    r"C:\Users\adity\Downloads\newtemp.png",
    r"C:\Users\adity\Downloads\lc.jpg",
    r"C:\Users\adity\Downloads\WhatsApp Image 2026-05-07 at 08.13.59.jpeg"
]
# -----------------------------------------------------------------------------

OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "image_descriptions.txt")


def process_images():
    if not IMAGE_PATHS:
        print("[!] IMAGE_PATHS list is empty. Add image paths at the top of this file.")
        return

    describer = VisionDescriber()
    pipeline = IngestionPipeline(user_id=DEFAULT_USER_ID)

    print(f"[*] Processing {len(IMAGE_PATHS)} image(s)...")
    print(f"[*] Descriptions will be saved to: {OUTPUT_FILE}\n")

    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"Run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"{'='*60}\n\n")

        for i, path in enumerate(IMAGE_PATHS, 1):
            path = path.strip()
            if not path:
                continue

            filename = os.path.basename(path)
            print(f"[{i}/{len(IMAGE_PATHS)}] {filename}")

            if not os.path.exists(path):
                msg = f"ERROR: File not found: {path}"
                print(f"  [!] {msg}")
                f.write(f"File: {filename}\nPath: {path}\nDescription: {msg}\n{'-'*50}\n\n")
                continue

            # Step 1: Generate vision description
            try:
                description = describer.describe(path)
                if not description:
                    description = "(Empty response -- check Ollama is running with llava:7b loaded)"
                print(f"  [OK] Description ({len(description)} chars): {description[:120]}...")
            except Exception as e:
                description = f"ERROR generating description: {e}"
                print(f"  [!] Vision failed: {e}")

            # Step 2: Write to text file
            f.write(f"File: {filename}\n")
            f.write(f"Path: {path}\n")
            f.write(f"Description:\n{description}\n")
            f.write(f"{'-'*50}\n\n")
            f.flush()

            # Step 3: Ingest into DB + FAISS
            try:
                result = pipeline.ingest(
                    source=path,
                    source_type="image",
                    extension=os.path.splitext(path)[1].lower(),
                    original_name=filename,
                )
                print(f"  [OK] Ingested -> object_id={result['object_id']}, chunks={result['chunk_count']}")
            except Exception as e:
                print(f"  [!] Ingestion failed: {e}")

            print()

    print(f"\n[+] Done! All descriptions written to: {OUTPUT_FILE}")
    print(f"[+] Images are now searchable in the frontend.")


if __name__ == "__main__":
    process_images()
