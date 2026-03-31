"""
将提取的Warren Buffett 2024年会内容保存为PDF
"""
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import textwrap

# 文本内容
content = """# Morning Session - 2024 Berkshire Hathaway Annual Meeting Transcript

## Speakers
- Warren Buffett (CEO)
- Greg Abel (Vice Chairman)
- Ajit Jain (Vice Chairman)
- Becky Quick (Moderator)
- Various audience members

---

## Section 1: Introductions

WARREN BUFFETT: Opens meeting with thanks to staff and acknowledges directors present, including Greg Abel, Ajit Jain, Howard Buffett, Susan Buffett, Steve Burke, Ken Chenault, and others.

---

## Section 2: Thanks and Acknowledgments

Buffett expresses gratitude to Melissa Shapiro for organizing the event and notes See's Candy brought six tons of product. He mentions selling approximately 2,400 copies of "Poor Charlie's Almanack" and credits Brad Underwood for producing the meeting film, highlighting the effort needed to secure permissions from celebrities featured in archived footage.

---

## Section 3: First Quarter Results and Cash Position

Operating Earnings: Better-than-average quarter reported at $11.2 billion.

Insurance Underwriting: Jain notes first-quarter earnings cannot be multiplied by four due to seasonal variations. He emphasizes Berkshire's primary insurance risk involves Atlantic hurricanes affecting the East Coast. First quarter saw improved underwriting results as no major catastrophes occurred.

Investment Income: Increased substantially due to higher yields and short-term investments responsive to interest rate changes.

Railroad Earnings: Down modestly; car loadings running down.

Energy Company: Improved earnings despite some distortion from special conditions.

Cash Position: Berkshire holds $182 billion in cash and Treasury bills, expected to reach approximately $200 billion by quarter-end.

Historical Context: Buffett references building shareholder equity to $574 billion through retained earnings since taking control of Berkshire Hathaway, except for one dividend declaration (circa 1968-1969).

Comparison: JPMorgan Chase holds $338 billion in shareholders' equity but distributes dividends and repurchases shares differently.

---

## Section 4: Apple Stock Sales and Tax Philosophy

BECKY QUICK: Notes Berkshire sold 115 million Apple shares in the quarter—its largest holding.

Question from Sherman Lam (Malaysia): Asks if Berkshire's views on Apple's economics or attractiveness have changed since 2016 investment.

WARREN BUFFETT RESPONSE:

Views on Apple remain unchanged. He clarifies: "when we own Coca-Cola, American Express, or Apple, we look at that as a business," not mere stock positions.

Buffett explains his investment philosophy evolved after reading Ben Graham's The Intelligent Investor. The book taught him to view stocks as businesses and treat markets as tools serving investors, rather than guides for price movements.

On Tax Rates: Buffett notes Berkshire pays 21% federal tax on Apple gains—lower than historical rates (35% and previously 52%). He argues: "the federal government owns a part of the earnings of the business we make. They don't own the assets, but they own a percentage of the earnings."

Fiscal Outlook: "with the present fiscal policies, I think that something has to give. And I think that higher taxes are quite likely."

Buffett's Position: Berkshire paid over $5 billion in federal taxes last year. He states: "if 800 other company had done the same thing, no other person in the United States would have had to pay a dime of federal taxes." He welcomes appropriate taxation and anticipates rate increases may justify current Apple sales.

---

## Section 5: International Investments and America-First Strategy

Question from Matthew Lai (Hong Kong/China): Asks under what circumstances Berkshire would reinvest in Hong Kong and China companies beyond BYD.

WARREN BUFFETT RESPONSE:

"Our primary investments will always be in the United States." He emphasizes understanding American business environments, rules, weaknesses, and strengths better than foreign economies.

International Companies: Notes American Express and Coca-Cola conduct global business despite Berkshire's domestic focus. Coca-Cola operates in "something maybe like 170 or 180 out of 200" countries.

Japanese Investment: References five-year-old Japan commitment as "extraordinarily compelling," representing a few percent of assets in five major companies. States: "we won't find us making a lot of investments outside the United States."

Charlie Munger's Influence: Recalls two instances where Munger strongly advocated for investments—BYD and Costco. Buffett admits: "I should've been more aggressive" on both but notes success with Costco proved less critical.

Future Approach: "if we do something really big, it's extremely likely to be in the United States." Expresses confidence in Japanese holdings for the long term under future leadership.

---

## Section 6: Berkshire Energy and Regulatory Challenges

Question from Stanley Holmes (Salt Lake City): Concerns state sovereignty movements (particularly Utah) potentially shifting toward public power models, risking Berkshire Hathaway Energy assets through confiscatory policies.

WARREN BUFFETT RESPONSE:

"Utah is actually very likely to treat us fairly" regarding rate structures or potential public power transitions. Cites historical Nebraska example under Senator George Norris.

Investment Position: Berkshire will continue utility investments if receiving reasonable returns, but "we won't do it if we think we're not going to get any return. It'd be kind of crazy."

Climate Costs: Acknowledges some states resist classifying climate-related expenses as utility costs. "Well, believe me, if it was publicly owned, they would've incurred it too."

Capital Discipline: "we're not going to throw good money after bad."

---

GREG ABEL RESPONSE:

Outlines specific challenges across Berkshire utilities:

Iowa (MidAmerican): Over 100 years old; underlying demand doubles into mid-2030s due to AI and data centers. Substantial capital required with proper regulatory compact.

Nevada: Demand triples into late 2030s, requiring "incremental six to ten billion at least of rate base."

Wildfire Litigation: Recent $30 billion claims noted as incremental to existing lawsuits. PacifiCorp required operational culture shifts from "keep power on" mentality to de-energization priorities during fire risk.

Utah as Gold Standard: Recent legislation caps non-economic wildfire damages and created substantial Wildfire Fund. Abel terms this "the gold standard as we go forward."

---

## Section 7: Artificial Intelligence and Fraud Risk

Question from Joe (San Francisco): How does Buffett view technological advances, especially generative AI, affecting traditional industries?

WARREN BUFFETT RESPONSE:

"I don't know anything about AI. But I do...have" awareness of its existence and importance.

Nuclear Parallel: References releasing the nuclear "genie" during WWII. "The power of that genie is what, you know, scares the hell out of me."

AI Comparison: "It's out it's part-way out of the bottle. And it's enormously important, and it's going to be done by somebody."

Personal Experience: Saw realistic deepfake video of himself delivering messages he never made. "my wife or my daughter wouldn't have been able to detect any difference."

Fraud Opportunity: "if you can reproduce images that I can't even tell, that say, I need money...it's going to be the growth industry of all time." Admits: "I practically would send money to myself over in some crazy country."

No Simple Solution: Cannot advise on global AI governance given unresolved nuclear weapons dilemmas.

---

## Section 8: GEICO Data Analytics Development

Question from Ben Knoll (Minneapolis): Todd Combs previously noted Progressive's data advantage over GEICO's marketing strengths. Why delay prioritizing analytics until Combs became CEO?

AJIT JAIN RESPONSE:

Acknowledges GEICO's historical weakness in matching rates to risk through segmentation and pricing. States: "We are trying to still play catch-up. Technology is something that is unfortunately a bottleneck."

Progress: Hired superior data analytics and pricing talent. "by the certainly by the end of '25, we should be able to be along with the best of players when it comes to data analytics."

WARREN BUFFETT RESPONSE:

Confirms rate-to-risk matching's importance across insurance. Notes GEICO's fundamental advantage: "we have lower costs than virtually anybody." Driven underwriting expense ratio below 10%.

Market Position: "it's not in the least a survival question, and it isn't even exactly a profitability thing." March 2024 data showed stable 16 million policyholders with lowest operational costs.

Strategic Direction: GEICO must improve rate-to-risk matching to compete effectively. Low costs previously masked this gap. Todd Combs "has been working intensively at that, and he's made a lot of progress."

---

## Section 9: Trusted Advisors and Charlie Munger

Question from Sebastian Zartorter (Munich, Germany): Who are Buffett's most trusted advisors, and what does he value about them?

WARREN BUFFETT RESPONSE:

Family provides trusted counsel on personal matters, not stock selection. "I trust my children and my wife totally, but that doesn't mean I ask them what stocks to buy."

Charlie Munger's Unique Role: "in terms of managing money, there wasn't anybody better in the world to talk to for, you know, many, many decades, than Charlie."

Essential Qualities: Over decades together, "Charlie...not only never once lied to me ever but he didn't even shape things so that he told half-lies or quarter-lies." This integrity extended across all matters, occasionally causing social friction but providing invaluable partnership.

Life Lesson: "If you don't live a life where you surround yourself, and limit yourself, to people you trust, it won't be much fun."

---

## Section 10: Climate Risk and One-Year Contracts

Question from Meher Bharucha: How does climate change impact insurance risk expansion, and has Berkshire's investment thesis changed?

AJIT JAIN RESPONSE:

Climate risk has become increasingly important. Critical mitigation factor: "our contractual liabilities are limited to a year in most cases." Year-end repricing allows exit decisions.

Pricing Challenge: Prices require substantial increases, but "It is difficult to be very scientific about how much the prices need to go up."

Regulatory Obstacles: State regulators restrict withdrawal and pricing changes. Result: multiple carriers, including Berkshire, declined business in certain states.

Current Trend: "regulators are getting a little more realistic...insurance carriers need to make some kind of a return, a decent return, for us to keep deploying our capital."

Industry Performance: Recent carrier results show record profits. "for the next several months I think the insurance industry, in spite of climate change and in spite of increased risk...it's going to be an OK place to be in."

WARREN BUFFETT PERSPECTIVE:

Climate change increases risk but "in the end it makes our business bigger over time, but not if we...misprice them, we'll also go broke."

Assessment Authority: "I would rather have Ajit assessing this than any thousand underwriters or insurance managers in the world."

Atlantic Hurricane Complexity: Temperature-water relationships don't simply predict hurricane outcomes; frequency, intensity, and path changes complicate analysis.

One-Year Structure Advantage: "we don't have to tell you what's going to happen five years from now or ten years from now."

AJIT JAIN ADDITION: "climate change, much like inflation, done right, can be a friend of the risk bearer."

Historical Example: GEICO grew from 175,000 policies at $40/car ($7 million premium) in 1950 to $40 billion business. "if we'd operated in a non-inflationary world, GEICO would not be a 40-billion-dollar company."

---

## Section 11: Canadian Investment Comfort

Question from Liam (Ontario, Canada, age 27): What are Buffett's views on Canadian economy and bank stocks?

GREG ABEL RESPONSE:

Berkshire maintains significant Canadian operations across multiple entities and invested companies. "We're always looking at making incremental investments there because it's an environment we're very comfortable with."

Economic Alignment: "Canada...moves very closely to the U.S. So, the results we're seeing out of our various businesses...aren't drastically different."

Energy Investments: Makes substantial Alberta investments, consistent with economic growth.

WARREN BUFFETT ADDITION:

"there aren't as many big companies up there as there are in the United States. But when we...see anything that's suggesting an idea that's of a size that would interest [us] here...we don't have any hesitancy about putting big money in Canada."

Recent Example: Financial institution assistance several years ago; Ted Weschler addressed crisis within days after Monday notification.

Current Status: "we do not feel uncomfortable in any way, shape, or form putting our money into Canada. In fact, we're actually looking at one thing now."

Standard Application: Canadian investments must "meet our standards in terms of what we get for our money."

---

## Section 12: Ajit Jain's Legacy and Succession

Question from Mark Blakley (Tulsa, Oklahoma): Who will replace Ajit when succession becomes necessary?

WARREN BUFFETT RESPONSE:

"We won't find another Ajit. But, fortunately, he's a good bit younger than I am."

Institutional Building: "he has created and that...part of it there are certain parts of it that are almost impossible for competitors to imitate." Structure didn't exist pre-1986 and remains unmatched industry-wide.

Business Importance: "insurance is the most important business at Berkshire. Marketable securities are important, but they're not in the class, exactly, as our insurance business."

Long-term Sustainability: "We won't have the same business if Ajit isn't running it. But we'll have a very good business. And, again, that's thanks to Ajit."

Historical Context: Jain arrived in 1986 despite never owning insurance stock or seeing a policy. "here are the keys. And that's worked out very well."

AJIT JAIN RESPONSE:

"nobody is irreplaceable. And we have [Apple CEO} Tim Cook here in the audience, I believe, who has proved that."

Succession Planning: Board reviews succession annually. Jain identifies candidate shortlist and designates specific individual for potential transition.

"Obviously, that could be subject to change, but we take this issue fairly seriously. And I think...it'll be the biggest non-issue of the day. The Earth will keep still keep revolving around the axis."

---

## Section 13: Charlie Munger Reflection

Question from Ange Enunikis: If you had one more day with Charlie, what would you do?

WARREN BUFFETT RESPONSE:

"In effect, I did have one more day." Relationship based on daily happiness with shared activities.

Shared Values: Both enjoyed learning but with different breadths. "Charlie liked learning...he was much broader than I was."

Problem-Solving Bond: "we'd play golf together. We'd play tennis together. We did everything together."

Failure Appreciation: "we had as much fun, perhaps even more, to some extent, with things that failed because then, we really had to work and work our way out of them."

Longevity Surprise: Charlie reached 99.9 years despite "never did a day of exercise, except what was required when he was in the Army."

Partnership Quality: "we never had any doubts about the other person, period."

Age Wisdom: "There's a great advantage in not knowing where you're going what day you're going to die."

Charlie's Perspective: "Just tell me where I'm going to die so I'll never go there."

Intellectual Peak: "I'd never seen anybody that was peaking, you know, at 99." World leaders sought him out at "351 North June Street." Elon Musk and others visited.

Unique Comparison: Only comparison was the Dalai Lama in terms of global interest.

Life Approach: "He lived his life the way he wanted to. And he got to say what he wanted to say. He, like I, loved having a podium."

No Conflict: "I can't remember any time that he was mad at me, or I was mad at him. It just didn't happen."

Learning Together: Daily communication in early years; stayed intellectually engaged. "we did keep learning. And we liked learning together...we tended to be a little smarter, because as the years went by because we had mistakes."

Historical Reading: Charlie "had met all of them, you know, because he...read all their books." Preferred Ben Franklin's work to extended dining.

Life Lesson: "Who do you feel that you'd want to start spending the last day of your life with, and then figure out a way to start meeting them tomorrow."

---

## Section 14: Cyber Insurance Risk Assessment

Question from Karel De Gend (Switzerland): Views on cybersecurity insurance profitability and challenges across retail, small business, large enterprise, and critical infrastructure?

AJIT JAIN RESPONSE:

Market Size: $10 billion+ global market with historically high profitability (approximately 20% profit margins).

Key Concerns:
1. "very difficult to know what is the quantum of losses that can be subject to a single occurrence." Cloud operation failures create massive aggregation risk without worst-case caps.
2. "very difficult to have some sense of...lost cost, or the cost of goods sold."

Historical Data: "losses over the last four of five years...have not been beyond forty cents on the dollar, leaving a decent profit margin."

Problem: Insufficient historical data for confident loss-cost projections.

Berkshire Approach: Operations discouraged from writing cyber insurance. Where required for client retention: "each time you write a cyber insurance policy, you're losing money. We can argue about how much money you're losing, but the mindset should be, you're not making money on it, you're losing money."

Future Outlook: Likely huge business eventually "associated with huge losses...stay away from it right now, until we can have access to some meaningful data."

WARREN BUFFETT RESPONSE:

Insurance fundamentally requires understanding maximum loss potential. 1968 riot-related losses created ambiguity: "if somebody is assassinated in some town and that causes losses at thousands of businesses...do you have one event or do you have a thousand events?"

Cyber Dilemma: "if you're writing 10 million dollars of limit per risk...if that one event turns out to affect a thousand policies...you've written something that, in no way we're getting the proper price for and could break the company."

Industry Temptation: "most people want to be in anything that's fashionable when they write insurance...the agents like it...getting a commission on every policy."

Risk Management Need: Must have leadership understanding aggregation risks exceeding single-event expectations.

Charlie's Warning: "as Charlie would say, it may be rat poison."

---

## Section 15: Renewable Energy and Fossil Fuels

Question from Maria Perenes (Las Vegas, Nevada): Concerns about climate, environmental justice, and clean energy transition speed.

[This section is truncated in the source document]

---

END OF TRANSCRIPT
"""

