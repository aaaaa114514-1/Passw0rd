"""Qt glass interface for P@ssw0rd, backed by the unchanged encrypted vault service."""
from __future__ import annotations

import sys
from pathlib import Path


# PyInstaller unpacks bundled UI resources into _MEIPASS at executable startup.
def resource_path(relative_path: str) -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent)) / relative_path


APP_ICON_PNG = resource_path("icon/89076139-ccdd-471f-9de5-416ae31e3a16.png")
APP_ICON_ICO = resource_path("icon/favicon.ico")

from PySide6.QtCore import QEvent, QPoint, QPropertyAnimation, QEasingCurve, Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QColor, QDesktopServices, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (QApplication, QDialog, QFileDialog, QFormLayout, QFrame, QHBoxLayout,
    QLabel, QLineEdit, QMainWindow, QMenu, QMessageBox, QPushButton, QSplitter, QStackedWidget,
    QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget)

from preferences import PreferencesService
from vault import ValidationError, VaultEntry, VaultError, VaultService

THEMES = {
    "dark": {"text":"#F7FAFF", "muted":"#B2C0D8", "accent":"#38C7FF", "accent2":"#079BD7", "line":"rgba(255,255,255,0.22)", "panel":"rgba(8,18,38,0.62)", "field":"rgba(5,13,30,0.52)", "card":"rgba(255,255,255,0.10)", "hover":"rgba(56,199,255,0.20)", "danger":"#FF7890", "menu":"#16233C", "toast":"rgba(9,43,32,0.90)"},
    "light": {"text":"#17243B", "muted":"#5A6D89", "accent":"#087BD3", "accent2":"#0068B6", "line":"rgba(20,45,78,0.20)", "panel":"rgba(249,252,255,0.70)", "field":"rgba(255,255,255,0.72)", "card":"rgba(255,255,255,0.52)", "hover":"rgba(8,123,211,0.13)", "danger":"#BE2547", "menu":"#FFFFFF", "toast":"rgba(236,255,246,0.94)"},
}
TEXT = {
 "en": {"welcome":"Welcome back","create":"Create your vault","unlock_note":"Unlock your local encrypted vault to continue.","create_note":"Your encryption key stays on this device.","master":"Master password","confirm":"Confirm password","unlock":"Unlock vault","create_vault":"Create encrypted vault","local":"LOCAL ONLY  ·  AES-256-GCM","theme":"Theme","settings":"Settings","lock":"Lock","vault":"LOCAL VAULT","search":"Search accounts","categories":"All categories","new":"＋ New account","account":"ACCOUNT","identity":"IDENTITY","category":"CATEGORY","details":"DETAILS","select":"Select an account","select_note":"Choose an entry to see its identity and secret fields.","none":"Uncategorized","copy":"Copied to clipboard","success":"Success","edit":"Edit","delete":"Delete","cancel":"Cancel","save":"Save account","new_account":"New account","edit_account":"Edit account","notes":"Notes","appearance":"Appearance","language":"Language","background":"Background image","choose":"Choose image","remove":"Remove image","security":"Security","change":"Change master password","apply":"Apply changes","current":"Current password","new_password":"New password","update":"Update password","settings_title":"Settings","settings_note":"Customize the local vault experience.","delete_title":"Delete account","delete_note":"Delete '{0}'? This cannot be undone."},
 "zh": {"welcome":"欢迎回来","create":"创建密码库","unlock_note":"解锁本机加密密码库以继续。","create_note":"加密密钥只保存在此设备上。","master":"主密码","confirm":"确认密码","unlock":"解锁密码库","create_vault":"创建加密密码库","local":"仅本机  ·  AES-256-GCM","theme":"主题","settings":"设置","lock":"锁定","vault":"本地密码库","search":"搜索账户","categories":"全部分类","new":"＋ 新建账户","account":"账户","identity":"身份信息","category":"分类","details":"详情","select":"选择一个账户","select_note":"选择条目后可查看身份与密码字段。","none":"未分类","copy":"已复制到剪贴板","success":"成功","edit":"编辑","delete":"删除","cancel":"取消","save":"保存账户","new_account":"新建账户","edit_account":"编辑账户","notes":"备注","appearance":"外观","language":"语言","background":"背景图片","choose":"选择图片","remove":"移除图片","security":"安全","change":"修改主密码","apply":"应用更改","current":"当前密码","new_password":"新密码","update":"更新密码","settings_title":"设置","settings_note":"自定义本地密码库体验。","delete_title":"删除账户","delete_note":"确认删除“{0}”？此操作无法撤销。"},
}

