import os
import shutil
from pathlib import Path

def fix_mojibake(text):
    """Attempt to fix cp1252 -> utf-8 mojibake."""
    try:
        # If it contains typical mojibake characters, try decoding
        if 'â' in text:
            # We replace specific known mojibake manually to avoid encode/decode errors on mixed content
            replacements = {
                'â€”': '—',
                'â€“': '–',
                'â€™': "'",
                'â€˜': "'",
                'â€œ': '"',
                'â€\x9d': '"',
                'â€': '"',
                'â€¦': '...',
                'â€²': "'",
                'â€³': '"',
                'â€¢': '-',
            }
            for k, v in replacements.items():
                text = text.replace(k, v)
    except Exception as e:
        print("Error fixing mojibake:", e)
    return text

def fix_structured_markdowns():
    structured_dir = Path(r"C:\Users\jackl\OneDrive\Documents\私人文件\金融投资\value Investing\Annual meeting\structured")
    clean_mds_dir = Path(r"C:\Users\jackl\buffett_kb\data\clean_mds")
    
    md_files = list(structured_dir.glob("*.md"))
    print(f"Fixing encoding for {len(md_files)} files...")
    
    for md_path in md_files:
        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        fixed_content = fix_mojibake(content)
        
        # Save back to structured
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(fixed_content)
            
        # Copy to clean_mds
        dest_path = clean_mds_dir / md_path.name
        with open(dest_path, 'w', encoding='utf-8') as f:
            f.write(fixed_content)

def cleanup_root_dir():
    root_dir = Path(r"C:\Users\jackl")
    archive_dir = Path(r"C:\Users\jackl\buffett_kb\scripts_archive")
    archive_dir.mkdir(parents=True, exist_ok=True)
    
    files_to_move = [
        "buffett_full_scraper.py",
        "buffett_meeting_scraper.py",
        "clean_transcript.py",
        "save_buffett_pdf.py",
        "test_gemini_api.py",
        "test_retrieval_2008.py",
        "test_retrieval_v2.py",
        "test_retrieval.py",
        "使用说明.md",
    ]
    
    files_to_delete = [
        "Buffett_2024_Afternoon_Raw.txt",
        "Buffett_2024_Cleaned.txt",
        "temp.lua",
        "requirements.txt"  # Duplicate of the one in buffett_kb
    ]
    
    print("\nMoving files to archive...")
    for f in files_to_move:
        src = root_dir / f
        if src.exists():
            shutil.move(str(src), str(archive_dir / f))
            print(f"Moved: {f}")
            
    print("\nDeleting unnecessary files...")
    for f in files_to_delete:
        src = root_dir / f
        if src.exists():
            os.remove(str(src))
            print(f"Deleted: {f}")

if __name__ == "__main__":
    fix_structured_markdowns()
    cleanup_root_dir()
    print("\nDone!")
