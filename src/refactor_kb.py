import os
import re
import shutil
from pathlib import Path

# Paths
ORIGINAL_DIR = Path(r"C:\Users\jackl\OneDrive\Documents\私人文件\金融投资\Markdown_Knowledge_Base")
CLEAN_DIR = Path(r"C:\Users\jackl\buffett_kb\data\clean_mds")

# Noise to exclude
EXCLUDE_PREFIXES = [
    "business case_",
    "Luckin Coffee_",
    "Deep-Hill_",
    "GPO-FCIC",
    "s13731-021-00157-5",
    "sea-change_sc",
    "The Great Depression",
    "deep_research_",
    "article_capitalallocation"
]

def is_noise(filename):
    for prefix in EXCLUDE_PREFIXES:
        if filename.startswith(prefix):
            return True
    return False

def extract_year(text):
    match = re.search(r"\b(197\d|198\d|199\d|200\d|201\d|202\d)\b", text)
    return int(match.group(1)) if match else None

def inject_frontmatter(content, metadata):
    yaml = "---\n"
    for k, v in metadata.items():
        if isinstance(v, list):
            v_str = "[" + ", ".join([f'"{x}"' for x in v]) + "]"
            yaml += f"{k}: {v_str}\n"
        elif isinstance(v, str):
            yaml += f'{k}: "{v}"\n'
        else:
            yaml += f"{k}: {v}\n"
    yaml += "---\n\n"
    return yaml + content

def normalize_name_and_metadata(filename):
    meta = {
        "title": filename.replace(".md", ""),
        "year": 0,
        "author": [],
        "doc_type": "document"
    }
    new_name = filename

    # Extract year if possible
    year = extract_year(filename)
    if year:
        meta["year"] = year

    # Rules
    if filename.startswith("PDFs_Buffett_") and ("Session" in filename or "Part" in filename):
        # PDFs_Buffett_1994_Afternoon_Session.md
        meta["author"] = ["Warren Buffett", "Charlie Munger"]
        meta["doc_type"] = "meeting_transcript"
        new_name = filename.replace("PDFs_Buffett_", f"{year}_Buffett_Meeting_") if year else filename
        meta["title"] = new_name.replace(".md", "").replace("_", " ")

    elif "shareholder‘s letter" in filename or "shareholder's letter" in filename:
        meta["author"] = ["Warren Buffett"]
        meta["doc_type"] = "shareholder_letter"
        new_name = f"{year}_Buffett_Letter_Shareholders.md" if year else filename.replace("shareholder‘s letter_", "")
        meta["title"] = f"{year} Berkshire Hathaway Shareholder Letter" if year else "Berkshire Hathaway Shareholder Letter"

    elif "value Investing" in filename or "Munger" in filename or "munger" in filename:
        meta["author"] = ["Charlie Munger"]
        meta["doc_type"] = "munger_wisdom"
        if year:
            new_name = f"{year}_Munger_Speech_{filename.split('-')[-1]}"
        meta["title"] = filename.replace("value Investing_", "").replace(".md", "").replace("-", " ")

    return new_name, meta

def process_big_letter_file(filepath):
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    
    # Split by "To the Shareholders"
    parts = re.split(r"(?i)To the (?:Stockholders|Shareholders) of Berkshire Hathaway Inc.*?:?", content)
    
    # parts[0] is intro
    for i, part in enumerate(parts[1:], 1):
        if len(part.strip()) < 500:
            continue
        
        # Try to find year in the first 300 chars
        header_text = part[:300]
        year = extract_year(header_text)
        if not year:
            continue
            
        meta = {
            "title": f"{year} Berkshire Hathaway Shareholder Letter",
            "year": year,
            "author": ["Warren Buffett"],
            "doc_type": "shareholder_letter"
        }
        
        new_content = f"To the Shareholders of Berkshire Hathaway Inc.:\n{part}"
        final_content = inject_frontmatter(new_content, meta)
        
        out_name = f"{year}_Buffett_Letter_Shareholders.md"
        out_path = CLEAN_DIR / out_name
        with open(out_path, "w", encoding="utf-8") as out_f:
            out_f.write(final_content)
        print(f"    -> Splitted {year} letter")

def main():
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    
    all_files = list(ORIGINAL_DIR.glob("*.md"))
    print(f"Found {len(all_files)} total markdown files.")
    
    processed_count = 0
    for f in all_files:
        if is_noise(f.name):
            print(f"Skipping noise: {f.name}")
            continue
            
        if "1977-2010" in f.name:
            print(f"Splitting big file: {f.name}")
            process_big_letter_file(f)
            processed_count += 1
            continue
            
        new_name, meta = normalize_name_and_metadata(f.name)
        
        # Read content and inject
        with open(f, "r", encoding="utf-8", errors="ignore") as in_f:
            content = in_f.read()
            
        final_content = inject_frontmatter(content, meta)
        
        out_path = CLEAN_DIR / new_name
        with open(out_path, "w", encoding="utf-8") as out_f:
            out_f.write(final_content)
            
        processed_count += 1
        print(f"Processed: {f.name} -> {new_name}")

    print(f"\\nDone! Refactored {processed_count} relevant files into {CLEAN_DIR}")

if __name__ == "__main__":
    main()