class Backdrop(QWidget):
    """High quality cover-scaled image, redrawn whenever the window size changes."""
    def __init__(self, image_path: str, theme: str): super().__init__(); self.path=image_path; self.theme=theme; self.source=QPixmap(image_path) if image_path and Path(image_path).exists() else QPixmap()
    def paintEvent(self, event):
        painter=QPainter(self); rect=self.rect()
        if not self.source.isNull():
            scaled=self.source.scaled(rect.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            x=(rect.width()-scaled.width())//2; y=(rect.height()-scaled.height())//2; painter.drawPixmap(x,y,scaled)
            painter.fillRect(rect, QColor(7,16,35,85 if self.theme=="dark" else 42))
        else: painter.fillRect(rect, QColor("#101C33" if self.theme=="dark" else "#E8F2FF"))
        painter.end()

class GlassFrame(QFrame):
    def __init__(self, kind="panel", parent=None): super().__init__(parent); self.setObjectName(kind)

class Toast(QFrame):
    """Top notification with a short downward entrance and upward exit."""
    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("toast")
        self.setFixedHeight(52)
        self.hide()
        row=QHBoxLayout(self); row.setContentsMargins(15,8,18,8); row.setSpacing(10)
        tick=QLabel("✓"); tick.setObjectName("tick"); tick.setAlignment(Qt.AlignmentFlag.AlignCenter); tick.setFixedSize(26,26)
        row.addWidget(tick); self.text=QLabel(); row.addWidget(self.text)
        self.timer=QTimer(self); self.timer.setSingleShot(True); self.timer.timeout.connect(self.hide_animated)
        self.animation=QPropertyAnimation(self,b"pos",self); self.animation.setDuration(230); self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def show_message(self, message):
        self.timer.stop(); self.animation.stop(); self.text.setText(message); self.adjustSize()
        x=(self.parent().width()-self.width())//2
        self.move(x,-self.height()); self.show(); self.raise_()
        self.animation.setStartValue(QPoint(x,-self.height())); self.animation.setEndValue(QPoint(x,20)); self.animation.start()
        self.timer.start(2600)

    def hide_animated(self):
        x=(self.parent().width()-self.width())//2
        self.animation.stop(); self.animation.setStartValue(self.pos()); self.animation.setEndValue(QPoint(x,-self.height()))
        self.animation.finished.connect(self.hide)
        self.animation.start()

class AccountDialog(QDialog):
    def __init__(self, parent, entry=None):
        super().__init__(parent); self.host=parent; self.entry=entry or VaultEntry(id="",title=""); self.saved_entry=None; t=parent.t; self.setWindowTitle(t("new_account") if not entry else t("edit_account")); self.setMinimumWidth(525)
        root=QVBoxLayout(self); root.setContentsMargins(28,26,28,26); root.setSpacing(12); root.addWidget(QLabel(t("new_account") if not entry else t("edit_account"),objectName="dialogTitle"))
        self.fields={}; form=QFormLayout(); form.setSpacing(10)
        labels=[("Name *","title"),("Username","username"),("Phone","phone"),("Email","email"),("Website","url"),("Password","password"),("Category","category"),("Tags","tags")]
        for label,key in labels:
            box=QLineEdit(getattr(self.entry,key)); box.setPlaceholderText(label); box.setClearButtonEnabled(True)
            if key=="password": self.host.add_password_toggle(box)
            self.fields[key]=box; form.addRow(label,box)
        root.addLayout(form); root.addWidget(QLabel(t("notes"),objectName="fieldLabel")); self.notes=QTextEdit(self.entry.notes); self.notes.setFixedHeight(92); self.notes.installEventFilter(self); root.addWidget(self.notes); self.error=QLabel(objectName="error"); root.addWidget(self.error)
        actions=QHBoxLayout(); actions.addStretch(); cancel=QPushButton(t("cancel")); cancel.clicked.connect(self.reject); save=QPushButton(t("save")); save.setObjectName("primary"); save.clicked.connect(self.accept); actions.addWidget(cancel); actions.addWidget(save); root.addLayout(actions); save.setDefault(True); save.setAutoDefault(True)
    def value(self): return VaultEntry(id=self.entry.id,created_at=self.entry.created_at,updated_at=self.entry.updated_at,notes=self.notes.toPlainText(),**{k:v.text() for k,v in self.fields.items()})
    def eventFilter(self,watched,event):
        if watched is self.notes and event.type()==QEvent.Type.KeyPress and event.key() in (Qt.Key.Key_Return,Qt.Key.Key_Enter) and not event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            self.accept();return True
        return super().eventFilter(watched,event)
    def accept(self):
        try: self.saved_entry=self.host.vault.save_entry(self.value()); super().accept()
        except ValidationError as exc: self.error.setText(str(exc))

class SettingsDialog(QDialog):
    def __init__(self, host):
        super().__init__(host); self.host=host; self.setWindowTitle(host.t("settings_title")); self.resize(670,540); self.setMinimumSize(620,500); self.draft_theme=host.preferences.theme; self.draft_language=host.preferences.language; self.draft_background=host.preferences.background_image
        shell=QHBoxLayout(self); shell.setContentsMargins(0,0,0,0); nav=GlassFrame("settingsNav"); nav.setFixedWidth(175); nv=QVBoxLayout(nav); nv.setContentsMargins(18,24,18,18); nv.addWidget(QLabel(host.t("settings_title"),objectName="dialogTitle")); nv.addSpacing(22); self.stack=QStackedWidget();
        for label,index in [(host.t("appearance"),0),(host.t("security"),1)]: b=QPushButton(label); b.clicked.connect(lambda checked=False,i=index:self.stack.setCurrentIndex(i)); nv.addWidget(b)
        nv.addStretch(); shell.addWidget(nav); shell.addWidget(self.stack,1); self.build_appearance(); self.build_security()
    def build_appearance(self):
        p=QWidget(); box=QVBoxLayout(p); box.setContentsMargins(28,27,28,24); box.setSpacing(14)
        box.addWidget(QLabel(self.host.t("appearance"),objectName="dialogTitle")); box.addWidget(QLabel(self.host.t("settings_note"),objectName="muted")); box.addSpacing(7)
        self.theme_value = QLabel(); self.language_value = QLabel(); self.image_value = QLabel()
        self.theme_value.setObjectName("settingValue"); self.language_value.setObjectName("settingValue"); self.image_value.setObjectName("settingValue")
        theme_button=QPushButton(self.host.t("theme")); theme_button.clicked.connect(self.toggle_theme)
        language_button=QPushButton(self.host.t("language")); language_button.clicked.connect(self.toggle_language)
        pick=QPushButton(self.host.t("choose")); pick.clicked.connect(self.choose)
        remove=QPushButton(self.host.t("remove")); remove.clicked.connect(self.remove)
        self._appearance_row(box, self.host.t("theme"), self.theme_value, [theme_button])
        self._appearance_row(box, self.host.t("language"), self.language_value, [language_button])
        self._appearance_row(box, self.host.t("background"), self.image_value, [pick, remove])
        self.update_appearance_values(); box.addStretch(); apply=QPushButton(self.host.t("apply")); apply.setObjectName("primary"); apply.clicked.connect(self.apply); box.addWidget(apply); self.stack.addWidget(p)

    def _appearance_row(self, parent, label, value, actions):
        row=GlassFrame("card"); layout=QHBoxLayout(row); layout.setContentsMargins(14,11,14,11); layout.setSpacing(10)
        labels=QVBoxLayout(); name=QLabel(label); name.setObjectName("fieldLabel"); labels.addWidget(name); labels.addWidget(value); layout.addLayout(labels,1)
        for action in actions: layout.addWidget(action)
        parent.addWidget(row)

    def update_appearance_values(self):
        self.theme_value.setText("Dark" if self.draft_theme=="dark" else "Light")
        self.language_value.setText("English" if self.draft_language=="en" else "中文")
        self.image_value.setText(Path(self.draft_background).name if self.draft_background else "—")

    def toggle_theme(self): self.draft_theme="light" if self.draft_theme=="dark" else "dark"; self.update_appearance_values()
    def toggle_language(self): self.draft_language="zh" if self.draft_language=="en" else "en"; self.update_appearance_values()
    def choose(self):
        name,_=QFileDialog.getOpenFileName(self,self.host.t("choose"),"","Images (*.png *.jpg *.jpeg *.webp *.bmp)")
        if name: self.draft_background=name; self.update_appearance_values()
    def remove(self): self.draft_background=""; self.update_appearance_values()
    def apply(self):
        p=self.host.preferences; p.theme=self.draft_theme; p.language=self.draft_language; p.background_image=self.draft_background; self.host.pref_service.save(p); self.host.apply_theme(); self.host.show_vault(); self.accept()
    def build_security(self):
        p=QWidget(); box=QVBoxLayout(p); box.setContentsMargins(28,27,28,24); box.addWidget(QLabel(self.host.t("security"),objectName="dialogTitle")); box.addWidget(QLabel(self.host.t("change"),objectName="muted")); form=QFormLayout(); self.passwords=[]
        for label in (self.host.t("current"),self.host.t("new_password"),self.host.t("confirm")):
            field=QLineEdit(); self.host.add_password_toggle(field); form.addRow(label,field); self.passwords.append(field)
        box.addLayout(form); self.security_error=QLabel(objectName="error"); box.addWidget(self.security_error); box.addStretch(); update=QPushButton(self.host.t("update")); update.setObjectName("primary"); update.clicked.connect(self.change); update.setDefault(True); update.setAutoDefault(True); box.addWidget(update); self.stack.addWidget(p)
    def change(self):
        current,new,confirm=[x.text() for x in self.passwords]
        if new!=confirm: self.security_error.setText("Passwords do not match." if self.host.preferences.language=="en" else "两次输入的新密码不一致。 "); return
        try: self.host.vault.change_master_password(current,new); self.accept(); self.host.toast(self.host.t("success"))
        except VaultError as exc: self.security_error.setText(str(exc))

class VaultWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.vault=VaultService(); self.pref_service=PreferencesService(); self.preferences=self.pref_service.load(); self.entries={}; self.current=None; self.resize(1220,780); self.setMinimumSize(980,640); self.setWindowIcon(QIcon(str(APP_ICON_ICO))); self.toast_widget=Toast(self); self.apply_theme(); self.show_gate()
    def t(self,key): return TEXT[self.preferences.language][key]
    def c(self): return THEMES[self.preferences.theme]
    def apply_theme(self):
        c = self.c()
        # Microsoft YaHei provides cleaner CJK glyphs; Segoe UI Variable remains the Latin fallback.
        font_family = "Microsoft YaHei UI" if self.preferences.language == "zh" else "Segoe UI Variable"
        QApplication.instance().setFont(QFont(font_family, 10))
        rules = [
            f'QWidget {{ color:{c["text"]}; font-family:"Microsoft YaHei UI","Segoe UI Variable","Segoe UI"; font-size:14px; }}',
            f'#panel {{ background:{c["panel"]}; border:1px solid {c["line"]}; border-radius:18px; }}',
            f'#card {{ background:{c["card"]}; border:1px solid {c["line"]}; border-radius:12px; }}',
            f'#settingsNav {{ background:rgba(20,38,68,0.26); border-right:1px solid {c["line"]}; }}',
            f'QLabel#eyebrow {{ color:{c["accent"]}; font-size:11px; font-weight:700; letter-spacing:1.4px; }}',
            f'QLabel#title {{ color:{"#075B98" if self.preferences.theme == "light" else c["text"]}; font-size:30px; font-weight:700; }}',
            'QLabel#dialogTitle { font-size:24px; font-weight:700; }',
            f'QLabel#muted {{ color:{c["muted"]}; }}', f'QLabel#settingValue {{ color:{c["text"]}; font-weight:600; }}', f'QLabel#error {{ color:{c["danger"]}; }}',
            f'QLineEdit,QTextEdit {{ background:{c["field"]}; border:1px solid {c["line"]}; border-radius:9px; padding:10px; }}',
            f'QLineEdit:focus,QTextEdit:focus {{ border-color:{c["accent"]}; }}',
            f'QPushButton {{ background:rgba(255,255,255,0.11); border:1px solid {c["line"]}; border-radius:9px; padding:9px 14px; font-weight:600; }}',
            f'QPushButton:hover {{ background:{c["hover"]}; border-color:{c["accent"]}; }}',
            f'QPushButton#primary {{ background:{c["accent"]}; color:white; border:0; }}', f'QPushButton#primary:hover {{ background:{c["accent2"]}; }}',
            f'QPushButton#danger {{ color:{c["danger"]}; }}',
            f'#tableShell {{ background:rgba(255,255,255,0.13); border:1px solid {c["line"]}; border-radius:12px; }}',
            'QTableWidget { background:transparent; border:0; gridline-color:transparent; }',
            'QTableWidget::viewport { background:transparent; border-bottom-left-radius:12px; border-bottom-right-radius:12px; }',
            f'QHeaderView {{ background:{"#67CDEA" if self.preferences.theme == "light" else "rgba(255,255,255,0.16)"}; border-top-left-radius:11px; border-top-right-radius:11px; }}',
            f'QHeaderView::section {{ background:{"#67CDEA" if self.preferences.theme == "light" else "rgba(255,255,255,0.16)"}; color:{"#073754" if self.preferences.theme == "light" else c["muted"]}; border:0; border-right:1px solid {"rgba(7,55,84,0.18)" if self.preferences.theme == "light" else c["line"]}; padding:10px; font-size:11px; font-weight:700; }}',
            f'QHeaderView::section:first {{ border-top-left-radius:11px; }} QHeaderView::section:last {{ border-top-right-radius:11px; border-right:0; }}',
            f'QTableWidget::item {{ padding:8px; border:0; border-bottom:1px solid {c["line"]}; outline:0; }}',
            f'QTableWidget::item:selected {{ background:{"rgba(155,225,249,0.92)" if self.preferences.theme == "light" else c["hover"]}; color:{"#073754" if self.preferences.theme == "light" else c["text"]}; }}',
            'QTableWidget::item:focus { outline:none; border:0; }',
            f'QMenu {{ background:{c["menu"]}; border:1px solid {c["line"]}; border-radius:9px; padding:6px; }}',
            'QMenu::item { padding:9px 24px 9px 12px; border-radius:6px; }', f'QMenu::item:selected {{ background:{c["hover"]}; }}',
            f'#toast {{ background:{c["toast"]}; border:1px solid #42D392; border-radius:12px; }}',
            '#tick { background:#22B573; color:white; border-radius:13px; font-size:18px; font-weight:700; }',
            f'QDialog {{ background:{"#101B30" if self.preferences.theme == "dark" else "#F3F8FF"}; }}',
        ]
        QApplication.instance().setStyleSheet("\n".join(rules))
    def backdrop(self): return Backdrop(self.preferences.background_image,self.preferences.theme)
    def clear(self):
        if self.centralWidget(): self.centralWidget().deleteLater()
    def add_password_toggle(self, field):
        field.setEchoMode(QLineEdit.EchoMode.Password)
        action=QAction("◉",field)
        field.addAction(action,QLineEdit.ActionPosition.TrailingPosition)
        action.setToolTip("Show password" if self.preferences.language=="en" else "显示密码")
        def toggle():
            visible=field.echoMode()==QLineEdit.EchoMode.Password
            field.setEchoMode(QLineEdit.EchoMode.Normal if visible else QLineEdit.EchoMode.Password)
            action.setText("◉" if visible else "◌")
            action.setToolTip(("Hide password" if visible else "Show password") if self.preferences.language=="en" else ("隐藏密码" if visible else "显示密码"))
        action.triggered.connect(toggle)
        return action
    def show_gate(self):
        self.clear(); back=self.backdrop(); layout=QVBoxLayout(back); layout.setAlignment(Qt.AlignmentFlag.AlignCenter); panel=GlassFrame(); panel.setMaximumWidth(470); p=QVBoxLayout(panel); p.setContentsMargins(38,36,38,36); p.setSpacing(12); first=not self.vault.is_initialized
        p.addWidget(QLabel("P@SSW0RD",objectName="eyebrow")); p.addWidget(QLabel(self.t("create") if first else self.t("welcome"),objectName="dialogTitle")); note=QLabel(self.t("create_note") if first else self.t("unlock_note"),objectName="muted");note.setWordWrap(True);p.addWidget(note)
        self.gate_pass=QLineEdit();self.gate_pass.setPlaceholderText(self.t("master"));self.add_password_toggle(self.gate_pass);p.addWidget(self.gate_pass);self.gate_confirm=None
        if first: self.gate_confirm=QLineEdit();self.gate_confirm.setPlaceholderText(self.t("confirm"));self.add_password_toggle(self.gate_confirm);p.addWidget(self.gate_confirm)
        self.gate_error=QLabel(objectName="error");p.addWidget(self.gate_error);go=QPushButton(self.t("create_vault") if first else self.t("unlock"));go.setObjectName("primary");go.clicked.connect(lambda:self.unlock(first));go.setDefault(True);go.setAutoDefault(True);p.addWidget(go);p.addWidget(QLabel(self.t("local"),objectName="eyebrow")); layout.addWidget(panel); self.setCentralWidget(back); self.gate_pass.returnPressed.connect(lambda:self.unlock(first));
        if self.gate_confirm: self.gate_confirm.returnPressed.connect(lambda:self.unlock(first))
        self.gate_pass.setFocus()
    def unlock(self,first):
        try:
            if first:
                if self.gate_pass.text()!=self.gate_confirm.text(): raise ValidationError("The two passwords do not match.")
                self.vault.initialize(self.gate_pass.text())
            else:self.vault.unlock(self.gate_pass.text())
            self.show_vault()
        except VaultError as exc:self.gate_error.setText(str(exc))
    def show_vault(self):
        self.clear();self.sort_column=0;self.sort_descending=False;back=self.backdrop();outer=QVBoxLayout(back);outer.setContentsMargins(30,25,30,25);outer.setSpacing(14);header=QHBoxLayout();brand_icon=QLabel();brand_icon.setPixmap(QPixmap(str(APP_ICON_PNG)).scaled(34,34,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation));brand_icon.setFixedSize(36,36);header.addWidget(brand_icon);header.addWidget(QLabel("P@ssw0rd",objectName="title"));header.addWidget(QLabel(self.t("vault"),objectName="eyebrow"));header.addStretch()
        theme_icon=QPushButton("☀" if self.preferences.theme=="dark" else "☾");theme_icon.setFixedWidth(42);theme_icon.setToolTip("Switch to light mode" if self.preferences.theme=="dark" else "Switch to dark mode");theme_icon.clicked.connect(self.toggle_theme);header.addWidget(theme_icon)
        for text,slot in [(self.t("settings"),self.settings),(self.t("lock"),self.lock)]: b=QPushButton(text);b.clicked.connect(slot);header.addWidget(b)
        outer.addLayout(header);glass=GlassFrame();outer.addWidget(glass,1);gl=QVBoxLayout(glass);gl.setContentsMargins(14,14,14,14);split=QSplitter();split.setChildrenCollapsible(False);split.setHandleWidth(14);split.setStyleSheet("QSplitter::handle { background: rgba(255,255,255,0.12); margin: 10px 3px; border-radius:4px; } QSplitter::handle:hover { background: rgba(56,199,255,0.55); }");gl.addWidget(split);left=QWidget();ll=QVBoxLayout(left);tools=QHBoxLayout();self.search=QLineEdit();self.search.setPlaceholderText(self.t("search"));self.search.textChanged.connect(self.refresh);tools.addWidget(self.search,1);self.category=QPushButton(self.t("categories")+"  ▾");self.category.clicked.connect(self.category_menu);tools.addWidget(self.category);new=QPushButton(self.t("new"));new.setObjectName("primary");new.clicked.connect(self.edit);tools.addWidget(new);ll.addLayout(tools)
        table_shell=GlassFrame("tableShell");table_layout=QVBoxLayout(table_shell);table_layout.setContentsMargins(0,0,0,0);self.table=QTableWidget(0,3);self.table.setHorizontalHeaderLabels([self.t("account"),self.t("identity"),self.t("category")]);self.table.verticalHeader().hide();self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows);self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection);self.table.setFocusPolicy(Qt.FocusPolicy.StrongFocus);self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers);self.table.setShowGrid(False);self.table.itemSelectionChanged.connect(self.select);self.table.installEventFilter(self);self.table.horizontalHeader().setStretchLastSection(True);self.table.horizontalHeader().setSectionsClickable(True);self.table.horizontalHeader().sectionClicked.connect(self.sort_by_column);self.table.setColumnWidth(0,230);self.table.setColumnWidth(1,310);table_layout.addWidget(self.table);ll.addWidget(table_shell);split.addWidget(left);self.detail=QWidget();self.detail.setMinimumWidth(320);split.addWidget(self.detail);split.setSizes([780,350]);self.setCentralWidget(back);self.refresh()
    def refresh(self):
        if not self.vault.is_unlocked:return
        selected_id=self.current
        category=self.category.text().replace("  ▾","");all_label=self.t("categories");none_label=self.t("none");self.entries={x.id:x for x in self.vault.list_entries(self.search.text())};rows=[x for x in self.entries.values() if category==all_label or (category==none_label and not x.category) or x.category==category]
        sort_values = (lambda item: item.title, lambda item: item.username or item.email or item.phone, lambda item: item.category)
        rows.sort(key=lambda item: sort_values[self.sort_column](item).casefold(), reverse=self.sort_descending)
        self.table.blockSignals(True);self.table.clearContents();self.table.setRowCount(len(rows))
        selected_row=None
        for r,x in enumerate(rows):
            for col,value in enumerate((x.title,x.username or x.email or x.phone or self.t("none"),x.category or self.t("none"))): item=QTableWidgetItem(value);item.setData(Qt.ItemDataRole.UserRole,x.id);self.table.setItem(r,col,item)
            if x.id==selected_id:selected_row=r
        self.table.clearSelection()
        if selected_row is None:
            self.current=None
        else:
            self.table.selectRow(selected_row)
        self.table.blockSignals(False)
        if self.current:self.detail_view(self.entries[self.current])
        else:self.empty_detail()
    def sort_by_column(self, column):
        if self.sort_column == column:
            self.sort_descending = not self.sort_descending
        else:
            self.sort_column = column
            self.sort_descending = False
        self.refresh()

    def category_menu(self):
        menu=QMenu(self);all_label=self.t("categories");a=QAction(all_label,menu);a.triggered.connect(lambda:self.set_category(all_label));menu.addAction(a)
        entries=self.vault.list_entries()
        if any(not entry.category for entry in entries):
            none=QAction(self.t("none"),menu);none.triggered.connect(lambda:self.set_category(self.t("none")));menu.addAction(none)
        for name in self.vault.categories(): a=QAction(name,menu);a.triggered.connect(lambda checked=False,n=name:self.set_category(n));menu.addAction(a)
        menu.exec(self.category.mapToGlobal(self.category.rect().bottomLeft()))
    def set_category(self,name):self.category.setText(name+"  ▾");self.refresh()
    def select(self):
        rows=self.table.selectedItems()
        if not rows:return
        entry_id=rows[0].data(Qt.ItemDataRole.UserRole)
        if entry_id in self.entries:self.current=entry_id;self.detail_view(self.entries[entry_id])
    def _dispose_layout_item(self,item):
        widget=item.widget()
        if widget:widget.setParent(None);widget.deleteLater();return
        layout=item.layout()
        if layout:
            while layout.count():self._dispose_layout_item(layout.takeAt(0))
            layout.deleteLater()
    def reset_detail(self):
        layout=self.detail.layout()
        if layout:
            while layout.count():self._dispose_layout_item(layout.takeAt(0))
        else:layout=QVBoxLayout(self.detail);layout.setContentsMargins(20,20,20,20);layout.setSpacing(8)
        return layout
    def empty_detail(self):
        box=self.reset_detail();box.addWidget(QLabel(self.t("details"),objectName="eyebrow"));box.addWidget(QLabel(self.t("select"),objectName="dialogTitle"));box.addWidget(QLabel(self.t("select_note"),objectName="muted"));box.addStretch()
    def detail_view(self,x):
        box=self.reset_detail();box.addWidget(QLabel(self.t("details"),objectName="eyebrow"));box.addWidget(QLabel(x.title,objectName="dialogTitle"));box.addWidget(QLabel(" · ".join(filter(None,[x.category,x.tags])) or self.t("none"),objectName="muted"))
        for label,val in [("Username",x.username),("Phone",x.phone),("Email",x.email),("Website",x.url),("Password",x.password)]:
            if val:
                card=GlassFrame("card");row=QHBoxLayout(card);left=QVBoxLayout();left.addWidget(QLabel(label.upper(),objectName="eyebrow"));shown="●"*min(max(len(val),9),20) if label=="Password" else val;left.addWidget(QLabel(shown));row.addLayout(left,1)
                if label=="Website":
                    open_link=QPushButton("↗");open_link.setToolTip("Open website" if self.preferences.language=="en" else "打开网页");open_link.clicked.connect(lambda checked=False,url=val:self.open_website(url));row.addWidget(open_link)
                copy=QPushButton("⧉");copy.setToolTip(label);copy.clicked.connect(lambda checked=False,v=val:self.copy(v));row.addWidget(copy);box.addWidget(card)
        if x.notes:box.addWidget(QLabel(self.t("notes").upper(),objectName="eyebrow"));box.addWidget(QLabel(x.notes,objectName="muted"))
        box.addStretch();actions=QHBoxLayout();edit=QPushButton(self.t("edit"));edit.clicked.connect(lambda:self.edit(x));delete=QPushButton(self.t("delete"));delete.setObjectName("danger");delete.clicked.connect(lambda:self.delete(x));actions.addWidget(edit);actions.addWidget(delete);box.addLayout(actions)
    def toast(self,message):self.toast_widget.show_message(message)
    def resizeEvent(self,event):super().resizeEvent(event);self.toast_widget.move((self.width()-self.toast_widget.width())//2,20)
    def copy(self,value):QApplication.clipboard().setText(value);self.toast(self.t("copy"))
    def open_website(self,value):
        url=QUrl.fromUserInput(value)
        if url.isValid() and url.scheme():QDesktopServices.openUrl(url)
    def eventFilter(self,watched,event):
        if watched is getattr(self,"table",None) and event.type()==QEvent.Type.KeyPress and event.key() in (Qt.Key.Key_Up,Qt.Key.Key_Down):
            current_row=self.table.currentRow()
            if current_row<0:current_row=0
            step=-1 if event.key()==Qt.Key.Key_Up else 1
            self.table.selectRow((current_row+step)%self.table.rowCount());return True
        return super().eventFilter(watched,event)
    def edit(self,entry=None):
        dialog=AccountDialog(self,entry)
        if dialog.exec():self.current=dialog.saved_entry.id;self.refresh();self.toast(self.t("success"))
    def delete(self,x):
        if QMessageBox.question(self,self.t("delete_title"),self.t("delete_note").format(x.title),QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes:self.vault.delete_entry(x.id);self.current=None;self.refresh();self.empty_detail()
    def toggle_theme(self):self.preferences.theme="light" if self.preferences.theme=="dark" else "dark";self.pref_service.save(self.preferences);self.apply_theme();self.show_vault()
    def settings(self):SettingsDialog(self).exec()
    def lock(self):self.vault.lock();self.show_gate()
    def closeEvent(self,event):self.vault.lock();event.accept()

if __name__=="__main__":
    app=QApplication(sys.argv);app.setStyle("Fusion");window=VaultWindow();window.show();sys.exit(app.exec())
