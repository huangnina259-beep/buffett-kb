import os
import re
from pathlib import Path

def clean_transcript(input_path, output_path):
    with open(input_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    cleaned_lines = []
    
    # Noise exact matches to remove completely
    noise_exact = {
        "Sync Video to Paragraph",
        "Back To Top",
        "watch now",
        "VIDEO",
        "Key",
        "Chapters —",
        "See All Chapters",
        "See details on this meeting"
    }

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Skip empty lines
        if not line:
            i += 1
            continue
            
        # Skip exact noise
        if line in noise_exact:
            i += 1
            continue
            
        # Skip timestamps like 02:55:11
        if re.match(r'^\d{2}:\d{2}:\d{2}$', line):
            i += 1
            continue
            
        # Skip metadata header dates like "Mon, May 6 2024 • 12:04 AM EDT"
        if re.match(r'^[A-Z][a-z]{2}, [A-Z][a-z]{2} \d{1,2} \d{4} •', line):
            i += 1
            continue
            
        # Skip "Morning Session - 2024 Meeting" or similar
        if "Session -" in line and "Meeting" in line:
            i += 1
            continue
            
        if line == "Annual Meetings":
            i += 1
            continue

        # Handle fragmented chapter headers: 
        # Line 1: Number (e.g., "3")
        # Line 2: "."
        # Line 3: Title (e.g., "First quarter results and $182B in cash")
        if re.match(r'^\d+$', line) and i + 2 < len(lines):
            next_line = lines[i+1].strip()
            third_line = lines[i+2].strip()
            if next_line == ".":
                # It's a fragmented header! Stitch it together as a Markdown H2
                cleaned_lines.append(f"\n## {line}. {third_line}\n")
                i += 3
                continue

        # Format Speakers (e.g., "WARREN BUFFETT:")
        speaker_match = re.match(r'^([A-Z\s]+):\s*(.*)', line)
        if speaker_match and len(speaker_match.group(1)) > 3:
            speaker = speaker_match.group(1).strip()
            speech = speaker_match.group(2).strip()
            
            # Start a new paragraph for the speaker
            cleaned_lines.append(f"\n**{speaker}:** {speech}")
            i += 1
            continue
            
        # Regular text (append to the current speaker/paragraph)
        if cleaned_lines and not cleaned_lines[-1].endswith('\n\n') and not cleaned_lines[-1].startswith('##'):
            # It's a continuation of the previous paragraph
            # But let's keep it clean by adding a space instead of a hard newline if it belongs to the same thought
            if cleaned_lines[-1].endswith('\n'):
                 cleaned_lines.append(line)
            else:
                 cleaned_lines[-1] = cleaned_lines[-1] + " " + line
        else:
            # Fallback for stray text
            cleaned_lines.append(line)
            
        i += 1

    # Final formatting pass: join lines and ensure proper paragraph spacing
    final_text = "\n\n".join([l.strip() for l in cleaned_lines if l.strip()])
    
    # Fix double spaces or weird artifacts
    final_text = re.sub(r'\n{3,}', '\n\n', final_text)

    # Save to output
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(final_text)

if __name__ == "__main__":
    raw_dir = Path(r"C:\Users\jackl\OneDrive\Documents\私人文件\金融投资\value Investing\Annual meeting\raw")
    out_dir = Path(r"C:\Users\jackl\OneDrive\Documents\私人文件\金融投资\value Investing\Annual meeting\structured")
    
    test_file = raw_dir / "Buffett_2024_Morning_Session.txt"
    out_file = out_dir / "Buffett_2024_Morning_Session.md"
    
    print(f"Cleaning {test_file.name}...")
    clean_transcript(test_file, out_file)
    print(f"Saved to {out_file.name}")