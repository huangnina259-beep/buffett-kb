import os
import re
from pathlib import Path

def split_oaktree_memos():
    input_path = Path(r"C:\Users\jackl\buffett_kb\data\clean_mds\Oaktree the-complete-collection.md")
    dest_dir = Path(r"C:\Users\jackl\buffett_kb\data\clean_mds")
    
    with open(input_path, 'r', encoding='utf-8') as f:
        text = f.read()

    # Use regex to find each memo start
    # The pattern looks for "Memo to:" and captures everything up to the next "Memo to:" or EOF
    pattern = re.compile(r'(?i)(Memo to:.*?(?=(?:\nMemo to:)|$))', re.DOTALL)
    memos = pattern.findall(text)
    
    print(f"Found {len(memos)} memos.")
    
    if len(memos) == 0:
        return

    # Extract the year from each memo to use in the filename
    # Years are typically found at the end of the memo, or near the beginning. 
    # Let's just find the first occurrence of a year (1990-2025) or extract from the date line
    
    count = 0
    for i, memo_text in enumerate(memos):
        # Skip the table of contents part if it was captured as a memo (the first one usually contains TOC)
        # But looking at the text, the first "Memo to:" is the intro, let's keep it.
        
        # Try to find a title from the "Re:" line
        title_match = re.search(r'(?i)Re:\s*(.*?)\n', memo_text)
        if title_match:
            title = title_match.group(1).strip()
            # Clean title for filename
            clean_title = re.sub(r'[\\/*?:"<>|]', '', title)[:50]
        else:
            clean_title = f"Memo_{i+1}"
            
        # Try to find the year from a date string (e.g., "October 12, 1990")
        year_match = re.search(r'(199\d|20[0-2]\d)', memo_text)
        year = year_match.group(1) if year_match else "Unknown"
        
        filename = f"Howard_Marks_{year}_{clean_title.replace(' ', '_')}.md"
        out_path = dest_dir / filename
        
        # Add YAML frontmatter
        frontmatter = f"---\ntitle: {clean_title}\nauthor: Howard Marks\nyear: {year}\nsource: Oaktree Memos\ndoc_type: howard_marks_memo\n---\n\n"
        
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(frontmatter + memo_text.strip())
            
        count += 1

    print(f"Successfully split {count} memos.")
    
    # Remove the original huge file to avoid duplication
    input_path.unlink()
    print("Deleted the original huge markdown file.")

if __name__ == "__main__":
    split_oaktree_memos()
