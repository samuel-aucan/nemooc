"""QSS base para la shell Qt."""

from __future__ import annotations

from app_qt.theme.tokens import TOKENS


def build_app_stylesheet() -> str:
    """Retorna la hoja de estilos principal de la app Qt."""
    t = TOKENS
    return f"""
    QWidget {{
        color: {t["text"]};
        font-family: "Segoe UI";
        font-size: {t["font_base"]}px;
    }}

    QLabel {{
        background: transparent;
    }}

    QMainWindow, QFrame#AppShell, QFrame#ContentSurface {{
        background-color: {t["bg_app"]};
    }}

    QFrame#TopBar {{
        background-color: transparent;
    }}

    QFrame#Sidebar {{
        background-color: {t["bg_panel_alt"]};
        border-right: 1px solid {t["border_soft"]};
    }}

    QFrame#SidebarSection, QFrame#PageCard, QFrame#StatusCard {{
        background-color: {t["bg_panel"]};
        border: 1px solid {t["border"]};
        border-radius: {t["radius_md"]}px;
    }}

    QFrame#InsetCard {{
        background-color: {t["bg_card"]};
        border: 1px solid {t["border_soft"]};
        border-radius: {t["radius_md"]}px;
    }}

    QFrame#DetailField {{
        background-color: {t["bg_card"]};
        border: 1px solid {t["border_soft"]};
        border-radius: {t["radius_sm"]}px;
    }}

    QLabel#BrandTitle {{
        font-size: 20px;
        font-weight: 700;
        color: {t["text"]};
    }}

    QLabel#BrandHero {{
        font-size: 14px;
        font-weight: 700;
        color: {t["text"]};
    }}

    QLabel#BrandSubtitle {{
        font-size: {t["font_base"]}px;
        color: {t["text_muted"]};
    }}

    QLabel#SectionEyebrow {{
        font-size: {t["font_small"]}px;
        color: {t["text_soft"]};
        text-transform: uppercase;
        font-weight: 600;
    }}

    QLabel#PageTitle {{
        font-size: {t["font_large"]}px;
        font-weight: 700;
        color: {t["text"]};
    }}

    QLabel#PageSubtitle {{
        font-size: {t["font_base"]}px;
        color: {t["text_muted"]};
    }}

    QLabel#CardTitle {{
        font-size: 13px;
        font-weight: 700;
        color: {t["text"]};
    }}

    QLabel#CardBody {{
        font-size: {t["font_base"]}px;
        color: {t["text_muted"]};
    }}

    QLabel#FieldValue {{
        font-size: 12px;
        font-weight: 600;
        color: {t["text"]};
    }}

    QLabel#MetricValue {{
        font-size: 17px;
        font-weight: 700;
        color: {t["text"]};
    }}

    QLabel#MetricCaption {{
        font-size: {t["font_base"]}px;
        color: {t["text_muted"]};
    }}

    QLabel#Chip {{
        background-color: {t["bg_card"]};
        border: 1px solid {t["border"]};
        border-radius: 999px;
        padding: 4px 8px;
        color: {t["text_muted"]};
        font-size: {t["font_small"]}px;
        font-weight: 600;
    }}

    QPushButton {{
        background-color: {t["bg_card"]};
        border: 1px solid {t["border"]};
        border-radius: {t["radius_sm"]}px;
        min-height: {t["control_height"]}px;
        padding: 4px 10px;
        color: {t["text"]};
    }}

    QPushButton:hover {{
        background-color: {t["bg_hover"]};
    }}

    QPushButton:pressed {{
        background-color: {t["bg_active"]};
    }}

    QPushButton#PrimaryButton {{
        background-color: {t["accent"]};
        border-color: {t["accent"]};
        color: #07131C;
        font-weight: 700;
    }}

    QPushButton#PrimaryButton:hover {{
        background-color: {t["accent_soft"]};
        border-color: {t["accent_soft"]};
        color: #E6FCFF;
    }}

    QPushButton[quickActive="true"] {{
        background-color: {t["bg_active"]};
        border-color: {t["accent_soft"]};
        color: {t["accent"]};
        font-weight: 700;
    }}

    QLineEdit, QComboBox, QTextEdit, QDateEdit, QSpinBox {{
        background-color: {t["bg_card"]};
        border: 1px solid {t["border"]};
        border-radius: {t["radius_sm"]}px;
        padding: 5px 8px;
        color: {t["text"]};
        selection-background-color: {t["accent_soft"]};
    }}

    QLineEdit, QComboBox, QDateEdit, QSpinBox {{
        min-height: {t["control_height"]}px;
    }}

    QTextEdit {{
        padding-top: 6px;
        padding-bottom: 6px;
    }}

    QLineEdit:focus, QComboBox:focus, QTextEdit:focus, QDateEdit:focus, QSpinBox:focus {{
        border: 1px solid {t["accent"]};
    }}

    QComboBox::drop-down, QDateEdit::drop-down {{
        border: none;
        width: 18px;
    }}

    QSpinBox::up-button,
    QSpinBox::down-button {{
        width: 16px;
        border: none;
        background: transparent;
    }}

    QComboBox QAbstractItemView {{
        background-color: {t["bg_panel"]};
        border: 1px solid {t["border"]};
        selection-background-color: {t["bg_active"]};
        selection-color: {t["text"]};
        color: {t["text"]};
        outline: 0;
    }}

    QCheckBox {{
        color: {t["text"]};
        spacing: 6px;
    }}

    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border-radius: 4px;
        border: 1px solid {t["border"]};
        background-color: {t["bg_card"]};
    }}

    QCheckBox::indicator:checked {{
        background-color: {t["accent"]};
        border: 1px solid {t["accent"]};
    }}

    QProgressBar {{
        border: 1px solid {t["border"]};
        border-radius: 6px;
        background-color: {t["bg_card"]};
        text-align: center;
        color: {t["text"]};
        min-height: 12px;
    }}

    QProgressBar::chunk {{
        background-color: {t["accent"]};
        border-radius: 5px;
    }}

    QPushButton#NavButton {{
        text-align: left;
        padding: 6px 12px;
        border-radius: 10px;
        background-color: transparent;
        border: 1px solid transparent;
        color: {t["text_muted"]};
        font-size: 12px;
    }}

    QPushButton#NavButton:hover {{
        background-color: {t["bg_hover"]};
        border-color: {t["border"]};
        color: {t["text"]};
    }}

    QPushButton#NavButton[active="true"] {{
        background-color: {t["bg_active"]};
        border-color: {t["accent_soft"]};
        color: {t["accent"]};
        font-weight: 600;
    }}

    QStatusBar {{
        background-color: {t["bg_panel_alt"]};
        border-top: 1px solid {t["border_soft"]};
        color: {t["text_muted"]};
    }}

    QStatusBar::item {{
        border: none;
    }}

    QListWidget, QListView {{
        background-color: {t["bg_card"]};
        border: 1px solid {t["border"]};
        border-radius: {t["radius_sm"]}px;
        outline: 0;
    }}

    QListWidget::item, QListView::item {{
        padding: 5px 8px;
        border-bottom: 1px solid {t["border_soft"]};
    }}

    QListWidget::item:selected, QListView::item:selected {{
        background-color: {t["bg_active"]};
        color: {t["text"]};
    }}

    QSplitter::handle {{
        background-color: {t["bg_panel_alt"]};
    }}

    QSplitter::handle:hover {{
        background-color: {t["border"]};
    }}

    QScrollBar:vertical {{
        background: {t["bg_panel_alt"]};
        width: 10px;
        margin: 2px;
    }}

    QScrollBar::handle:vertical {{
        background: {t["border"]};
        border-radius: 5px;
        min-height: 22px;
    }}

    QScrollBar::handle:vertical:hover {{
        background: {t["text_soft"]};
    }}

    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical,
    QScrollBar::add-page:vertical,
    QScrollBar::sub-page:vertical {{
        height: 0px;
        background: transparent;
    }}

    QScrollBar:horizontal {{
        background: {t["bg_panel_alt"]};
        height: 10px;
        margin: 2px;
    }}

    QScrollBar::handle:horizontal {{
        background: {t["border"]};
        border-radius: 5px;
        min-width: 22px;
    }}

    QScrollBar::handle:horizontal:hover {{
        background: {t["text_soft"]};
    }}

    QScrollBar::add-line:horizontal,
    QScrollBar::sub-line:horizontal,
    QScrollBar::add-page:horizontal,
    QScrollBar::sub-page:horizontal {{
        width: 0px;
        background: transparent;
    }}
    """
