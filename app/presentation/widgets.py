import asyncio
from collections.abc import Awaitable, Callable, Sequence
from typing import Any

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QPersistentModelIndex, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QDateEdit, QDialog, QDialogButtonBox, QFormLayout, QFrame, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QMessageBox, QProgressBar, QPushButton,
    QSpinBox, QTableView, QVBoxLayout, QWidget,
)

from app.application.exceptions import ApplicationValidationError
from app.presentation.error_handler import ErrorHandler

type Row = tuple[int, tuple[object, ...]]


class TaskRunner:
    def __init__(self) -> None:
        self.tasks: set[asyncio.Task[None]] = set()

    def start(self, operation: Awaitable[None]) -> None:
        async def run() -> None:
            await operation

        task = asyncio.create_task(run())
        self.tasks.add(task)
        task.add_done_callback(self._finished)

    def _finished(self, task: asyncio.Task[None]) -> None:
        self.tasks.discard(task)
        if not task.cancelled() and (error := task.exception()) is not None:
            task.get_loop().call_exception_handler({"exception": error})

    async def drain(self) -> None:
        while self.tasks:
            await asyncio.gather(*tuple(self.tasks), return_exceptions=True)


class SearchBar(QLineEdit):
    def __init__(self, placeholder: str = "Пошук за назвою") -> None:
        super().__init__()
        self.setPlaceholderText(placeholder)
        self.setClearButtonEnabled(True)
        self.setAccessibleName(placeholder)


class NotificationWidget(QLabel):
    def __init__(self) -> None:
        super().__init__()
        self.setWordWrap(True)
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.hide()

    def show_message(self, message: str, *, error: bool = False) -> None:
        self.setObjectName("error" if error else "success")
        self.style().unpolish(self)
        self.style().polish(self)
        self.setText(message)
        self.show()


class LoadingWidget(QProgressBar):
    def __init__(self) -> None:
        super().__init__()
        self.setRange(0, 0)
        self.setTextVisible(False)
        self.setFixedHeight(4)
        self.setAccessibleName("Завантаження")
        self.hide()


class EmptyStateWidget(QLabel):
    def __init__(self, text: str = "Немає записів.") -> None:
        super().__init__(text)
        self.setObjectName("muted")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWordWrap(True)


