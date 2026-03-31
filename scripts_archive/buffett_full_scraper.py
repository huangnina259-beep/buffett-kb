"""
完整提取Warren Buffett Annual Meeting的文字记录
直接爬取网页完整内容，不进行任何删减
"""
import requests
from bs4 import BeautifulSoup
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_CENTER
import shutil
import os
import re

def extract_full_transcript(url):
    """提取完整的文字记录，不进行任何删减"""
    print(f"Fetching URL: {url}")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.encoding = 'utf-8'
        response.raise_for_status()
        print(f"Successfully fetched, status code: {response.status_code}")

        soup = BeautifulSoup(response.content, 'html.parser')

        # 移除不需要的标签
        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'iframe', 'noscript']):
            tag.decompose()

        # 尝试多种方法找到transcript内容
        transcript_content = None

        # 方法1: 查找包含transcript的div
        transcript_divs = soup.find_all('div', class_=re.compile(r'transcript|content|article|entry', re.I))
        if transcript_divs:
            print(f"Found {len(transcript_divs)} possible transcript containers")
            # 选择内容最长的div
            transcript_content = max(transcript_divs, key=lambda x: len(x.get_text()))

        # 方法2: 查找main或article标签
        if not transcript_content:
            transcript_content = soup.find('main') or soup.find('article')

        # 方法3: 查找包含大量文本的div
        if not transcript_content:
            all_divs = soup.find_all('div')
            # 找文本内容最多的div
            if all_divs:
                transcript_content = max(all_divs, key=lambda x: len(x.get_text()))

        if transcript_content:
            # 提取所有段落和文本
            full_text = []

            # 保留标题结构
            for element in transcript_content.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'div', 'span']):
                text = element.get_text(separator=' ', strip=True)
                if text and len(text) > 1:  # 确保不是空文本
                    # 根据标签类型添加标记
                    if element.name in ['h1', 'h2', 'h3']:
                        full_text.append(f"\n{'='*80}\n{text}\n{'='*80}\n")
                    else:
                        full_text.append(text)

            result = '\n\n'.join(full_text)
            print(f"Extraction complete, total characters: {len(result)}")
            return result
        else:
            print("Warning: transcript content area not found")
            # 如果找不到特定区域，返回整个body的文本
            body = soup.find('body')
            if body:
                result = body.get_text(separator='\n', strip=True)
                print(f"Using full body content, total characters: {len(result)}")
                return result

        return None

    except Exception as e:
        print(f"提取失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def clean_text_for_pdf(text):
    """清理文本以便PDF生成"""
    if not text:
        return ""

    # 替换特殊字符
    text = text.replace('\u2019', "'")  # 右单引号
    text = text.replace('\u2018', "'")  # 左单引号
    text = text.replace('\u201c', '"')  # 左双引号
    text = text.replace('\u201d', '"')  # 右双引号
    text = text.replace('\u2013', '-')  # en dash
    text = text.replace('\u2014', '--') # em dash
    text = text.replace('\u2026', '...')  # 省略号
    text = text.replace('\u00a0', ' ')  # 非断空格

    # 移除过多的空行
    lines = text.split('\n')
    cleaned_lines = []
    prev_empty = False

    for line in lines:
        line = line.strip()
        if line:
            cleaned_lines.append(line)
            prev_empty = False
        elif not prev_empty:
            cleaned_lines.append('')
            prev_empty = True

    return '\n'.join(cleaned_lines)

def save_as_txt(text, output_path):
    """保存为TXT文件（备份）"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(text)
    print(f"TXT文件已保存: {output_path}")

def save_as_pdf(text, output_path, title="Berkshire Hathaway Annual Meeting Transcript"):
    """保存为PDF文件"""
    if not text:
        print("错误: 没有内容可保存")
        return False

    print(f"开始生成PDF: {output_path}")

    try:
        # 创建PDF
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=50,
            leftMargin=50,
            topMargin=50,
            bottomMargin=30,
        )

        # 样式
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            leading=20,
            textColor='#000000',
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=12,
            leading=16,
            spaceAfter=10,
            spaceBefore=10,
            fontName='Helvetica-Bold'
        )

        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['BodyText'],
            fontSize=9,
            leading=12,
            spaceAfter=6,
            alignment=TA_LEFT,
            fontName='Helvetica',
        )

        # 构建内容
        story = []

        # 添加标题
        story.append(Paragraph(title, title_style))
        story.append(Spacer(1, 0.3*inch))

        # 处理文本内容
        paragraphs = text.split('\n')

        for para in paragraphs:
            para = para.strip()

            if not para:
                story.append(Spacer(1, 0.1*inch))
                continue

            # 转义XML特殊字符
            para = para.replace('&', '&amp;')
            para = para.replace('<', '&lt;')
            para = para.replace('>', '&gt;')

            # 检测是否是标题（包含等号分隔符）
            if '=' in para and len(para) > 50 and para.count('=') > 20:
                continue  # 跳过分隔符

            # 检测是否是标题（全大写或特定格式）
            if para.isupper() and len(para) < 200:
                story.append(Paragraph(para, heading_style))
            else:
                # 分割过长的段落
                if len(para) > 1000:
                    # 尝试按句子分割
                    sentences = para.split('. ')
                    current_chunk = ""
                    for sentence in sentences:
                        if len(current_chunk) + len(sentence) < 800:
                            current_chunk += sentence + ". "
                        else:
                            if current_chunk:
                                try:
                                    story.append(Paragraph(current_chunk.strip(), body_style))
                                except:
                                    pass
                            current_chunk = sentence + ". "
                    if current_chunk:
                        try:
                            story.append(Paragraph(current_chunk.strip(), body_style))
                        except:
                            pass
                else:
                    try:
                        story.append(Paragraph(para, body_style))
                    except Exception as e:
                        print(f"Warning: 无法添加段落 (长度 {len(para)}): {str(e)[:100]}")
                        # 如果paragraph失败，尝试分割
                        words = para.split()
                        chunk_size = 100
                        for i in range(0, len(words), chunk_size):
                            chunk = ' '.join(words[i:i+chunk_size])
                            try:
                                story.append(Paragraph(chunk, body_style))
                            except:
                                pass

        # 生成PDF
        doc.build(story)
        print(f"PDF生成成功: {output_path}")
        return True

    except Exception as e:
        print(f"生成PDF失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    # 2024年的URL
    url = "https://buffett.cnbc.com/video/2024/05/06/morning-session---2024-meeting.html"
    year = "2024"

    print("="*80)
    print("Warren Buffett Annual Meeting Complete Transcript Extractor")
    print("="*80)

    # 提取完整内容
    full_text = extract_full_transcript(url)

    if not full_text:
        print("错误: 无法提取内容")
        return

    print(f"\nContent extracted successfully!")
    print(f"Total characters: {len(full_text)}")
    print("="*80)

    # 清理文本
    cleaned_text = clean_text_for_pdf(full_text)

    # 临时文件路径
    temp_txt = f"C:\\Users\\jackl\\Buffett_{year}_Full_Transcript.txt"
    temp_pdf = f"C:\\Users\\jackl\\Buffett_{year}_Full_Transcript.pdf"

    # 保存TXT（备份）
    save_as_txt(cleaned_text, temp_txt)

    # 保存PDF
    title = f"Warren Buffett {year} Annual Meeting - Complete Transcript"
    if save_as_pdf(cleaned_text, temp_pdf, title):
        # 移动到目标位置
        target_dir = r"C:\Users\jackl\OneDrive\Documents\私人文件\金融投资\科技学习\Annual meeting"

        try:
            target_pdf = os.path.join(target_dir, f"Buffett_{year}_Full_Transcript.pdf")
            target_txt = os.path.join(target_dir, f"Buffett_{year}_Full_Transcript.txt")

            shutil.copy2(temp_pdf, target_pdf)
            shutil.copy2(temp_txt, target_txt)

            print(f"\n成功! 文件已保存到:")
            print(f"PDF: {target_pdf}")
            print(f"TXT: {target_txt}")

            # 删除临时文件
            os.remove(temp_pdf)
            os.remove(temp_txt)

        except Exception as e:
            print(f"\n警告: 移动文件失败: {e}")
            print(f"文件保存在临时位置:")
            print(f"PDF: {temp_pdf}")
            print(f"TXT: {temp_txt}")

    print("\n" + "="*80)
    print(f"总字符数: {len(cleaned_text)}")
    print(f"总段落数: {len(cleaned_text.split(chr(10)))}")
    print("="*80)

if __name__ == "__main__":
    main()
