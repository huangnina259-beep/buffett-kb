"""
清理和格式化Warren Buffett年会文字记录
"""
import re
import shutil

def clean_transcript(input_file, output_file):
    """清理文字记录格式"""

    with open(input_file, 'r', encoding='utf-8') as f:
        text = f.read()

    # 1. 删除所有 "Sync Video to Paragraph"
    text = text.replace('Sync Video to Paragraph', '')

    # 2. 删除网页导航元素（前面的无用内容）
    # 从第一个真正的章节开始
    if 'Introductions' in text:
        # 保留从 "1. Introductions" 开始的内容
        match = re.search(r'\n1\n\.\nIntroductions\n', text)
        if match:
            text = text[match.start():]

    # 3. 修复分散的章节编号 (数字\n.\n标题 -> 数字. 标题)
    text = re.sub(r'\n(\d+)\n\.\n', r'\n\n## \1. ', text)

    # 4. 识别并格式化说话人
    speakers = ['WARREN BUFFETT', 'GREG ABEL', 'AJIT JAIN', 'BECKY QUICK', 'CHARLIE MUNGER']
    for speaker in speakers:
        # 在说话人前添加空行，说话人名加粗
        text = re.sub(f'({speaker}:)', r'\n\n**\1**', text)

    # 5. 修复特殊字符
    replacements = {
        'â': '"',
        'â': '"',
        'â': "'",
        'â': '-',
        'â¦': '...',
        ' ': ' ',  # 非断空格
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    # 6. 清理多余空行（保留最多2个连续空行）
    text = re.sub(r'\n{4,}', '\n\n\n', text)

    # 7. 移除行尾空格
    lines = text.split('\n')
    lines = [line.rstrip() for line in lines]
    text = '\n'.join(lines)

    # 8. 在主要章节标题后添加分隔线
    text = re.sub(r'(## \d+\. [^\n]+)\n', r'\1\n' + '='*80 + '\n', text)

    # 保存清理后的文本
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(text)

    return text

def save_as_formatted_pdf(text, output_pdf):
    """将清理后的文本保存为格式化的PDF"""
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_LEFT, TA_CENTER

    doc = SimpleDocTemplate(
        output_pdf,
        pagesize=letter,
        leftMargin=60,
        rightMargin=60,
        topMargin=60,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()

    # 自定义样式
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor='#000000',
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )

    chapter_style = ParagraphStyle(
        'Chapter',
        parent=styles['Heading2'],
        fontSize=13,
        leading=16,
        spaceAfter=12,
        spaceBefore=20,
        fontName='Helvetica-Bold',
        textColor='#1a1a1a'
    )

    speaker_style = ParagraphStyle(
        'Speaker',
        parent=styles['BodyText'],
        fontSize=10,
        leading=14,
        spaceAfter=8,
        spaceBefore=12,
        fontName='Helvetica-Bold',
        textColor='#2c3e50'
    )

    body_style = ParagraphStyle(
        'Body',
        parent=styles['BodyText'],
        fontSize=10,
        leading=14,
        spaceAfter=8,
        alignment=TA_LEFT,
    )

    story = []

    # 标题
    story.append(Paragraph('Berkshire Hathaway Annual Meeting 2024', title_style))
    story.append(Paragraph('Complete Transcript - Morning Session', styles['Heading3']))
    story.append(Spacer(1, 0.5*inch))

    # 处理内容
    lines = text.split('\n')
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        if not line:
            i += 1
            continue

        # 章节标题 (## 1. Title)
        if line.startswith('## '):
            chapter_text = line.replace('## ', '')
            story.append(Spacer(1, 0.2*inch))
            try:
                story.append(Paragraph(chapter_text, chapter_style))
            except:
                pass
            i += 1
            continue

        # 分隔线
        if line.startswith('==='):
            story.append(Spacer(1, 0.1*inch))
            i += 1
            continue

        # 说话人 (**WARREN BUFFETT:**)
        if line.startswith('**') and '**' in line[2:]:
            try:
                # 提取说话人和内容
                speaker_match = re.match(r'\*\*([^*]+)\*\*(.*)', line)
                if speaker_match:
                    speaker = speaker_match.group(1)
                    content = speaker_match.group(2).strip()

                    # 说话人名称
                    speaker_text = speaker.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    story.append(Paragraph(f'<b>{speaker_text}</b>', speaker_style))

                    # 说话内容
                    if content:
                        content = content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                        story.append(Paragraph(content, body_style))
            except:
                pass
            i += 1
            continue

        # 普通段落
        try:
            line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            if len(line) > 5:  # 忽略太短的行
                story.append(Paragraph(line, body_style))
        except:
            pass

        i += 1

    # 生成PDF
    doc.build(story)
    print(f'Formatted PDF created: {output_pdf}')

def main():
    input_file = r'C:\Users\jackl\OneDrive\Documents\私人文件\金融投资\科技学习\Annual meeting\Buffett_2024_Complete.txt'
    output_txt = r'C:\Users\jackl\Buffett_2024_Cleaned.txt'
    output_pdf = r'C:\Users\jackl\Buffett_2024_Cleaned.pdf'

    print('Cleaning transcript...')
    cleaned_text = clean_transcript(input_file, output_txt)
    print(f'Cleaned text saved: {output_txt}')
    print(f'Total characters: {len(cleaned_text)}')

    print('\nCreating formatted PDF...')
    save_as_formatted_pdf(cleaned_text, output_pdf)

    # 复制到目标位置
    target_dir = r'C:\Users\jackl\OneDrive\Documents\私人文件\金融投资\科技学习\Annual meeting'

    target_txt = target_dir + r'\Buffett_2024_Cleaned.txt'
    target_pdf = target_dir + r'\Buffett_2024_Cleaned.pdf'

    shutil.copy2(output_txt, target_txt)
    shutil.copy2(output_pdf, target_pdf)

    print(f'\nFiles saved to:')
    print(f'TXT: {target_txt}')
    print(f'PDF: {target_pdf}')
    print('\nDone!')

if __name__ == '__main__':
    main()