def create_pdf(output_path):
    """创建PDF文件"""
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=60,
        leftMargin=60,
        topMargin=60,
        bottomMargin=40,
    )

    # 创建样式
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=18,
        textColor='#000000',
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )

    heading_style = ParagraphStyle(
        'Heading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor='#1a1a1a',
        spaceAfter=12,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    )

    body_style = ParagraphStyle(
        'Body',
        parent=styles['BodyText'],
        fontSize=10,
        leading=14,
        spaceAfter=8,
        alignment=TA_LEFT,
    )

    speaker_style = ParagraphStyle(
        'Speaker',
        parent=styles['BodyText'],
        fontSize=10,
        leading=14,
        spaceAfter=8,
        fontName='Helvetica-Bold',
        textColor='#333333'
    )

    # 构建PDF内容
    story = []

    lines = content.split('\n')

    for line in lines:
        line = line.strip()

        if not line or line == '---':
            story.append(Spacer(1, 0.1*inch))
            continue

        # 转义特殊字符
        line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        # 主标题
        if line.startswith('# '):
            text = line[2:]
            story.append(Paragraph(text, title_style))
            story.append(Spacer(1, 0.3*inch))

        # 二级标题
        elif line.startswith('## '):
            text = line[3:]
            story.append(Paragraph(text, heading_style))

        # 加粗说话人
        elif ':' in line and any(name in line for name in ['WARREN BUFFETT', 'GREG ABEL', 'AJIT JAIN', 'BECKY QUICK']):
            parts = line.split(':', 1)
            if len(parts) == 2:
                speaker = parts[0].strip()
                text = parts[1].strip()
                story.append(Paragraph(f"<b>{speaker}:</b> {text}", body_style))
            else:
                story.append(Paragraph(line, body_style))

        # 普通段落
        else:
            try:
                story.append(Paragraph(line, body_style))
            except:
                # 如果段落有问题，直接跳过
                pass

    # 生成PDF
    doc.build(story)
    print(f"PDF generated successfully: {output_path}")

if __name__ == "__main__":
    import os
    import sys
    import shutil

    # Save to temp location first (English path)
    temp_file = "C:\\Users\\jackl\\Buffett_2024_Annual_Meeting_Morning_Session.pdf"
    print("Generating PDF...")

    create_pdf(temp_file)

    # Move to target location
    target_dir = "C:\\Users\\jackl\\OneDrive\\Documents\\私人文件\\金融投资\\科技学习\\Annual meeting"
    target_file = os.path.join(target_dir, "Buffett_2024_Annual_Meeting_Morning_Session.pdf")

    try:
        shutil.move(temp_file, target_file)
        print(f"SUCCESS! PDF saved to: {target_file}")
    except Exception as e:
        print(f"Error moving file: {e}")
        print(f"PDF saved at temp location: {temp_file}")
