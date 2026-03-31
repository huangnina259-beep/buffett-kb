import os
from pathlib import Path

def unify_messy_names():
    mds_dir = Path(r"C:\Users\jackl\buffett_kb\data\clean_mds")
    
    # Explicit mapping for the most messy files
    renames = {
        # Li Lu
        "LiLu_价值投资在中国的展望-李录2015-10-23北大演讲.md": "LiLu_2015_Prospect_of_Value_Investing_in_China_CN.md",
        "LiLu_The_Prospect_of_Value_Investing_in_China_English_Translation.md": "LiLu_2015_Prospect_of_Value_Investing_in_China_EN.md",
        "LiLu_李录2019年年度书评_2019.11.19.md": "LiLu_2019_Annual_Book_Review_CN.md",
        "LiLu_李录谈现代化_（全文）大字号.md": "LiLu_2016_Discussion_on_Modernization_CN.md",
        "LiLu_李录谈现代化-从人类文明史角度看当今中美关系走向.md": "LiLu_2016_Modernization_and_Sino_US_Relations_CN.md",
        "LiLu_Discussions_About_Modernization_-_A_Look_at_the_Future_of_Sino-US_Relations.md": "LiLu_2016_Modernization_and_Sino_US_Relations_EN.md",
        "LiLu_Li_Lu_on_Discussion_of_Modernization_2016_Final.md": "LiLu_2016_Discussion_on_Modernization_EN.md",
        "LiLu_全球价值投资与时代2024年12月.md": "LiLu_2024_Global_Value_Investing_CN.md",
        "LiLu_Global_Value_Investing_in_Our_Era_(2024-12-07).md": "LiLu_2024_Global_Value_Investing_EN.md",
        "LiLu_Li_Lu_-_Foreword_to_Chinese_Edition_of_PCA_(English_translation).md": "LiLu_2011_Foreword_to_PCA_EN.md",
        "LiLu_PCAF_Chinese_2011.md": "LiLu_2011_Foreword_to_PCA_CN.md",
        "LiLu_Li_Lu_John_Jay_Award_2012_Speech.md": "LiLu_2012_John_Jay_Award_Speech.md",

        # Munger
        "Munger_1994_lecture_by_charlie_munger_at_usc_a_lesson_on_elementary_worldly_wisdom_as_it_relates_to_investment.md": "Munger_1994_USC_Worldly_Wisdom.md",
        "Munger_1995_speech_by_charlie_munger_at_harvard_the_psychology_of_human_misjudgment.md": "Munger_1995_Harvard_Psychology_of_Human_Misjudgment.md",
        "Munger_1996_lecture_by_charlie_munger_at_stanford_law_school_worldly_wisdom_revisited_business_what_lawyers_should_know.md": "Munger_1996_Stanford_Worldly_Wisdom_Revisited.md",
        "Munger_1999_wesco_annual_meeting_notes_of_charlie_mungers_remarks_simpleinvestor.md": "Munger_1999_Wesco_Annual_Meeting.md",
        "Munger_2000_wesco_annual_meeting_excerpts_of_charlie_mungers_remarks_outstanding_investor_digest.md": "Munger_2000_Wesco_Annual_Meeting_Excerpts.md",
        "Munger_2000_wesco_annual_meeting_notes_of_charlie_mungers_remarks_whitney_tilson.md": "Munger_2000_Wesco_Annual_Meeting.md",
        "Munger_2001_wesco_annual_meeting_notes_of_charlie_mungers_remarks_whitney_tilson.md": "Munger_2001_Wesco_Annual_Meeting.md",
        "Munger_2002_wesco_annual_meeting_notes_of_charlie_mungers_remarks_whitney_tilson.md": "Munger_2002_Wesco_Annual_Meeting.md",
        "Munger_2003_speech_by_charlie_munger_at_ucsb_academic_economics_strengths_and_faults_after_considering_interdisciplinary.md": "Munger_2003_UCSB_Academic_Economics.md",
        "Munger_2003_wesco_annual_meeting_notes_of_charlie_mungers_remarks_whitney_tilson.md": "Munger_2003_Wesco_Annual_Meeting.md",
        "Munger_2004_wesco_annual_meeting_notes_of_charlie_mungers_remarks_whitney_tilson.md": "Munger_2004_Wesco_Annual_Meeting.md",
        "Munger_2005_wesco_annual_meeting_notes_of_charlie_mungers_remarks_whitney_tilson.md": "Munger_2005_Wesco_Annual_Meeting.md",
        "Munger_2006_wesco_annual_meeting_notes_of_charlie_mungers_remarks_whitney_tilson.md": "Munger_2006_Wesco_Annual_Meeting.md",
        "Munger_2007_commencement_speech_by_charlie_munger_at_usc_gould_school_of_law.md": "Munger_2007_USC_Law_Commencement.md",
        "Munger_2007_wesco_annual_meeting_notes_of_charlie_mungers_remarks_whitney_tilson.md": "Munger_2007_Wesco_Annual_Meeting.md",
        "Munger_2008_wesco_annual_meeting_notes_of_charlie_mungers_remarks_peter_boodell.md": "Munger_2008_Wesco_Annual_Meeting.md",
        "Munger_2009_wesco_annual_meeting_notes_of_charlie_mungers_remarks_peter_boodell.md": "Munger_2009_Wesco_Annual_Meeting.md",
        "Munger_2010_wesco_annual_meeting_notes_of_charlie_mungers_remarks.md": "Munger_2010_Wesco_Annual_Meeting.md",
        "Munger_2011_wesco_annual_meeting_notes_of_charlie_mungers_remarks_the_inoculated_investor.md": "Munger_2011_Wesco_Annual_Meeting.md",
        "Munger_2013_daily_journal_corp_annual_meeting_notes_of_charlie_mungers_remarks.md": "Munger_2013_Daily_Journal_Meeting.md",
        "Munger_2014_daily_journal_corp_annual_meeting_notes_of_charlie_mungers_remarks.md": "Munger_2014_Daily_Journal_Meeting.md",
        "Munger_2015_daily_journal_corp_annual_meeting_notes_of_charlie_mungers_remarks_forbes.md": "Munger_2015_Daily_Journal_Meeting.md",
        "Munger_2016_daily_journal_corp_annual_meeting_transcript_of_charlie_mungers_remarks_latticework_investing.md": "Munger_2016_Daily_Journal_Meeting.md",
        "Munger_2017_a_conversation_with_charlie_munger_at_university_of_michigan_ross.md": "Munger_2017_Michigan_Ross_Conversation.md",
        "Munger_2017_daily_journal_corp_annual_meeting_transcript_of_charlie_mungers_remarks_santangels_review.md": "Munger_2017_Daily_Journal_Meeting_Santangels.md",
        "Munger_2017_daily_journal_corp_post_annual_meeting_fireside_chat_with_charlie_munger_transcript_latticework_investing.md": "Munger_2017_Daily_Journal_Meeting_Fireside_Chat.md",
        "Munger_2018_daily_journal_corp_annual_meeting_transcript_of_charlie_mungers_remarks.md": "Munger_2018_Daily_Journal_Meeting.md",
        "Munger_2019_daily_journal_corp_annual_meeting_transcript_of_charlie_mungers_remarks.md": "Munger_2019_Daily_Journal_Meeting.md",
        "Munger_2020_daily_journal_corp_annual_meeting_transcript_of_charlie_mungers_remarks.md": "Munger_2020_Daily_Journal_Meeting.md",
        "Munger_2022_daily_journal_corp_annual_meeting_transcript_of_charlie_mungers_remarks.md": "Munger_2022_Daily_Journal_Meeting.md",
        "Munger_2023_daily_journal_corp_annual_meeting_transcript_of_charlie_mungers_remarks.md": "Munger_2023_Daily_Journal_Meeting.md",
        "Munger_Unknown_1986_commencement_speech_by_charlie_munger_at_harvard_school_now_harvard_westlake.md": "Munger_1986_Harvard_School_Commencement.md",
        "Munger_Unknown_Lesson_on_Elementary_Worldly_Wisdom_Charlie_Munger.md": "Munger_1994_USC_Worldly_Wisdom_Duplicate.md",
        "Munger_Unknown_mungerspeech_june_95.md": "Munger_1995_Harvard_Psychology_Duplicate.md",
        
        # Books
        "Munger_Unknown_PoorCharliesAlmanack_TheWitandWisdomofCharlesTMungerPDFDrive.md": "Book_2005_Poor_Charlies_Almanack.md",
        "Book_Unknown_The_Little_Book_of_Valuation.md": "Book_2011_The_Little_Book_of_Valuation.md",
        "Book_Unknown_The_Outsiders.md": "Book_2012_The_Outsiders.md",
        "Book_Unknown_Warren_Buffett_Speaks.md": "Book_1997_Warren_Buffett_Speaks.md",
    }
    
    rename_count = 0
    for old_name, new_name in renames.items():
        old_path = mds_dir / old_name
        new_path = mds_dir / new_name
        
        if old_path.exists():
            if not new_path.exists():
                old_path.rename(new_path)
                print(f"Renamed: {old_name} -> {new_name}")
                rename_count += 1
            else:
                # If both exist, the old one is likely a duplicate, let's just delete the messy old one
                print(f"Duplicate found, removing old file: {old_name}")
                old_path.unlink()
                
    print(f"\nSuccessfully processed {rename_count} files.")

if __name__ == "__main__":
    unify_messy_names()