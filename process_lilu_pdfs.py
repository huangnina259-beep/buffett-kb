import os
import re
from pathlib import Path
import pdfplumber

def process_lilu_pdfs():
    source_dir = Path(r"C:\Users\jackl\OneDrive\Documents\私人文件\金融投资\value Investing")
    dest_dir = Path(r"C:\Users\jackl\buffett_kb\data\clean_mds")
    
    # List of Li Lu related files to process
    target_files = [
        "5ef3c7300432b403eb659976_Li Lu on Discussion of Modernization 2016 Final.pdf",
        "5ef3c7300432b4440a659983_Li Lu - Foreword to Chinese Edition of PCA (English translation).pdf",
        "5ef3c7300432b46a7e659977_The Prospect of Value Investing in China English Translation.pdf",
        "5ef3c7300432b4dfa6659979_Li Lu John Jay Award 2012 Speech.pdf",
        "5ef3c7300432b4f82e659975_Discussions About Modernization - A Look at the Future of Sino-US Relations.pdf",
        "5f09347783851614276c3fdb_李录2019年年度书评 2019.11.19.pdf",
        "5f0934f93967fc62fa42c844_李录谈现代化-从人类文明史角度看当今中美关系走向.pdf",
        "5f0935ee7646e6ff74f6d311_李录谈现代化 （全文）大字号.pdf",
        "5f0936c4321954706fa9eca2_价值投资在中国的展望-李录2015-10-23北大演讲.pdf",
        "5f0936f9d3ce59738af03b4d_PCAF_Chinese_2011.pdf",
        "67a4f75703627bd3a927077e_Global Value Investing in Our Era (2024-12-07).pdf",
        "67a4f8e8160103c8a74017a7_全球价值投资与时代2024年12月.pdf"
    ]
    
    for filename in target_files:
        pdf_path = source_dir / filename
        if not pdf_path.exists():
            print(f"File not found: {filename}")
            continue
            
        print(f"Processing: {filename}")
        
        # Clean up the output filename
        clean_name = re.sub(r'^[a-f0-9]+_', '', filename)
        clean_name = clean_name.replace('.pdf', '')
        
        # Extract year if possible
        year_match = re.search(r'(19|20)\d{2}', clean_name)
        year = year_match.group(0) if year_match else "Unknown"
        
        md_filename = f"LiLu_{clean_name.replace(' ', '_')}.md"
        out_path = dest_dir / md_filename
        
        text_content = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        text_content.append(text)
        except Exception as e:
            print(f"Error reading PDF {filename}: {e}")
            continue
            
        full_text = "\n\n".join(text_content)
        
        # Add YAML frontmatter
        frontmatter = f"---\ntitle: {clean_name}\nauthor: Li Lu (李录)\nyear: {year}\nsource: Li Lu Writings\ndoc_type: lilu_article\n---\n\n"
        
        # Basic cleanup
        full_text = re.sub(r'\n{3,}', '\n\n', full_text)
        
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(frontmatter + full_text)
            
        print(f"Saved to: {md_filename}")

if __name__ == "__main__":
    process_lilu_pdfs()
