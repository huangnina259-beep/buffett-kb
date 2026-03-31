import os
import re
from pathlib import Path

def advanced_faithful_clean(input_text):
    # 1. Remove non-verbal cues and noise tags
    noise_tags = [
        r'\(Applause\)', r'\(Laughs\)', r'\(Laughter\)', r'\(unintelligible\)', 
        r'\(PH\)', r'\(laughs\)', r'\(laughter\)', r'\(ph\)',
        r'Sync Video to Paragraph', r'Back To Top', r'watch now', r'VIDEO',
        r'See All Chapters', r'See details on this meeting', r'Key Chapters —'
    ]
    for tag in noise_tags:
        input_text = re.sub(tag, '', input_text, flags=re.IGNORECASE)

    # 2. Remove verbal fillers (surgical precision with word boundaries)
    # We remove "you know", "I mean", "sort of", "kind of" when used as fillers
    fillers = [
        r'\byou know,?\s*',
        r'\bI mean,?\s*',
        r'\bsort of\b\s*',
        r'\bkind of\b\s*',
        r'\bwell,\s+',  # Only remove "Well, " at start of clauses
        r'\bOK,\s+',    # Only remove "OK, " at start of clauses
    ]
    for filler in fillers:
        input_text = re.sub(filler, '', input_text, flags=re.IGNORECASE)

    return input_text

def process_all_transcripts():
    raw_dir = Path(r"C:\Users\jackl\OneDrive\Documents\私人文件\金融投资\value Investing\Annual meeting\raw")
    out_dir = Path(r"C:\Users\jackl\OneDrive\Documents\私人文件\金融投资\value Investing\Annual meeting\structured")
    os.makedirs(out_dir, exist_ok=True)

    txt_files = list(raw_dir.glob("*.txt"))
    print(f"Found {len(txt_files)} files to process.")

    for txt_path in txt_files:
        # Extract metadata from filename (e.g., "Buffett_2024_Morning_Session.txt")
        year_match = re.search(r'(\d{4})', txt_path.name)
        year = year_match.group(1) if year_match else "Unknown"
        
        session = "Unknown"
        if "Morning" in txt_path.name: session = "Morning"
        elif "Afternoon" in txt_path.name: session = "Afternoon"

        with open(txt_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        cleaned_lines = []
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue

            # Handle fragmented chapter headers (Number -> Dot -> Title)
            if re.match(r'^\d+$', line) and i + 2 < len(lines):
                next_line = lines[i+1].strip()
                third_line = lines[i+2].strip()
                if next_line == ".":
                    header_title = advanced_faithful_clean(third_line).strip()
                    cleaned_lines.append(f"\n## {line}. {header_title}\n")
                    i += 3
                    continue

            # Apply advanced cleaning to the line
            line = advanced_faithful_clean(line)
            if not line.strip():
                i += 1
                continue

            # Format Speakers
            speaker_match = re.match(r'^([A-Z\s]{3,25}):\s*(.*)', line)
            if speaker_match:
                speaker = speaker_match.group(1).strip()
                speech = speaker_match.group(2).strip()
                cleaned_lines.append(f"\n**{speaker}:** {speech}")
            else:
                # Continuation of previous paragraph
                if cleaned_lines and not cleaned_lines[-1].startswith('\n##'):
                    cleaned_lines[-1] = cleaned_lines[-1].strip() + " " + line.strip()
                else:
                    cleaned_lines.append(line)
            i += 1

        # Add Frontmatter
        frontmatter = f"---\nyear: {year}\nsession: {session}\nsource: Berkshire Annual Meeting\n---\n\n"
        final_text = frontmatter + "\n\n".join([l.strip() for l in cleaned_lines if l.strip()])
        final_text = re.sub(r'\n{3,}', '\n\n', final_text) # Normalize spacing
        
        # Save as Markdown
        out_file = out_dir / txt_path.name.replace(".txt", ".md")
        with open(out_file, 'w', encoding='utf-8') as f:
            f.write(final_text)
        
    print("Batch processing complete!")

if __name__ == "__main__":
    process_all_transcripts()
