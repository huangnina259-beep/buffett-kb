import os
import re
import shutil
import filecmp
from pathlib import Path

def normalize_filenames():
    mds_dir = Path(r"C:\Users\jackl\buffett_kb\data\clean_mds")
    files = list(mds_dir.glob("*.md"))
    
    print(f"Total files before cleanup: {len(files)}")
    
    # --- PASS 1: Identify exact duplicates ---
    duplicates_to_delete = set()
    for i in range(len(files)):
        for j in range(i + 1, len(files)):
            f1, f2 = files[i], files[j]
            # Fast check by size first
            if f1.stat().st_size == f2.stat().st_size:
                if filecmp.cmp(f1, f2, shallow=False):
                    # Keep the one with the better name (e.g. YYYY_Buffett_Letter_Shareholders.md is better than YYYYltr.md)
                    name1 = f1.name.lower()
                    name2 = f2.name.lower()
                    
                    score1 = len(name1) + (100 if "buffett" in name1 else 0)
                    score2 = len(name2) + (100 if "buffett" in name2 else 0)
                    
                    if score1 > score2:
                        duplicates_to_delete.add(f2)
                    else:
                        duplicates_to_delete.add(f1)

    print(f"\nFound {len(duplicates_to_delete)} exact duplicates to delete.")
    for d in duplicates_to_delete:
        print(f"Deleting duplicate: {d.name}")
        d.unlink()
        
    # Refresh file list
    files = list(mds_dir.glob("*.md"))
    
    # --- PASS 2: Delete 'Raw' files if a structured version exists ---
    raw_to_delete = set()
    for f in files:
        if "Raw" in f.name:
            year_match = re.search(r'(\d{4})', f.name)
            if year_match:
                year = year_match.group(1)
                # Check if structured versions exist for this year
                structured_exists = any(year in str(x.name) and "Session" in str(x.name) for x in files)
                if structured_exists:
                    raw_to_delete.add(f)
                    
    print(f"\nFound {len(raw_to_delete)} Raw transcripts with structured equivalents to delete.")
    for d in raw_to_delete:
        print(f"Deleting raw file: {d.name}")
        d.unlink()
        
    # Refresh file list
    files = list(mds_dir.glob("*.md"))
    
    # --- PASS 3: Rename files ---
    rename_count = 0
    for f in files:
        old_name = f.name
        new_name = old_name
        
        # 1. Shareholder Letters (e.g., 1977_Buffett_Letter_Shareholders.md -> Buffett_1977_Shareholder_Letter.md)
        m = re.match(r'^(\d{4})_Buffett_Letter_Shareholders\.md$', new_name)
        if m:
            new_name = f"Buffett_{m.group(1)}_Shareholder_Letter.md"
            
        # 1b. Remaining ltr/pdf (e.g. 2004ltr.md -> Buffett_2004_Shareholder_Letter.md)
        m = re.match(r'^(\d{4})(ltr|pdf)\.md$', new_name)
        if m:
            new_name = f"Buffett_{m.group(1)}_Shareholder_Letter.md"
            
        # 2. Buffett Annual Meetings (e.g., Buffett_1994_Morning_Session.md -> Buffett_1994_Annual_Meeting_Morning.md)
        new_name = re.sub(r'^Buffett_(\d{4})_(Morning|Afternoon)_Session\.md$', r'Buffett_\1_Annual_Meeting_\2.md', new_name)
        
        # 3. Value Investing prefix removal and formatting for Munger
        if new_name.startswith("value Investing_"):
            new_name = new_name.replace("value Investing_", "")
            
            # Extract year
            year_m = re.search(r'(199\d|20[0-2]\d)', new_name)
            year = year_m.group(1) if year_m else "Unknown"
            
            # Clean title
            title = new_name.replace(year, "").replace("-", "_").replace("__", "_").replace(".md", "").strip("_")
            title = re.sub(r'[^A-Za-z0-9_]', '', title)
            
            new_name = f"Munger_{year}_{title}.md"
            
        # 4. Howard Marks
        if new_name.startswith("Howard_Marks_"):
            new_name = new_name.replace("Howard_Marks_", "Marks_")
            
        # 5. Munger specific cleanups
        if new_name == "1994_Munger_Speech_2011.md":
            new_name = "Munger_1994_Speech.md"
        if "Munger_Speech_" in new_name:
            new_name = new_name.replace("Munger_Speech_", "Munger_")
            
        # 6. Damodaran
        if "Aswath Damodaran" in new_name:
            title = new_name.replace("Aswath Damodaran", "").replace(".md", "").replace(" ", "_").strip("_")
            new_name = f"Damodaran_Unknown_{title}.md"
            
        # 7. Books
        if "The Little Book of Valuation" in new_name:
            new_name = "Book_Unknown_The_Little_Book_of_Valuation.md"
        if "The Outsiders" in new_name:
            new_name = "Book_Unknown_The_Outsiders.md"
        if "Warren Buffett Speaks" in new_name:
            new_name = "Book_Unknown_Warren_Buffett_Speaks.md"
            
        # 8. Clean up extra underscores and formatting
        new_name = re.sub(r'_+', '_', new_name)
        new_name = new_name.replace("_.md", ".md")
        
        if old_name != new_name:
            # Handle potential destination collision
            dest_path = f.parent / new_name
            if dest_path.exists():
                # If destination already exists, we have another duplicate. Just delete the old one.
                print(f"Duplicate found upon rename, deleting: {old_name}")
                f.unlink()
            else:
                f.rename(dest_path)
                rename_count += 1
                
    print(f"\nSuccessfully renamed {rename_count} files to unified format.")
    
if __name__ == "__main__":
    normalize_filenames()
