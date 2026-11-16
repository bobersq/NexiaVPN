"""
NexiaVPN - Application Stylesheet
Dark blue-purple theme
"""

MAIN_STYLE = """
/* ===== Global ===== */
* {
    font-family: 'Segoe UI', Arial, sans-serif;
    outline: none;
}

QMainWindow, QWidget#centralWidget {
    background-color: #0a0e1a;
}

QWidget {
    color: #e2e8f0;
    font-size: 13px;
}

/* ===== Scrollbar ===== */
QScrollBar:vertical {
    background: #0d1117;
    width: 6px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #3b4a6b;
    border-radius: 3px;
    min-height: 20px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

/* ===== Tooltip ===== */
QToolTip {
    background: #1e2535;
    color: #e2e8f0;
    border: 1px solid #3b4a6b;
    border-radius: 4px;
    padding: 4px 8px;
}

/* ===== Menu ===== */
QMenu {
    background: #131929;
    border: 1px solid #2d3f5e;
    border-radius: 8px;
    padding: 4px;
}
QMenu::item {
    padding: 8px 16px;
    border-radius: 4px;
}
QMenu::item:selected {
    background: #2d3f5e;
}

/* ===== Input ===== */
QLineEdit {
    background: #131929;
    border: 1px solid #2d3f5e;
    border-radius: 8px;
    padding: 10px 14px;
    color: #e2e8f0;
    font-size: 13px;
}
QLineEdit:focus {
    border-color: #6366f1;
    background: #161d30;
}
QLineEdit::placeholder {
    color: #4a5568;
}

/* ===== ComboBox ===== */
QComboBox {
    background: #131929;
    border: 1px solid #2d3f5e;
    border-radius: 8px;
    padding: 8px 12px;
    color: #e2e8f0;
    min-width: 120px;
}
QComboBox:hover {
    border-color: #4f5b8f;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid #6b7280;
    width: 0;
    height: 0;
    margin-right: 8px;
}
QComboBox QAbstractItemView {
    background: #131929;
    border: 1px solid #2d3f5e;
    selection-background-color: #2d3f5e;
    color: #e2e8f0;
    border-radius: 8px;
}

/* ===== CheckBox ===== */
QCheckBox {
    spacing: 8px;
    color: #94a3b8;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #2d3f5e;
    border-radius: 4px;
    background: #0a0e1a;
}
QCheckBox::indicator:checked {
    background: #6366f1;
    border-color: #6366f1;
}

/* ===== Spin Box ===== */
QSpinBox {
    background: #131929;
    border: 1px solid #2d3f5e;
    border-radius: 8px;
    padding: 8px 12px;
    color: #e2e8f0;
}
QSpinBox:focus { border-color: #6366f1; }
QSpinBox::up-button, QSpinBox::down-button {
    background: #2d3f5e;
    border: none;
    width: 20px;
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background: #4f5b8f;
}
"""

SERVER_LIST_STYLE = """
QListWidget {
    background: transparent;
    border: none;
    outline: none;
}
QListWidget::item {
    padding: 0;
    margin: 4px 8px;
    border-radius: 10px;
}
QListWidget::item:selected {
    background: transparent;
}
QListWidget::item:hover {
    background: transparent;
}
"""
