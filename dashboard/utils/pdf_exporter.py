from fpdf import FPDF
import re

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'G9 Antigravity Report', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def clean_text_for_pdf(text):
    """Remove emojis and unsupported characters for FPDF."""
    # Remove emojis (characters outside basic multilingual plane might cause issues in FPDF 1.7)
    # This regex removes characters in the emoji ranges
    return re.sub(r'[^\w\s,.\-!?:;()\[\]{}<>@#$%^&*+=/\\|~\'\"가-힣]', '', text)

def create_pdf(markdown_text):
    """Simple PDF generator from markdown text."""
    pdf = PDF()
    pdf.add_page()
    
    # Try to add a Korean font
    font_path = '/System/Library/Fonts/Supplemental/AppleGothic.ttf'
    try:
        pdf.add_font('AppleGothic', '', font_path, uni=True)
        pdf.set_font("AppleGothic", size=12)
    except:
        # Fallback if font not found
        pdf.set_font("Arial", size=12)
    
    # Clean the text first
    cleaned_text = clean_text_for_pdf(markdown_text)
    
    for line in cleaned_text.split('\n'):
        # Handle headers
        if line.startswith('#'):
            if 'AppleGothic' in pdf.fonts:
                pdf.set_font("AppleGothic", '', 14)
            else:
                pdf.set_font("Arial", 'B', 14)
            
            clean_line = line.replace('#', '').strip()
            pdf.multi_cell(0, 10, clean_line)
            
            if 'AppleGothic' in pdf.fonts:
                pdf.set_font("AppleGothic", '', 12)
            else:
                pdf.set_font("Arial", size=12)
        else:
            try:
                if 'AppleGothic' in pdf.fonts:
                    pdf.multi_cell(0, 10, line)
                else:
                    safe_line = line.encode('latin-1', 'replace').decode('latin-1')
                    pdf.multi_cell(0, 10, safe_line)
            except:
                # Last resort
                safe_line = line.encode('latin-1', 'replace').decode('latin-1')
                pdf.multi_cell(0, 10, safe_line)
            
    try:
        return pdf.output(dest='S').encode('latin-1', errors='replace')
    except UnicodeEncodeError:
        # Fallback for severe encoding issues
        return pdf.output(dest='S').encode('utf-8', errors='ignore')
