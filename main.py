import sys
import shutil
from pathlib import Path

from PySide6.QtGui import (
    QColor, QTextCharFormat, QKeySequence, QTextCursor, QPalette, QFont,
    QIcon, QTextListFormat, QCursor, QShortcut
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTextEdit, QFileDialog, QScrollBar,
    QToolBar, QMessageBox, QToolButton, QWidget, QHBoxLayout, QVBoxLayout,
    QListWidget, QListWidgetItem, QFontComboBox, QSpinBox, QPushButton,
    QSizePolicy, QLabel, QMenu, QAbstractItemView
)
from PySide6.QtCore import Qt, QPoint, QSize, QEvent, QTimer, QStandardPaths


NOTE_EXTENSIONS = {".html", ".htm", ".txt"}


def get_notes_directory():
    app_data = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppDataLocation
    )
    if not app_data:
        raise OSError("Writy could not determine a writable notes folder.")

    directory = Path(app_data) / "Notes"
    directory.mkdir(parents=True, exist_ok=True)
    migration_marker = directory / ".legacy-notes-imported"
    if not migration_marker.exists():
        legacy_directory = (
            Path(sys.executable).parent
            if getattr(sys, "frozen", False)
            else Path(__file__).parent
        )
        if legacy_directory.resolve() != directory.resolve():
            for path in legacy_directory.iterdir():
                if (
                    path.is_file()
                    and path.suffix.lower() in NOTE_EXTENSIONS
                    and not (directory / path.name).exists()
                ):
                    shutil.copy2(path, directory / path.name)
        migration_marker.write_text("done", encoding="utf-8")
    return directory


class SavedNoteRow(QWidget):
    def __init__(self):
        super().__init__()
        self.delete_button = None
        self.leave_timer = QTimer(self)
        self.leave_timer.setSingleShot(True)
        self.leave_timer.setInterval(80)
        self.leave_timer.timeout.connect(self.hide_delete_if_outside)

    def enterEvent(self, event):
        self.leave_timer.stop()
        if self.delete_button:
            self.delete_button.show()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.leave_timer.start()
        super().leaveEvent(event)

    def hide_delete_if_outside(self):
        if (
            self.delete_button
            and not self.rect().contains(self.mapFromGlobal(QCursor.pos()))
        ):
            self.delete_button.hide()


class NotesWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.current_file = None
        self.current_display_name = "Untitled"
        self.list_buttons = {}
        self.notes_directory = get_notes_directory()
        self.setWindowTitle("Untitled")
        self.app_icon = QIcon(str(Path(__file__).with_name("writy.svg")))
        self.setWindowIcon(self.app_icon)

        self.editor = QTextEdit()
        self.default_font = QFont("Segoe UI", 11)
        self.editor.setFont(self.default_font)
        self.editor.document().setDefaultFont(self.default_font)
        self.editor.setAcceptRichText(True)
        self.editor.document().contentsChanged.connect(self.document_changed)
        self.editor.selectionChanged.connect(self.update_selection_toolbar)
        self.menuBar().hide()
        self.create_format_shortcuts()

        self.create_header()
        self.editor.cursorPositionChanged.connect(self.update_list_button_state)
        self.content = QWidget()
        self.content_layout = QHBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        self.create_sidebar()
        self.workspace = QWidget()
        self.workspace_layout = QHBoxLayout(self.workspace)
        self.workspace_layout.setContentsMargins(24, 20, 24, 20)
        self.workspace_layout.setSpacing(0)
        self.workspace_layout.addStretch(1)
        self.editor.setMinimumWidth(0)
        self.editor.setMaximumWidth(900)
        self.editor.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.workspace_layout.addWidget(self.editor, 100)
        self.workspace_layout.addStretch(1)
        self.content_layout.addWidget(self.workspace, 1)
        self.setCentralWidget(self.content)
        self.setup_scrollbar()
        self.selection_toolbar = None
        self.resize(1100, 750)
        self.theme = "light"
        self.apply_theme(self.theme)

        self.statusBar().hide()

    def create_header(self):
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 6, 12, 6)

        menu_button = QToolButton()
        menu_button.setText("\u2630")
        menu_button.setObjectName("hamburger")
        menu_button.setAutoRaise(True)
        menu_button.clicked.connect(self.show_hamburger_menu)
        header_layout.addWidget(menu_button)

        header_layout.addStretch()

        self.font_combo = QFontComboBox()
        self.font_combo.setFixedWidth(150)
        self.font_combo.setCurrentFont(self.editor.currentFont())
        self.font_combo.currentFontChanged.connect(self.change_font)
        header_layout.addWidget(self.font_combo)

        self.font_size = QSpinBox()
        self.font_size.setRange(8, 72)
        self.font_size.setValue(11)
        self.font_size.setFixedWidth(52)
        self.font_size.valueChanged.connect(self.change_font_size)
        header_layout.addWidget(self.font_size)

        self.save_button = QPushButton("Save")
        self.save_button.setObjectName("saveButton")
        self.save_button.clicked.connect(self.save_file)
        header_layout.addWidget(self.save_button)

        self.theme_button = QPushButton()
        self.theme_button.setObjectName("themeButton")
        self.theme_button.clicked.connect(self.toggle_theme)
        header_layout.addWidget(self.theme_button)

        self.addToolBarBreak(Qt.TopToolBarArea)
        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.setAllowedAreas(Qt.TopToolBarArea)
        toolbar.setObjectName("header")
        toolbar.addWidget(header)
        self.addToolBar(Qt.TopToolBarArea, toolbar)

    def create_format_shortcuts(self):
        self.format_shortcuts = []
        for text, shortcut, callback in (
            ("Bold", "Ctrl+B", self.toggle_bold),
            ("Italic", "Ctrl+I", self.toggle_italic),
            ("Underline", "Ctrl+U", self.toggle_underline),
        ):
            key_shortcut = QShortcut(QKeySequence(shortcut), self.editor)
            key_shortcut.setObjectName(f"{text.lower()}Shortcut")
            key_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
            key_shortcut.activated.connect(
                lambda format_action=callback: self.apply_format_shortcut(
                    format_action
                )
            )
            self.format_shortcuts.append(key_shortcut)

    def apply_format_shortcut(self, callback):
        active_window = QApplication.activeWindow()
        if active_window is self:
            focus_widget = QApplication.focusWidget()
            if (
                focus_widget is None
                or (
                    focus_widget is not self.editor
                    and not self.editor.isAncestorOf(focus_widget)
                )
            ):
                return
        elif active_window is not self.selection_toolbar:
            return

        callback()
        if self.selection_toolbar and self.editor.textCursor().hasSelection():
            self.update_format_button_states()

    def show_hamburger_menu(self):
        self.refresh_saved_files()
        self.sidebar.setVisible(not self.sidebar.isVisible())

    def create_sidebar(self):
        self.sidebar = QWidget()
        self.sidebar.setFixedWidth(260)
        self.sidebar.setObjectName("sidebar")
        layout = QVBoxLayout(self.sidebar)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        close_row = QHBoxLayout()
        close_row.addStretch()

        close_button = QPushButton("\u00d7")
        close_button.setObjectName("sidebarClose")
        close_button.setFixedSize(38, 38)
        close_button.setToolTip("Close sidebar")
        close_button.clicked.connect(self.show_hamburger_menu)
        close_row.addWidget(close_button)
        layout.addLayout(close_row)

        logo = QLabel()
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setPixmap(self.app_icon.pixmap(48, 48))
        layout.addWidget(logo, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(16)

        new_button = QPushButton("+ Add new note")
        new_button.setObjectName("sidebarNew")
        new_button.setMinimumHeight(42)
        new_button.clicked.connect(self.new_file)
        layout.addWidget(new_button)

        self.saved_list = QListWidget()
        self.saved_list.setSelectionMode(
            QAbstractItemView.SelectionMode.NoSelection
        )
        self.saved_list.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.saved_list.customContextMenuRequested.connect(
            self.show_saved_note_context_menu
        )
        layout.addWidget(self.saved_list)

        self.content_layout.addWidget(self.sidebar)
        self.sidebar.show()
        self.refresh_saved_files()

    def setup_scrollbar(self):
        self.editor.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.native_scrollbar = self.editor.verticalScrollBar()
        self.overlay_scrollbar = QScrollBar(Qt.Vertical, self.editor.viewport())
        self.overlay_scrollbar.setFixedWidth(5)
        self.overlay_scrollbar.valueChanged.connect(self.native_scrollbar.setValue)
        self.native_scrollbar.valueChanged.connect(self.sync_overlay_scrollbar)
        self.native_scrollbar.rangeChanged.connect(self.update_overlay_scrollbar_range)

        self.scrollbar_timer = QTimer(self)
        self.scrollbar_timer.setSingleShot(True)
        self.scrollbar_timer.setInterval(900)
        self.scrollbar_timer.timeout.connect(self.overlay_scrollbar.hide)

        viewport = self.editor.viewport()
        viewport.setMouseTracking(True)
        viewport.installEventFilter(self)
        self.overlay_scrollbar.installEventFilter(self)
        self.update_overlay_scrollbar_range(
            self.native_scrollbar.minimum(), self.native_scrollbar.maximum()
        )
        self.position_overlay_scrollbar()

    def update_overlay_scrollbar_range(self, minimum, maximum):
        self.overlay_scrollbar.setRange(minimum, maximum)
        self.overlay_scrollbar.setPageStep(self.native_scrollbar.pageStep())
        self.position_overlay_scrollbar()
        if maximum <= minimum:
            self.overlay_scrollbar.hide()

    def sync_overlay_scrollbar(self, value):
        self.overlay_scrollbar.setValue(value)
        self.reveal_scrollbar()

    def position_overlay_scrollbar(self):
        if not hasattr(self, "overlay_scrollbar"):
            return
        viewport = self.editor.viewport()
        self.overlay_scrollbar.setGeometry(
            viewport.width() - 7, 4, 5, max(0, viewport.height() - 8)
        )

    def reveal_scrollbar(self):
        if self.native_scrollbar.maximum() <= self.native_scrollbar.minimum():
            return
        self.position_overlay_scrollbar()
        self.overlay_scrollbar.show()
        self.overlay_scrollbar.raise_()
        self.scrollbar_timer.start()

    def eventFilter(self, watched, event):
        if watched is self.editor.viewport():
            if event.type() == QEvent.Type.Resize:
                self.position_overlay_scrollbar()
            elif event.type() == QEvent.Type.MouseMove:
                if event.position().x() >= self.editor.viewport().width() - 12:
                    self.reveal_scrollbar()
                elif self.overlay_scrollbar.isVisible():
                    self.scrollbar_timer.start()
            elif event.type() == QEvent.Type.Wheel:
                self.reveal_scrollbar()
        elif watched is self.overlay_scrollbar:
            if event.type() in (QEvent.Type.Enter, QEvent.Type.MouseMove):
                self.overlay_scrollbar.show()
                self.overlay_scrollbar.raise_()
                self.scrollbar_timer.stop()
            elif event.type() in (QEvent.Type.Leave, QEvent.Type.MouseButtonRelease):
                self.scrollbar_timer.start()
            elif event.type() == QEvent.Type.MouseButtonPress:
                self.scrollbar_timer.stop()
        return super().eventFilter(watched, event)

    def refresh_saved_files(self):
        self.saved_list.clear()
        saved_files = sorted(
            [
                path for path in self.notes_directory.glob("*")
                if path.is_file() and path.suffix.lower() in NOTE_EXTENSIONS
            ],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for path in saved_files:
            display_name = self.saved_note_name(path)
            item = QListWidgetItem()
            item.setData(Qt.UserRole, str(path))
            item.setSizeHint(QSize(236, 42))
            self.saved_list.addItem(item)
            current_note = bool(
                self.current_file
                and Path(self.current_file).resolve() == path.resolve()
            )

            row = SavedNoteRow()
            row.setObjectName(
                "savedNoteRowActive" if current_note else "savedNoteRow"
            )
            row.setMinimumHeight(42)
            row.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
            row.setMouseTracking(True)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(6, 2, 4, 2)
            row_layout.setSpacing(4)

            open_button = QPushButton(display_name)
            open_button.setObjectName("openSavedNote")
            open_button.setFlat(True)
            open_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            open_button.setToolTip(display_name)
            open_font = QFont("Segoe UI", 10)
            open_font.setUnderline(current_note)
            open_button.setFont(open_font)
            open_button.clicked.connect(
                lambda checked=False, note_path=path: self.open_saved_in_window(note_path)
            )
            row_layout.addWidget(open_button, 1)

            delete_button = QToolButton()
            delete_button.setObjectName("deleteNote")
            delete_button.setText("\U0001f5d1")
            delete_button.setToolTip("Delete note")
            delete_button.setFixedSize(28, 28)
            delete_button.setAutoRaise(True)
            delete_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            delete_button.hide()
            delete_button.clicked.connect(
                lambda checked=False, note_path=path: self.delete_saved_note(note_path)
            )
            row_layout.addWidget(delete_button)
            row.delete_button = delete_button
            self.saved_list.setItemWidget(item, row)
        if not saved_files:
            item = QListWidgetItem("No saved files")
            item.setFlags(Qt.NoItemFlags)
            self.saved_list.addItem(item)

    def saved_note_name(self, path):
        return Path(path).stem

    def show_saved_note_context_menu(self, position):
        item = self.saved_list.itemAt(position)
        if item is None or not item.data(Qt.ItemDataRole.UserRole):
            return

        menu = QMenu(self)
        menu.addAction("Open", lambda: self.open_saved_in_window(item))
        menu.addAction("Delete", lambda: self.delete_saved_note(item))
        menu.exec(self.saved_list.mapToGlobal(position))

    def delete_saved_note(self, item):
        path = (
            item.data(Qt.ItemDataRole.UserRole)
            if isinstance(item, QListWidgetItem)
            else item
        )
        if not path:
            return
        path = Path(path)
        answer = QMessageBox.question(
            self,
            "Delete note",
            f"Permanently delete '{self.saved_note_name(path)}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            path.unlink()
            if (
                self.current_file
                and Path(self.current_file).resolve() == path.resolve()
            ):
                self.editor.clear()
                self.editor.document().setModified(False)
                self.current_file = None
                self.current_display_name = "Untitled"
                self.setWindowTitle("Untitled")
            QTimer.singleShot(0, self.refresh_saved_files)
        except OSError as error:
            QMessageBox.warning(self, "Unable to delete note", str(error))

    def open_saved_in_window(self, item):
        path = (
            item.data(Qt.ItemDataRole.UserRole)
            if isinstance(item, QListWidgetItem)
            else item
        )
        if not path:
            return

        path = Path(path).resolve()
        if (
            self.current_file
            and Path(self.current_file).resolve() == path
        ):
            return

        if not self.open_saved_file(path):
            return
        QTimer.singleShot(0, self.refresh_saved_files)

    def change_font(self, font):
        self.default_font.setFamily(font.family())
        self.editor.document().setDefaultFont(self.default_font)
        fmt = QTextCharFormat()
        fmt.setFontFamilies([font.family()])
        self.editor.mergeCurrentCharFormat(fmt)
        self.editor.setCurrentFont(font)

    def change_font_size(self, size):
        self.default_font.setPointSize(size)
        self.editor.document().setDefaultFont(self.default_font)
        fmt = QTextCharFormat()
        fmt.setFontPointSize(size)

        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            self.editor.mergeCurrentCharFormat(fmt)
        else:
            document_cursor = QTextCursor(self.editor.document())
            document_cursor.select(QTextCursor.SelectionType.Document)
            document_cursor.mergeCharFormat(fmt)
            self.editor.mergeCurrentCharFormat(fmt)

        self.editor.setFontPointSize(size)

    def toggle_list(self, style):
        cursor = self.editor.textCursor()
        start = cursor.document().findBlock(cursor.selectionStart())
        end_cursor = QTextCursor(cursor.document())
        end_cursor.setPosition(cursor.selectionEnd())
        end_block_number = end_cursor.block().blockNumber()

        blocks = []
        block = start
        while block.isValid():
            blocks.append(block)
            if block.blockNumber() == end_block_number:
                break
            block = block.next()

        already_active = bool(blocks) and all(
            block.textList() and block.textList().format().style() == style
            for block in blocks
        )
        if already_active:
            for block in blocks:
                text_list = block.textList()
                if text_list:
                    text_list.remove(block)
        else:
            list_format = QTextListFormat()
            list_format.setStyle(style)
            cursor.createList(list_format)

        self.editor.setTextCursor(cursor)
        self.update_list_button_state()
        self.editor.setFocus(Qt.FocusReason.OtherFocusReason)

    def update_list_button_state(self):
        text_list = self.editor.textCursor().currentList()
        active_style = text_list.format().style() if text_list else None
        for style, button in self.list_buttons.items():
            button.setChecked(active_style == style)

    def toggle_theme(self):
        self.apply_theme("dark" if self.theme == "light" else "light")

    def apply_theme(self, theme):
        self.theme = theme
        app = QApplication.instance()

        if theme == "light":
            palette = QPalette()
            palette.setColor(QPalette.Window, QColor("#f5f5f5"))
            palette.setColor(QPalette.WindowText, QColor("#202020"))
            palette.setColor(QPalette.Base, QColor("#ffffff"))
            palette.setColor(QPalette.Text, QColor("#202020"))
            palette.setColor(QPalette.Button, QColor("#eeeeee"))
            palette.setColor(QPalette.ButtonText, QColor("#202020"))
            palette.setColor(QPalette.Highlight, QColor("#4c78a8"))
            palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
            editor_background = "#ffffff"
            editor_text = "#202020"
            workspace_background = "#f4ecd8"
            page_border = "#e5ddcb"
            scrollbar_color = "#9c9688"
        else:
            palette = QPalette()
            palette.setColor(QPalette.Window, QColor("#242424"))
            palette.setColor(QPalette.WindowText, QColor("#f5f5f5"))
            palette.setColor(QPalette.Base, QColor("#191919"))
            palette.setColor(QPalette.Text, QColor("#f5f5f5"))
            palette.setColor(QPalette.Button, QColor("#303030"))
            palette.setColor(QPalette.ButtonText, QColor("#f5f5f5"))
            palette.setColor(QPalette.Highlight, QColor("#4c78a8"))
            palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
            editor_background = "#111111"
            editor_text = "#f5f5f5"
            workspace_background = "#202020"
            page_border = "#383838"
            scrollbar_color = "#777777"

        app.setPalette(palette)
        self.editor.setStyleSheet(f"""
            QTextEdit {{
                background-color: {editor_background};
                color: {editor_text};
                border: 1px solid {page_border};
                padding: 56px 64px;
                selection-background-color: #4c78a8;
            }}
        """)
        self.workspace.setStyleSheet(
            f"QWidget {{ background-color: {workspace_background}; }}"
        )
        self.overlay_scrollbar.setStyleSheet(f"""
            QScrollBar:vertical {{
                width: 5px;
                background: transparent;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {scrollbar_color};
                border-radius: 2px;
                min-height: 28px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {"#6f6859" if theme == "light" else "#aaaaaa"};
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0;
            }}
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {{
                background: transparent;
            }}
        """)
        sidebar_background = "#202020" if theme == "dark" else "#f4ecd8"
        sidebar_text = "#f5f5f5" if theme == "dark" else "#3d3526"
        sidebar_hover = "#353535" if theme == "dark" else "#e9dfc8"
        active_background = "#3a3b34" if theme == "dark" else "#ddd4bf"
        active_hover = "#45473e" if theme == "dark" else "#d2c8b0"
        delete_color = "#ed7777" if theme == "dark" else "#b23a3a"
        new_note_border = "#555555" if theme == "dark" else "#d7cbae"
        self.sidebar.setStyleSheet(f"""
            QWidget#sidebar {{
                background: {sidebar_background};
                color: {sidebar_text};
                border-right: 1px solid {"#3a3a3a" if theme == "dark" else "#e2d7bd"};
            }}
            QListWidget {{ background: transparent; color: {sidebar_text}; border: none; }}
            QListWidget::item {{ padding: 0; }}
            QPushButton {{ padding: 6px; }}
            QWidget#savedNoteRow {{
                background: transparent;
                border-radius: 6px;
            }}
            QWidget#savedNoteRow:hover {{ background: {sidebar_hover}; }}
            QWidget#savedNoteRowActive {{
                background: {active_background};
                border-radius: 6px;
            }}
            QWidget#savedNoteRowActive:hover {{ background: {active_hover}; }}
            QPushButton#openSavedNote {{
                background: transparent;
                border: none;
                color: {sidebar_text};
                text-align: left;
                font-family: "Segoe UI";
                font-size: 10pt;
                padding: 6px;
            }}
            QToolButton#deleteNote {{
                background: transparent;
                border: none;
                color: {delete_color};
                font-size: 15px;
                padding: 0;
            }}
            QPushButton#sidebarClose {{
                background: transparent;
                border: none;
                border-radius: 19px;
                color: {sidebar_text};
                font-size: 26px;
                padding: 0;
            }}
            QPushButton#sidebarClose:hover {{ background: {sidebar_hover}; }}
            QPushButton#sidebarNew {{
                background: {sidebar_hover};
                border: 1px solid {new_note_border};
                border-radius: 8px;
                color: {sidebar_text};
                font-size: 13px;
                text-align: left;
                padding: 8px 12px;
            }}
            QPushButton#saveButton {{
                border: 1px solid {"#555555" if theme == "dark" else "#d7cbae"};
                border-radius: 5px;
                padding: 4px 10px;
            }}
        """)
        if hasattr(self, "theme_button"):
            self.theme_button.setText("Dark" if theme == "light" else "Light")
            self.theme_button.setToolTip(
                "Switch to dark mode" if theme == "light" else "Switch to light mode"
            )
            border = "#c9bea4" if theme == "light" else "#555555"
            self.theme_button.setStyleSheet(
                f"QPushButton {{ border: 1px solid {border}; border-radius: 5px; "
                "padding: 4px 10px; }}"
            )

    def create_selection_toolbar(self):
        toolbar = QWidget(self.editor)
        toolbar.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        toolbar.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        toolbar.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(5, 4, 5, 4)
        layout.setSpacing(3)

        self.format_buttons = {}
        for name, label, callback in (
            ("bold", "B", self.toggle_bold),
            ("italic", "I", self.toggle_italic),
            ("underline", "U", self.toggle_underline),
        ):
            button = QPushButton(label)
            button.setFixedSize(24, 24)
            button.setCheckable(True)
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            button.setStyleSheet(
                "QPushButton:checked { background: #4c78a8; color: white; border-radius: 4px; }"
            )
            button.clicked.connect(
                lambda checked=False, cb=callback: self.apply_selection_action(
                    lambda: cb(checked)
                )
            )
            layout.addWidget(button)
            self.format_buttons[name] = button

        self.list_buttons = {}
        for label, style, tooltip in (
            ("\u2022", QTextListFormat.Style.ListDisc, "Bulleted list"),
            ("1.", QTextListFormat.Style.ListDecimal, "Numbered list"),
        ):
            button = QPushButton(label)
            button.setToolTip(tooltip)
            button.setFixedSize(26, 24)
            button.setCheckable(True)
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            button.setStyleSheet(
                "QPushButton:checked { background: #4c78a8; color: white; border-radius: 4px; }"
            )
            button.clicked.connect(
                lambda checked=False, list_style=style: self.apply_selection_action(
                    lambda: self.toggle_list(list_style)
                )
            )
            layout.addWidget(button)
            self.list_buttons[style] = button

        for name, color in (
            ("Yellow", "#f2c94c"),
            ("Pink", "#f5a6c9"),
            ("Blue", "#9bc7f2"),
            ("Green", "#a7d7a5"),
        ):
            marker = QPushButton()
            marker.setToolTip(name)
            marker.setFixedSize(18, 18)
            marker.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            marker.clicked.connect(
                lambda checked=False, c=color: self.apply_selection_action(
                    lambda: self.highlight_selection(c)
                )
            )
            marker.setStyleSheet(
                f"QPushButton {{ background-color: {color}; border: 1px solid #777; "
                "min-width: 18px; max-width: 18px; min-height: 18px; "
                "max-height: 18px; border-radius: 9px; margin: 3px; padding: 0; }}"
            )
            layout.addWidget(marker)

        clear = QPushButton("Clear")
        clear.setFixedHeight(24)
        clear.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        clear.clicked.connect(
            lambda checked=False: self.apply_selection_action(self.clear_highlight)
        )
        layout.addWidget(clear)
        toolbar.hide()
        self.selection_toolbar = toolbar

    def apply_selection_action(self, callback):
        callback()
        self.selection_toolbar.hide()
        self.editor.setFocus(Qt.FocusReason.OtherFocusReason)

    def update_selection_toolbar(self):
        if self.selection_toolbar is None:
            self.create_selection_toolbar()
        if not self.editor.textCursor().hasSelection():
            self.selection_toolbar.hide()
            return

        self.update_format_button_states()
        cursor_rect = self.editor.cursorRect(self.editor.textCursor())
        global_point = self.editor.mapToGlobal(cursor_rect.topRight())
        toolbar_width = self.selection_toolbar.sizeHint().width()
        toolbar_height = self.selection_toolbar.sizeHint().height()
        x = global_point.x() + 10
        y = global_point.y() - toolbar_height // 2
        if x + toolbar_width > self.mapToGlobal(self.rect().bottomRight()).x():
            x = cursor_rect.left() + self.editor.mapToGlobal(QPoint()).x() - toolbar_width - 10
        self.selection_toolbar.move(x, y)
        self.selection_toolbar.show()
        self.editor.setFocus(Qt.FocusReason.OtherFocusReason)

    def update_format_button_states(self):
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            probe = QTextCursor(self.editor.document())
            probe.setPosition(cursor.selectionStart())
            probe.movePosition(
                QTextCursor.MoveOperation.NextCharacter,
                QTextCursor.MoveMode.KeepAnchor,
            )
            char_format = probe.charFormat()
        else:
            char_format = self.editor.currentCharFormat()

        self.format_buttons["bold"].setChecked(
            char_format.fontWeight() == QFont.Weight.Bold
        )
        self.format_buttons["italic"].setChecked(char_format.fontItalic())
        self.format_buttons["underline"].setChecked(char_format.fontUnderline())

    def toggle_bold(self, enabled=None):
        if enabled is None:
            enabled = self.editor.fontWeight() != QFont.Weight.Bold
        fmt = QTextCharFormat()
        fmt.setFontWeight(QFont.Weight.Bold if enabled else QFont.Weight.Normal)
        self.editor.mergeCurrentCharFormat(fmt)

    def toggle_italic(self, enabled=None):
        if enabled is None:
            enabled = not self.editor.fontItalic()
        fmt = QTextCharFormat()
        fmt.setFontItalic(enabled)
        self.editor.mergeCurrentCharFormat(fmt)

    def toggle_underline(self, enabled=None):
        if enabled is None:
            enabled = not self.editor.fontUnderline()
        fmt = QTextCharFormat()
        fmt.setFontUnderline(enabled)
        self.editor.mergeCurrentCharFormat(fmt)

    def highlight_selection(self, color="#f2c94c"):
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            fmt = QTextCharFormat()
            fmt.setBackground(QColor(color))
            fmt.setForeground(QColor("#222222"))
            cursor.mergeCharFormat(fmt)

    def clear_highlight(self):
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            fmt = QTextCharFormat()
            fmt.setBackground(Qt.transparent)
            cursor.mergeCharFormat(fmt)

    def toggle_full_screen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def new_file(self):
        if not self.confirm_discard():
            return
        self.editor.clear()
        self.current_file = None
        self.current_display_name = "Untitled"
        self.setWindowTitle("Untitled")
        QTimer.singleShot(0, self.refresh_saved_files)

    def open_file(self):
        if not self.confirm_discard():
            return

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Note",
            str(self.notes_directory),
            "Rich Text (*.html *.htm);;Text Files (*.txt);;All Files (*.*)",
        )
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as file:
                content = file.read()

            if path.lower().endswith((".html", ".htm")):
                self.editor.setHtml(content)
            else:
                self.editor.setPlainText(content)

            self.current_file = path
            self.current_display_name = self.saved_note_name(path)
            self.setWindowTitle(self.current_display_name)
            self.statusBar().showMessage("Note opened")
            self.refresh_saved_files()
        except Exception as error:
            QMessageBox.warning(self, "Unable to open", str(error))

    def open_saved_file(self, path, ask_confirm=True):
        if ask_confirm and not self.confirm_discard():
            return False

        try:
            content = path.read_text(encoding="utf-8")
            if path.suffix.lower() in (".html", ".htm"):
                self.editor.setHtml(content)
            else:
                self.editor.setPlainText(content)

            self.current_file = str(path)
            self.current_display_name = self.saved_note_name(path)
            self.setWindowTitle(self.current_display_name)
            self.editor.document().setModified(False)
            return True
        except Exception as error:
            QMessageBox.warning(self, "Unable to open", str(error))
            return False

    def save_file(self):
        if not self.current_file:
            return self.save_file_as()

        return self.write_file(self.current_file)

    def save_file_as(self):
        path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Save Note",
            str(self.notes_directory / "untitled.html"),
            "Rich Text (*.html);;Text Files (*.txt)",
        )
        if not path:
            return False

        if not path.lower().endswith((".html", ".htm", ".txt")):
            path += ".html" if "Rich Text" in selected_filter else ".txt"

        return self.write_file(path)

    def write_file(self, path):
        try:
            if path.lower().endswith((".html", ".htm")):
                content = self.editor.toHtml()
            else:
                content = self.editor.toPlainText()

            with open(path, "w", encoding="utf-8") as file:
                file.write(content)

            self.current_file = path
            self.current_display_name = self.saved_note_name(path)
            self.setWindowTitle(self.current_display_name)
            self.statusBar().showMessage("Saved")
            self.editor.document().setModified(False)
            self.refresh_saved_files()
            return True
        except Exception as error:
            QMessageBox.warning(self, "Unable to save", str(error))
            return False

    def document_changed(self):
        if self.editor.document().isModified():
            name = self.current_display_name
            self.setWindowTitle(f"* {name}")

    def confirm_discard(self):
        if not self.editor.document().isModified():
            return True

        result = QMessageBox.question(
            self,
            "Unsaved changes",
            "Save changes before continuing?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
        )

        if result == QMessageBox.Save:
            return self.save_file()
        if result == QMessageBox.Discard:
            return True
        return False

    def closeEvent(self, event):
        if self.confirm_discard():
            event.accept()
        else:
            event.ignore()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (
            QEvent.Type.WindowActivate,
            QEvent.Type.WindowDeactivate,
        ):
            QTimer.singleShot(0, self.refresh_saved_files)


app = QApplication(sys.argv)
app.setOrganizationName("Writy")
app.setApplicationName("Writy")
app.setStyle("Fusion")

try:
    window = NotesWindow()
except OSError as error:
    QMessageBox.critical(None, "Unable to open Writy notes", str(error))
    sys.exit(1)
window.showMaximized()
sys.exit(app.exec())