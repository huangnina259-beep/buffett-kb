"""
Warren Buffett Annual Meeting Transcript Scraper
自动提取并保存Berkshire Hathaway年度股东大会文字记录
"""

import requests
from bs4 import BeautifulSoup
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
import re
from pathlib import Path
import time
from urllib.parse import urljoin

class BuffettMeetingScraper:
    def __init__(self, output_dir):
        self.base_url = "https://buffett.cnbc.com"
        self.annual_meetings_url = "https://buffett.cnbc.com/annual-meetings/"
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

    def get_all_meeting_links(self):
        """获取所有年度股东大会的链接"""
        print(f"正在获取所有年会链接: {self.annual_meetings_url}")
        try:
            response = requests.get(self.annual_meetings_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            meetings = {}
            # 查找所有年会链接 - 根据实际网页结构调整选择器
            links = soup.find_all('a', href=re.compile(r'/(video|annual-meetings)/\d{4}/'))

            for link in links:
                href = link.get('href')
                text = link.get_text(strip=True)

                # 提取年份
                year_match = re.search(r'(\d{4})', href)
                if year_match:
                    year = year_match.group(1)
                    full_url = urljoin(self.base_url, href)

                    if year not in meetings:
                        meetings[year] = []
                    meetings[year].append({
                        'url': full_url,
                        'title': text or f'{year} Meeting'
                    })

            print(f"找到 {len(meetings)} 年的股东大会")
            return meetings

        except Exception as e:
            print(f"获取年会链接失败: {e}")
            return {}

    def extract_transcript(self, url):
        """从单个页面提取文字记录"""
        print(f"正在提取: {url}")
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            # 尝试多种可能的transcript位置
            transcript_text = ""

            # 方法1: 查找transcript容器
            transcript_div = soup.find('div', {'class': re.compile(r'transcript', re.I)})
            if transcript_div:
                transcript_text = transcript_div.get_text(separator='\n', strip=True)

            # 方法2: 查找main content
            if not transcript_text:
                main_content = soup.find('main') or soup.find('article') or soup.find('div', {'class': 'content'})
                if main_content:
                    transcript_text = main_content.get_text(separator='\n', strip=True)

            # 方法3: 整页文本（作为后备）
            if not transcript_text:
                # 移除script和style标签
                for script in soup(['script', 'style', 'nav', 'header', 'footer']):
                    script.decompose()
                transcript_text = soup.get_text(separator='\n', strip=True)

            return self.clean_text(transcript_text)

        except Exception as e:
            print(f"提取失败 {url}: {e}")
            return None

    def clean_text(self, text):
        """清洗文本数据"""
        if not text:
            return ""

        # 移除多余空行
        lines = text.split('\n')
        cleaned_lines = []

        for line in lines:
            line = line.strip()
            if line:
                # 移除多余空格
                line = re.sub(r'\s+', ' ', line)
                cleaned_lines.append(line)

        # 合并成段落
        text = '\n\n'.join(cleaned_lines)

        # 移除连续的空行
        text = re.sub(r'\n{3,}', '\n\n', text)

        return text

    def save_as_pdf(self, text, year, title, session_info=""):
        """保存为PDF文件"""
        if not text:
            print(f"没有内容可保存: {year}")
            return None

        filename = f"Buffett_{year}_Annual_Meeting{session_info}.pdf"
        filepath = self.output_dir / filename

        print(f"正在保存PDF: {filepath}")

        try:
            doc = SimpleDocTemplate(
                str(filepath),
                pagesize=letter,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=18,
            )

            # 创建样式
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                textColor='#000000',
                spaceAfter=30,
                alignment=1  # 居中
            )

            body_style = ParagraphStyle(
                'CustomBody',
                parent=styles['BodyText'],
                fontSize=10,
                leading=14,
                spaceAfter=12,
            )

            # 构建PDF内容
            story = []

            # 标题
            story.append(Paragraph(f"Warren Buffett Annual Meeting {year}", title_style))
            story.append(Paragraph(title, styles['Heading2']))
            story.append(Spacer(1, 0.3*inch))

            # 内容 - 分段处理
            paragraphs = text.split('\n\n')
            for para in paragraphs:
                if para.strip():
                    # 转义特殊字符
                    para_escaped = para.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    try:
                        story.append(Paragraph(para_escaped, body_style))
                    except:
                        # 如果段落太长或有问题，尝试拆分
                        for line in para.split('\n'):
                            if line.strip():
                                line_escaped = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                                story.append(Paragraph(line_escaped, body_style))

            # 生成PDF
            doc.build(story)
            print(f"✓ 成功保存: {filepath}")
            return filepath

        except Exception as e:
            print(f"保存PDF失败 {year}: {e}")
            # 如果PDF失败，保存为TXT作为备份
            txt_path = filepath.with_suffix('.txt')
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(f"Warren Buffett Annual Meeting {year}\n")
                f.write(f"{title}\n\n")
                f.write(text)
            print(f"已保存为TXT备份: {txt_path}")
            return txt_path

    def scrape_specific_year(self, year, url=None):
        """提取特定年份"""
        if not url:
            # 使用默认URL模式
            url = f"https://buffett.cnbc.com/video/{year}/05/06/morning-session---{year}-meeting.htm"

        print(f"\n{'='*60}")
        print(f"开始处理 {year} 年度股东大会")
        print(f"{'='*60}")

        text = self.extract_transcript(url)
        if text:
            self.save_as_pdf(text, year, f"{year} Annual Meeting")
            return True
        return False

    def scrape_all_years(self, start_year=None, end_year=None):
        """批量提取所有年份"""
        meetings = self.get_all_meeting_links()

        if not meetings:
            print("未找到年会链接，尝试使用默认年份范围...")
            meetings = {}
            start = start_year or 1994
            end = end_year or 2024
            for year in range(start, end + 1):
                meetings[str(year)] = [{
                    'url': f"https://buffett.cnbc.com/video/{year}/05/06/morning-session---{year}-meeting.htm",
                    'title': f"{year} Annual Meeting"
                }]

        results = {'success': [], 'failed': []}

        for year in sorted(meetings.keys(), reverse=True):
            year_meetings = meetings[year]

            for i, meeting in enumerate(year_meetings):
                url = meeting['url']
                title = meeting['title']
                session_info = f"_session{i+1}" if len(year_meetings) > 1 else ""

                print(f"\n{'='*60}")
                print(f"处理: {year} - {title}")
                print(f"{'='*60}")

                text = self.extract_transcript(url)

                if text and len(text) > 500:  # 确保有足够内容
                    filepath = self.save_as_pdf(text, year, title, session_info)
                    if filepath:
                        results['success'].append(f"{year} - {title}")
                else:
                    print(f"× 内容不足或提取失败: {year}")
                    results['failed'].append(f"{year} - {title}")

                # 避免请求过快
                time.sleep(2)

        # 打印总结
        print(f"\n{'='*60}")
        print("处理完成！")
        print(f"{'='*60}")
        print(f"成功: {len(results['success'])} 个")
        print(f"失败: {len(results['failed'])} 个")

        if results['failed']:
            print("\n失败列表:")
            for item in results['failed']:
                print(f"  - {item}")

        return results


def main():
    """主函数"""
    # 输出目录
    output_dir = r"C:\Users\jackl\OneDrive\Documents\私人文件\金融投资\科技学习\Annual meeting"

    scraper = BuffettMeetingScraper(output_dir)

    # 选择运行模式
    print("Warren Buffett Annual Meeting Scraper")
    print("="*60)
    print("1. 仅提取2024年")
    print("2. 提取所有年份")
    print("3. 提取指定年份范围")
    print("="*60)

    choice = input("请选择 (1/2/3): ").strip()

    if choice == '1':
        # 仅2024年
        url = "https://buffett.cnbc.com/video/2024/05/06/morning-session---2024-meeting.htm"
        scraper.scrape_specific_year('2024', url)

    elif choice == '2':
        # 所有年份
        scraper.scrape_all_years()

    elif choice == '3':
        # 指定范围
        start = input("起始年份 (如 2020): ").strip()
        end = input("结束年份 (如 2024): ").strip()
        scraper.scrape_all_years(start_year=int(start), end_year=int(end))

    else:
        print("无效选择")

    print(f"\n文件已保存到: {output_dir}")


if __name__ == "__main__":
    main()