class TableModel(QAbstractTableModel):
    def __init__(self, headers: Sequence[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.headers = tuple(headers)
        self.rows: tuple[Row, ...] = ()

    def replace(self, rows: Sequence[Row]) -> None:
        self.beginResetModel()
        self.rows = tuple(rows)
        self.endResetModel()

    def rowCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.headers)

    def data(
        self, index: QModelIndex | QPersistentModelIndex, role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if not index.isValid():
            return None
        key, values = self.rows[index.row()]
        if role == Qt.ItemDataRole.UserRole:
            return key
        if role == Qt.ItemDataRole.DisplayRole:
            value = values[index.column()]
            return "—" if value is None else str(value)
        return None

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self.headers[section]
        return None


class DataTable(QWidget):
    selection_changed = Signal()
    activated = Signal()

    def __init__(self, headers: Sequence[str], empty_text: str = "Немає записів.") -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.view = QTableView()
        self.model = TableModel(headers, self)
        self.view.setModel(self.model)
        self.view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.view.setAlternatingRowColors(True)
        self.view.verticalHeader().hide()
        header = self.view.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setStretchLastSection(True)
        self.view.selectionModel().selectionChanged.connect(
            lambda _selected, _deselected: self.selection_changed.emit()
        )
        self.view.activated.connect(lambda _index: self.activated.emit())
        self.empty = EmptyStateWidget(empty_text)
        layout.addWidget(self.view, 1)
        layout.addWidget(self.empty, 1)
        self.set_rows([])

    def selected_id(self) -> int | None:
        selected = self.view.selectionModel().selectedRows()
        return self.model.data(selected[0], Qt.ItemDataRole.UserRole) if selected else None

    def set_rows(self, rows: Sequence[Row]) -> None:
        current = self.selected_id()
        self.model.replace(rows)
        self.view.setVisible(bool(rows))
        self.empty.setVisible(not rows)
        for index, (key, _) in enumerate(rows):
            if key == current:
                self.view.selectRow(index)
                break
        self.selection_changed.emit()


class Page(QWidget):
    home_requested = Signal()
    idle = Signal()

    def __init__(self, title: str, runner: TaskRunner, subtitle: str = "") -> None:
        super().__init__()
        self.runner = runner
        self.busy = False
        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 24, 28, 24)
        outer.setSpacing(14)
        heading = QLabel(title)
        heading.setObjectName("heading")
        outer.addWidget(heading)
        if subtitle:
            label = QLabel(subtitle)
            label.setTextFormat(Qt.TextFormat.PlainText)
            label.setObjectName("muted")
            label.setWordWrap(True)
            outer.addWidget(label)
        self.notice = NotificationWidget()
        self.loading = LoadingWidget()
        outer.addWidget(self.notice)
        outer.addWidget(self.loading)
        self.body = QWidget()
        self.content = QVBoxLayout(self.body)
        self.content.setContentsMargins(0, 0, 0, 0)
        self.content.setSpacing(12)
        outer.addWidget(self.body, 1)

    def button(self, text: str, operation: Callable[[], Awaitable[None]]) -> QPushButton:
        button = QPushButton(text)
        button.clicked.connect(lambda: self.perform(operation))
        return button

    def perform(self, operation: Callable[[], Awaitable[None]]) -> None:
        if self.busy:
            return
        self.busy = True
        self.notice.hide()
        self.body.setEnabled(False)
        self.loading.show()

        async def run() -> None:
            try:
                await operation()
            except Exception as error:
                self.notice.show_message(ErrorHandler.report(error, self.window()), error=True)
            finally:
                self.busy = False
                self.body.setEnabled(True)
                self.loading.hide()
                self.idle.emit()

        self.runner.start(run())

    def refresh(self) -> None:
        self.perform(self.load)

    async def load(self) -> None:
        raise NotImplementedError


class FormDialog(QDialog):
    def __init__(self, title: str, parent: QWidget, submit_label: str = "Зберегти") -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(380)
        layout = QVBoxLayout(self)
        self.fields = QWidget()
        self.form = QFormLayout(self.fields)
        layout.addWidget(self.fields)
        self.notice = NotificationWidget()
        self.loading = LoadingWidget()
        layout.addWidget(self.notice)
        layout.addWidget(self.loading)
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.save_button = self.buttons.button(QDialogButtonBox.StandardButton.Save)
        self.save_button.setText(submit_label)
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Скасувати")
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self._saving = False
        self._initial_state: tuple[object, ...] | None = None
        self._leave_prompt: QMessageBox | None = None

    def form_state(self) -> tuple[object, ...]:
        values: list[object] = []
        for row in range(self.form.rowCount()):
            item = self.form.itemAt(row, QFormLayout.ItemRole.FieldRole)
            field = item.widget() if item is not None else None
            if isinstance(field, QLineEdit):
                values.append(field.text())
            elif isinstance(field, QComboBox):
                values.append(field.currentData())
            elif isinstance(field, QSpinBox):
                values.append(field.value())
            elif isinstance(field, QDateEdit):
                values.append(field.date().toJulianDay())
        return tuple(values)

    def reject(self) -> None:
        self.request_leave()

    def request_leave(self, after_leave: Callable[[], None] | None = None) -> None:
        def leave() -> None:
            super(FormDialog, self).reject()
            if after_leave is not None:
                QTimer.singleShot(0, after_leave)

        if self._saving or self._leave_prompt is not None:
            return
        if self._initial_state is None or self.form_state() == self._initial_state:
            leave()
            return
        prompt = QMessageBox(self)
        self._leave_prompt = prompt
        prompt.setWindowTitle("Незбережені зміни")
        prompt.setText("Ви внесли зміни. Що зробити перед виходом?")
        prompt.setIcon(QMessageBox.Icon.Warning)
        prompt.setStandardButtons(
            QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel
        )
        prompt.button(QMessageBox.StandardButton.Discard).setText("Вийти без збереження")
        prompt.button(QMessageBox.StandardButton.Cancel).setText("Продовжити редагування")
        prompt.setDefaultButton(QMessageBox.StandardButton.Cancel)
        prompt.setEscapeButton(QMessageBox.StandardButton.Cancel)

        def choose(result: int) -> None:
            self._leave_prompt = None
            prompt.deleteLater()
            if result == QMessageBox.StandardButton.Discard:
                leave()

        prompt.finished.connect(choose)
        prompt.open()

    async def execute(
        self, save: Callable[[], Awaitable[None]], *, allow_navigation: bool = False,
    ) -> bool:
        finished = asyncio.get_running_loop().create_future()

        def on_finished(result: int) -> None:
            if not finished.done():
                finished.set_result(result == QDialog.DialogCode.Accepted)

        self.finished.connect(on_finished)

        async def submit() -> None:
            success = False
            self.notice.hide()
            self.loading.show()
            try:
                await save()
                success = True
            except Exception as error:
                self.notice.show_message(ErrorHandler.report(error, self.window()), error=True)
            finally:
                self._saving = False
                self.loading.hide()
                self.fields.setEnabled(True)
                self.buttons.setEnabled(True)
            if success:
                self.accept()

        def on_submit() -> None:
            if self._saving:
                return
            self._saving = True
            self.fields.setEnabled(False)
            self.buttons.setEnabled(False)
            asyncio.create_task(submit())

        self.buttons.accepted.connect(on_submit)
        self._initial_state = self.form_state()
        if allow_navigation:
            self.show()
        else:
            self.open()
        try:
            return await finished
        finally:
            self.deleteLater()


class ConfirmationDialog(QMessageBox):
    def __init__(
        self, message: str, parent: QWidget, *, title: str = "Підтвердження видалення",
        object_name: str = "", confirm_text: str = "Видалити", cancel_text: str = "Скасувати",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setIcon(QMessageBox.Icon.Warning)
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setText(f'{message} «{object_name}»?' if object_name else message)
        self.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
        self.setDefaultButton(QMessageBox.StandardButton.Cancel)
        self.button(QMessageBox.StandardButton.Yes).setText(confirm_text)
        self.button(QMessageBox.StandardButton.Cancel).setText(cancel_text)
        self.setEscapeButton(QMessageBox.StandardButton.Cancel)

    async def confirmed(self) -> bool:
        result = asyncio.get_running_loop().create_future()
        self.finished.connect(lambda code: result.set_result(code == QMessageBox.StandardButton.Yes))
        self.open()
        try:
            return await result
        finally:
            self.deleteLater()


def toolbar(*widgets: QWidget) -> QWidget:
    panel = QFrame()
    layout = QHBoxLayout(panel)
    layout.setContentsMargins(0, 0, 0, 0)
    for widget in widgets:
        layout.addWidget(widget)
    layout.addStretch()
    return panel


def required(field: QLineEdit, label: str) -> str:
    value = field.text().strip()
    if not value:
        raise ApplicationValidationError(f"Заповніть поле «{label}».")
    return value
