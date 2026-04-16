from __future__ import annotations

import datetime

from i18n import t
from modules.version_matcher import VersionSearchQuery
from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDateEdit,
    QFrame,
    QGridLayout,
    QLineEdit,
)


class SearchBarWidget(QFrame):
    query = Signal(VersionSearchQuery)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setProperty("SettingsGroup", True)

        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(5, 5, 5, 5)

        self.fuzzy_text = QLineEdit(self)
        self.fuzzy_text.setPlaceholderText(t("act.search") + " . . .")
        self.fuzzy_text.textChanged.connect(self.query_updated)
        self.grid.addWidget(self.fuzzy_text, 0, 0, 1, 4)

        self.after_checkbox = QCheckBox(t("act.after"), self)
        self.after_checkbox.stateChanged.connect(self.query_updated)
        self.grid.addWidget(self.after_checkbox, 1, 0)

        self.date_after = QDateEdit(self)
        self.date_after.setCalendarPopup(True)
        self.date_after.setDate(QDate.currentDate().addYears(-1))
        self.date_after.setEnabled(False)
        self.date_after.dateChanged.connect(self.query_updated)
        self.grid.addWidget(self.date_after, 1, 1)

        self.after_checkbox.stateChanged.connect(
            lambda state: self.date_after.setEnabled(state == Qt.CheckState.Checked.value)
        )
        self.after_checkbox.stateChanged.connect(lambda _: self.query_updated)

        self.before_checkbox = QCheckBox(t("act.before"), self)
        self.before_checkbox.stateChanged.connect(self.query_updated)
        self.grid.addWidget(self.before_checkbox, 1, 2)

        self.date_before = QDateEdit(self)
        self.date_before.setCalendarPopup(True)
        self.date_before.setDate(QDate.currentDate())
        self.date_before.setEnabled(False)
        self.date_before.dateChanged.connect(self.query_updated)
        self.grid.addWidget(self.date_before, 1, 3)

        self.before_checkbox.stateChanged.connect(
            lambda state: self.date_before.setEnabled(state == Qt.CheckState.Checked.value)
        )
        self.before_checkbox.stateChanged.connect(lambda _: self.query_updated)

    def query_updated(self):
        self._q = self._generate_query()
        self.query.emit(self._q)

    def _generate_query(self) -> VersionSearchQuery:
        query = VersionSearchQuery()

        if self.after_checkbox.isChecked():
            qdate = self.date_after.date()
            after = datetime.datetime(
                qdate.year(),
                qdate.month(),
                qdate.day(),
                tzinfo=datetime.UTC,
            )
            query = query.with_after(after)

        if self.before_checkbox.isChecked():
            qdate = self.date_before.date()
            # Set to end of day
            before = datetime.datetime(
                qdate.year(),
                qdate.month(),
                qdate.day(),
                23,
                59,
                59,
                tzinfo=datetime.UTC,
            )
            query = query.with_before(before)

        # try to parse fuzzy text into a query
        text = self.fuzzy_text.text().strip()
        if text:
            splitted = text.split(" ", 1)
            possible_version = splitted.pop(0)
            try:
                q: VersionSearchQuery = VersionSearchQuery.parse(possible_version)
                if splitted:
                    q = q.with_fuzzy_text(splitted[0])

                query |= q
            except ValueError as _e:
                query = query.with_fuzzy_text(text)

        return query
