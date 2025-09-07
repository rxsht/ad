import re
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer, LTRect, LTLine, LTCurve

def clean_text_from_pdf(pdf_path):
    """
    Cleans text extracted from a PDF file by removing tables, artifacts, and unnecessary formatting.

    Args:
        pdf_path (str): Path to the PDF file.

    Returns:
        str: Cleaned text.
    """
    def is_table_element(element):
        """Check if an element is likely part of a table."""
        if isinstance(element, (LTLine, LTRect, LTCurve)):
            return True
        if isinstance(element, LTTextContainer):
            text = element.get_text().strip()
            if re.match(r'^\|.*\|$', text):
                return True
            if re.match(r'^\+[-+]+\+$', text):
                return True
            if re.match(r'^[-|+]+$', text):
                return True
        return False

    def is_chapter_heading(text):
        """Determine if the text is a chapter heading."""
        if '..' in text or re.search(r'\s*\.\s*\d+\s*$', text):
            return False
        if len(text.strip()) <= 1:
            return False
        chapter_patterns = [
            r'^\d+\s+[А-Я\s]+$',
            r'^\d+\.\d+\s+[А-Я][а-я\s]+',
            r'^[А-Я\s]+$'
        ]
        return any(re.match(pattern, text.strip()) for pattern in chapter_patterns)

    def clean_text(text):
        """Clean the text by removing artifacts and unnecessary formatting."""
        text = re.sub(r'\n\s*\d+\s*\n', '\n', text)
        text = re.sub(r'(Рисунок|Таблица|рисунок\.|таблица\.)\s*\d+([–—\-]?\d+)*\s*[-–—]?\s*.*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'ПР\s+[А-Я](\s+\([а-я]+\))?', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\b(на рисунке|На рисунке|На рисунках)\b.*?[\n.]*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'Министерство образования Республики Беларусь.*?Минск\s*\d{4}', '', text, flags=re.IGNORECASE)
        text = re.sub(r'Рисунок\s*\d+[-–—]?\s*.*?[A-ZА-Я]', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\b(в таблице|на таблице|в таблицах|на таблицах)\b.*?[\n.]*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'Таблица\s*\d+[-–—]?\s*. *?[A-ZА-Я]', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\[\s*\]', '', text)
        return text.strip()
    
    def clean_applications(text):
        text = re.sub(r'\n\s*\d+\.\d+.*?\.{2,}\s*\d+\s*\n', '', text, flags=re.DOTALL)
        text = re.sub(r'(\n\s*)(СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ)(\s*\n.*?)(?=\Z)', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'\n\s*СОДЕРЖАНИЕ\s*\n.*?(?=\n\s*\d+\.\d+|\n\s*[А-Я]+\s*\n|\Z)'   , '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'\n\s*\d+\.\d+.*?\.{2,}\s*\d+\s*\n', '', text)
        return text

    chapters_content = []
    current_chapter = "Бгиур"
    current_content = []

    for page_layout in extract_pages(pdf_path):
        first_text = ''
        for element in page_layout:
            if isinstance(element, LTTextContainer):
                first_text = element.get_text().strip()
                break 

        if first_text.upper().startswith('СОДЕРЖАНИЕ') or first_text.upper().startswith('МИНИСТЕРСТВО ОБРАЗОВАНИЯ'):
            continue

        for element in page_layout:
            if isinstance(element, LTTextContainer) and not is_table_element(element):
                text = element.get_text()
                if text:
                    if is_chapter_heading(text):
                        if current_chapter and current_content:
                            chapters_content.append({
                                'chapter': current_chapter,
                                'content': clean_text(' '.join(current_content))
                            })
                            current_content = []
                        current_chapter = text
                    else:
                        current_content.append(text)

    if current_content:
        chapters_content.append({
            'chapter': current_chapter,
            'content': clean_text(' '.join(current_content))
        })

    # Combine all content into a single string
    full_cleaned_text = clean_applications('\n\n'.join(f"{chapter['chapter']}\n{chapter['content']}" for chapter in chapters_content))
    return full_cleaned_text

