import asyncio
from dataclasses import dataclass, field

from PySide6.QtCore import QSignalBlocker, Qt, QTimer, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QListWidget, QMainWindow, QStackedWidget, QVBoxLayout, QWidget,
)

from app.application.services import (
    ChampionshipService, CoachService, NationalTeamService, PlayerService, TeamService,
)
from app.presentation.pages.championships import ChampionshipsPage
from app.presentation.pages.dashboard import DashboardPage
from app.presentation.pages.management import CoachesPage, PlayersPage, TeamsPage
from app.presentation.pages.national import NationalTeamPage
from app.presentation.dialogs import DetailsDialog
from app.presentation.widgets import FormDialog, Page, TaskRunner


@dataclass
class ApplicationContainer:
    teams: TeamService = field(default_factory=TeamService)
    players: PlayerService = field(default_factory=PlayerService)
    coaches: CoachService = field(default_factory=CoachService)
    championships: ChampionshipService = field(default_factory=ChampionshipService)
    national: NationalTeamService = field(default_factory=NationalTeamService)


class NavigationPanel(QFrame):
    def __init__(self, labels: tuple[str, ...]) -> None:
        super().__init__()
        self.setObjectName("sidebar")
        self.setFixedWidth(216)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 22, 14, 18)
        brand = QLabel("FOOTBALL\nMANAGER")
        brand.setObjectName("brand")
        layout.addWidget(brand)
        self.items = QListWidget()
        self.items.setObjectName("navigation")
        self.items.setAccessibleName("Навігація")
        self.items.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.items.addItems(labels)
        layout.addWidget(self.items, 1)


class MainWindow(QMainWindow):
    closed = Signal()

    def __init__(self, services: ApplicationContainer) -> None:
        super().__init__()
        self.setWindowTitle("Football Management System")
        self.setMinimumSize(850, 580)
        self.resize(1180, 760)
        self.runner = TaskRunner()
        self._waiting_to_close = False
        self.pages: tuple[Page, ...] = (
            DashboardPage(self.runner, services.teams, services.players, services.coaches, services.championships),
            TeamsPage(self.runner, services.teams, services.players),
            PlayersPage(self.runner, services.players, services.teams),
            CoachesPage(self.runner, services.coaches, services.teams),
            ChampionshipsPage(self.runner, services.championships, services.teams),
            NationalTeamPage(self.runner, services.national, services.coaches),
        )
        root = QWidget()
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.navigation = NavigationPanel(("Головна", "Команди", "Гравці", "Тренери",
                                          "Чемпіонати", "Національна збірна"))
        self.stack = QStackedWidget()
        for page in self.pages:
            self.stack.addWidget(page)
            page.home_requested.connect(lambda: self.select_page(0))
        layout.addWidget(self.navigation)
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(root)
        self.navigation.items.setCurrentRow(0)
        self.navigation.items.currentRowChanged.connect(self.select_page)

    def _active_dialog(self) -> QWidget | None:
        modal = QApplication.activeModalWidget()
        parent = modal
        while parent is not None:
            if parent is self:
                return modal
            parent = parent.parentWidget()
        return next((form for form in self.findChildren(FormDialog) if form.isVisible()), None)

    def select_page(self, index: int) -> None:
        if not 0 <= index < len(self.pages) or self._waiting_to_close:
            return
        current = self.stack.currentIndex()
        modal = self._active_dialog()
        if index != current and modal is not None:
            with QSignalBlocker(self.navigation.items):
                self.navigation.items.setCurrentRow(current)
            if isinstance(modal, FormDialog):
                parent = modal.parentWidget()
                modal.request_leave(lambda: self._navigate_after_form(index, parent))
            return
        with QSignalBlocker(self.navigation.items):
            self.navigation.items.setCurrentRow(index)
        self.stack.setCurrentIndex(index)
        self.pages[index].refresh()

    def _navigate_after_form(self, index: int, parent: QWidget | None) -> None:
        if not isinstance(parent, DetailsDialog):
            self.select_page(index)
            return

        def leave_details() -> None:
            parent.reject()
            QTimer.singleShot(0, lambda: self.select_page(index))

        if parent.page.busy:
            parent.page.idle.connect(leave_details, Qt.ConnectionType.SingleShotConnection)
        else:
            leave_details()

    def closeEvent(self, event: QCloseEvent) -> None:
        modal = self._active_dialog()
        if modal is not None:
            event.ignore()
            modal.close()
            return
        if self.runner.tasks:
            event.ignore()
            if not self._waiting_to_close:
                self._waiting_to_close = True
                self.navigation.setEnabled(False)
                self.statusBar().showMessage("Очікуємо завершення поточної операції…")
                asyncio.create_task(self._finish_close())
        else:
            event.accept()
            self.closed.emit()

    async def _finish_close(self) -> None:
        await self.runner.drain()
        self.close()
