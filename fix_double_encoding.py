import os
import re
from pathlib import Path

def fix_double_encoded_utf8(text):
    """
    Surgically fix double-encoded UTF-8 characters that look like â€” or â□□.
    If a scraper accidentally saved utf-8 bytes as if they were latin-1 characters,
    they appear as \u00e2 \u0080 \u0094 inside python strings.
    We convert them back to bytes using latin-1, then decode as utf-8.
    """
    def replace_match(m):
        try:
            # Revert the characters back to their raw byte values, then decode as actual UTF-8
            return m.group(0).encode('latin-1').decode('utf-8')
        except UnicodeDecodeError:
            # If it's not a valid UTF-8 sequence, leave it alone (it might be a legitimate latin-1 symbol like ©)
            return m.group(0)

    # Find sequences of characters that fall in the upper half of Latin-1
    return re.sub(r'[\x80-\xff]+', replace_match, text)

def fix_all_clean_mds():
    mds_dir = Path(r"C:\Users\jackl\buffett_kb\data\clean_mds")
    structured_dir = Path(r"C:\Users\jackl\OneDrive\Documents\私人文件\金融投资\value Investing\Annual meeting\structured")
    
    files_fixed = 0
    for file_path in list(mds_dir.glob("*.md")) + list(structured_dir.glob("*.md")):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        fixed_content = fix_double_encoded_utf8(content)
        
        if fixed_content != content:
            files_fixed += 1
            # Save it back
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
                
    print(f"\nSuccessfully decoded and fixed mojibake in {files_fixed} files!")

if __name__ == "__main__":
    fix_all_clean_mds()
