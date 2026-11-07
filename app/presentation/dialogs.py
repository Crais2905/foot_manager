import asyncio

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QDialog, QLabel, QLineEdit, QSpinBox, QPushButton, QVBoxLayout, QWidget

from app.application.exceptions import ApplicationValidationError
from app.domain.coach import Coach
from app.domain.enums import PlayerPosition
from app.presentation.widgets import FormDialog, Page, required, toolbar


def number_field(value: int = 1, *, minimum: int = 1, maximum: int = 99) -> QSpinBox:
    field = QSpinBox()
    field.setRange(minimum, maximum)
    field.setValue(value)
    return field


def position_combo(*, all_positions: bool = False) -> QComboBox:
    combo = QComboBox()
    if all_positions:
        combo.addItem("Усі позиції", None)
    for position in PlayerPosition:
        combo.addItem(position.display_name(), position)
    return combo


def selected_id(combo: QComboBox, label: str) -> int:
    value = combo.currentData()
    if type(value) is not int:
        raise ApplicationValidationError(f"Виберіть {label}.")
    return value


class DetailsDialog(QDialog):
    def __init__(
        self, title: str, page: Page, parent: QWidget, *, section: str, item_name: str,
    ) -> None:
        super().__init__(parent)
        self.page = page
        self.return_home = False
        self.setWindowTitle(title)
        self.resize(980, 570)
        layout = QVBoxLayout(self)
        home, section_button = QPushButton("Головна"), QPushButton(section)
        home.clicked.connect(self.go_home)
        section_button.clicked.connect(self.reject)
        current = QLabel(f"{item_name} · {title}")
        current.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(toolbar(home, QLabel("›"), section_button, QLabel("›"), current))
        layout.addWidget(page)
        close = QPushButton("Закрити")
        close.clicked.connect(self.reject)
        layout.addWidget(close)

    def reject(self) -> None:
        if not self.page.busy:
            super().reject()

    def go_home(self) -> None:
        if not self.page.busy:
            self.return_home = True
            self.reject()

    async def show_page(self) -> bool:
        done = asyncio.get_running_loop().create_future()
        self.finished.connect(lambda _: done.set_result(None))
        self.open()
        self.page.refresh()
        try:
            await done
            return self.return_home
        finally:
            self.deleteLater()


class NationalTeamDialog(FormDialog):
    def __init__(self, parent: QWidget, coaches: list[Coach]) -> None:
        super().__init__("Нова збірна", parent, "Далі")
        self.name = QLineEdit()
        self.city = QLineEdit()
        self.country = QLineEdit()
        self.name.setMaxLength(150)
        self.city.setMaxLength(100)
        self.country.setMaxLength(100)
        self.coach = QComboBox()
        self.coach.addItem("Виберіть тренера", None)
        for coach in coaches:
            self.coach.addItem(coach.full_name(), coach.id)
        self.form.addRow("Назва", self.name)
        self.form.addRow("Місто", self.city)
        self.form.addRow("Країна", self.country)
        self.form.addRow("Тренер", self.coach)
        if not coaches:
            self.notice.show_message("Для створення збірної потрібен тренер у базі даних.", error=True)
            self.save_button.setEnabled(False)

    def values(self) -> tuple[str, str, int]:
        return required(self.name, "Назва"), required(self.city, "Місто"), selected_id(self.coach, "тренера")
