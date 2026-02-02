from PyQt5 import QtWidgets, QtCore
from datetime import datetime
import sqlite3

from config import *
from saveconfig import *


def parse_date(value):
    return datetime.strptime(value, "%Y-%m-%d").date()


class ToDoViewer(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Aufgaben")
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        self.setMinimumSize(800, 450)

        layout = QtWidgets.QVBoxLayout(self)

        title = QtWidgets.QLabel("Alle To Do")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        # --- Table ---
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["Name", "Datum", "Beschreibung", "Status", ""]
        )

        header = self.table.horizontalHeader()
        self.table.verticalHeader().setVisible(False)
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeToContents)

        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)

        layout.addWidget(self.table)

        # --- Buttons ---
        btn_layout = QtWidgets.QHBoxLayout()

        add_btn = QtWidgets.QPushButton("To Do hinzufügen")
        add_btn.clicked.connect(self.add_todo)
        btn_layout.addWidget(add_btn)

        close_btn = QtWidgets.QPushButton("Schließen")
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

        self.load_data()

    # ---------------- LOAD DATA ----------------
    def load_data(self):
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()

            cur.execute("""
                SELECT name, date, text, state
                FROM todo
                WHERE deletflag = 0
            """)

            data = cur.fetchall()
            conn.close()

            self.table.setRowCount(len(data))

            for row, (name, date, text, state) in enumerate(data):
                self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(name))
                self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(date or ""))
                self.table.setItem(row, 2, QtWidgets.QTableWidgetItem(text or ""))
                self.table.setItem(row, 3, QtWidgets.QTableWidgetItem(state or ""))

                delete_btn = QtWidgets.QPushButton("🗑️")
                delete_btn.setFixedSize(28, 28)
                delete_btn.clicked.connect(lambda _, n=name: self.delete_todo(n))
                self.table.setCellWidget(row, 4, delete_btn)

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Fehler", str(e))

    # ---------------- DELETE ----------------
    def delete_todo(self, name):
        if QtWidgets.QMessageBox.question(
            self,
            "Bestätigung",
            f"Todo '{name}' wirklich löschen?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        ) != QtWidgets.QMessageBox.Yes:
            return

        try:
            # PostgreSQL
            conn = get_pg_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM todo WHERE name=%s", (name,))
            conn.commit()
            conn.close()

            # SQLite
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("DELETE FROM todo WHERE name=?", (name,))
            conn.commit()
            conn.close()

            self.load_data()

        except Exception:
            # Offline fallback
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("""
                UPDATE todo
                SET deletflag=1, synchronized=0
                WHERE name=?
            """, (name,))
            conn.commit()
            conn.close()
            self.load_data()

    # ---------------- ADD TODO ----------------
    def add_todo(self):
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("To Do hinzufügen")
        dialog.setFixedSize(400, 300)
        layout = QtWidgets.QVBoxLayout(dialog)

        name_edit = QtWidgets.QLineEdit()
        text_edit = QtWidgets.QLineEdit()
        date_edit = QtWidgets.QLineEdit()

        layout.addWidget(QtWidgets.QLabel("Name"))
        layout.addWidget(name_edit)

        layout.addWidget(QtWidgets.QLabel("Beschreibung"))
        layout.addWidget(text_edit)

        layout.addWidget(QtWidgets.QLabel("Datum (YYYY-MM-DD)"))
        layout.addWidget(date_edit)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        layout.addWidget(buttons)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return

        name = name_edit.text().strip()
        beschreibung = text_edit.text().strip()

        try:
            datum = parse_date(date_edit.text().strip())
        except ValueError:
            QtWidgets.QMessageBox.warning(self, "Fehler", "Datum ungültig")
            return

        if not name:
            QtWidgets.QMessageBox.warning(self, "Fehler", "Name darf nicht leer sein")
            return

        try:
            # PostgreSQL
            conn = get_pg_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO todo (name, text, date, status)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (name) DO UPDATE
                SET
                    text = EXCLUDED.text,
                    date = EXCLUDED.date,
                    status = EXCLUDED.status
            """, (name, beschreibung, datum, "todo"))
            conn.commit()
            conn.close()

            synchronized = True

        except Exception:
            synchronized = False

        # SQLite (immer)
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO todo
            (name, date, text, state, synchronized, deletflag)
            VALUES (?, ?, ?, ?, ?, 0)
        """, (
            name,
            datum.isoformat(),
            beschreibung,
            "todo",
            synchronized
        ))
        conn.commit()
        conn.close()

        self.load_data()
