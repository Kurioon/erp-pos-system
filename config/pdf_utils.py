"""Спільна реєстрація кириличного шрифту для PDF (ReportLab).

Стандартний Helvetica не має кириличних гліфів — тому всі PDF
(чеки, замовлення, квитанції ремонту) використовують DejaVu Sans.
"""
import os

from django.conf import settings
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

PDF_FONT = 'DejaVu'


def ensure_pdf_font():
    """Реєструє кириличний шрифт один раз і повертає його назву."""
    if PDF_FONT not in pdfmetrics.getRegisteredFontNames():
        font_path = os.path.join(settings.BASE_DIR, 'assets', 'fonts', 'DejaVuSans.ttf')
        pdfmetrics.registerFont(TTFont(PDF_FONT, font_path))
    return PDF_FONT
