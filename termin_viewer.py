from PyQt5 import QtWidgets, QtCore, QtGui
from datetime import datetime
from config import get_pg_connection  # liefert psycopg2.Connection
import sqlite3
from datetime import datetime
from config import *
from saveconfig import *

def parse_date(value):
    return datetime.strptime(value, "%Y-%m-%d").date()

def parse_time(value):
    return datetime.strptime(value, "%H:%M").time()

class TerminViewer(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gespeicherte Termine")
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        self.setMinimumSize(800, 450)

        layout = QtWidgets.QVBoxLayout(self)

        title = QtWidgets.QLabel("Alle gespeicherten Termine:")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        # --- Toggle Weekly ---
        self.toggle_btn = QtWidgets.QPushButton("Zeige: Weekly Termine")
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #264653; color: white; padding: 6px 12px;
                border-radius: 6px; font-weight: bold;
            }
            QPushButton:checked {
                background-color: #2a9d8f;
            }
        """)
        self.toggle_btn.toggled.connect(self.toggle_view)
        layout.addWidget(self.toggle_btn)

        # --- Table ---
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["Name", "Datum", "von", "bis", "Ort", "Wiederholen", ""]
        )
        header = self.table.horizontalHeader()
        self.table.verticalHeader().setVisible(False)
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(5, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QtWidgets.QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        layout.addWidget(self.table)

        # --- Buttons ---
        btn_layout = QtWidgets.QHBoxLayout()
        add_btn = QtWidgets.QPushButton("Termin hinzufügen")
        add_btn.setStyleSheet("background-color: #2a9d8f; color: white; padding: 6px 12px; border-radius: 5px;")
        add_btn.clicked.connect(self.add_termin)
        btn_layout.addWidget(add_btn)

        close_btn = QtWidgets.QPushButton("Schließen")
        close_btn.setStyleSheet("padding: 6px 12px;")
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        # --- Initial load ---
        self.load_data()

    # --- Toggle Weekly / Single ---

    
    def toggle_view(self, checked):
        if checked:
            self.toggle_btn.setText("Zeige: Einmalige Termine")
            self.load_data(only_weekly=True)
        else:
            self.toggle_btn.setText("Zeige: Weekly Termine")
            self.load_data(only_weekly=False)

    # --- Load data from PostgreSQL ---
    def load_data(self, only_weekly=False):

        try:
            connectionOffline = sqlite3.connect(DB_PATH)
            cursorOffline = connectionOffline.cursor()
        

            # Fetch data
            if only_weekly:
                cursorOffline.execute("""
                    SELECT name, datum, uhrzeitstart, uhrzeitende, ort, repeate 
                    FROM termine 
                    WHERE repeate='weekly' 
                    ORDER BY datum
                """)
            else:
                cursorOffline.execute("""
                    SELECT name, datum, uhrzeitstart, uhrzeitende, ort, repeate 
                    FROM termine 
                    ORDER BY datum
                """)
            data = cursorOffline.fetchall()
            connectionOffline.close()

            self.table.setRowCount(len(data))

            for row_index, (name, datum, uhrzeitstart, uhrzeitende, ort, repeate) in enumerate(data):

                datum_str = datum or ""
                uhrzeitstart_str = uhrzeitstart[:5] if uhrzeitstart else ""
                uhrzeitende_str = uhrzeitende[:5] if uhrzeitende else ""
                ort = ort or ""
                repeate = repeate or ""

                self.table.setItem(row_index, 0, QtWidgets.QTableWidgetItem(name))
                self.table.setItem(row_index, 1, QtWidgets.QTableWidgetItem(datum_str))
                self.table.setItem(row_index, 2, QtWidgets.QTableWidgetItem(uhrzeitstart_str))
                self.table.setItem(row_index, 3, QtWidgets.QTableWidgetItem(uhrzeitende_str))
                self.table.setItem(row_index, 4, QtWidgets.QTableWidgetItem(ort))
                self.table.setItem(row_index, 5, QtWidgets.QTableWidgetItem(repeate))


                delete_btn = QtWidgets.QPushButton("🗑️")
                delete_btn.setFixedSize(28, 28)
                delete_btn.setStyleSheet("""
                    QPushButton { background-color: #e63946; color: white; border-radius: 5px; font-size: 14px;}
                    QPushButton:hover { background-color: #d62828; }
                """)
                delete_btn.clicked.connect(lambda _, n=name: self.delete_termin(n))
                self.table.setCellWidget(row_index, 6, delete_btn)

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Fehler", str(e))

    # --- Delete ---
    def delete_termin(self, name):
        confirm = QtWidgets.QMessageBox.question(
            self,
            "Bestätigung",
            f"Soll der Termin '{name}' wirklich gelöscht werden?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if confirm != QtWidgets.QMessageBox.Yes:
            return

        try:
            conn = get_pg_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM termine WHERE name=%s", (name,))
            conn.commit()
            rows_deleted = cur.rowcount
            conn.close()

            if rows_deleted > 0:
                connectionOffline = sqlite3.connect(DB_PATH)
                cursorOffline = connectionOffline.cursor()
                cursorOffline.execute("DELETE FROM termine WHERE name=?", (name,))
                connectionOffline.commit()
                connectionOffline.close()
                QtWidgets.QMessageBox.information(self, "Erfolg", f"'{name}' wurde gelöscht.")
                self.load_data()
            else:
                QtWidgets.QMessageBox.warning(self, "Fehler", f"Termin '{name}' nicht gefunden.")
        except Exception as e:
            connectionOffline = sqlite3.connect(DB_PATH)
            cursorOffline = connectionOffline.cursor()
            cursorOffline.execute("UPDATE termine SET deletflag=True, synchronized=False WHERE name=?", (name,))
            connectionOffline.commit()
            connectionOffline.close()
            QtWidgets.QMessageBox.critical(self, "Fehler", str(e))

    def add_termin(self):
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Termin hinzufügen")
        dialog.setFixedSize(400, 350)
        layout = QtWidgets.QVBoxLayout(dialog)

        name_edit = QtWidgets.QLineEdit()
        datum_edit = QtWidgets.QLineEdit()
        von_edit = QtWidgets.QLineEdit()
        bis_edit = QtWidgets.QLineEdit()
        ort_edit = QtWidgets.QLineEdit()
        repeate_combo = QtWidgets.QComboBox()
        repeate_combo.addItems(["no", "weekly", "daily", "monthly", "yearly"])

        layout.addWidget(QtWidgets.QLabel("Name:"))
        layout.addWidget(name_edit)
        layout.addWidget(QtWidgets.QLabel("Datum (YYYY-MM-DD):"))
        layout.addWidget(datum_edit)
        layout.addWidget(QtWidgets.QLabel("Uhrzeit von (HH:MM):"))
        layout.addWidget(von_edit)
        layout.addWidget(QtWidgets.QLabel("Uhrzeit bis (HH:MM):"))
        layout.addWidget(bis_edit)
        layout.addWidget(QtWidgets.QLabel("Ort:"))
        layout.addWidget(ort_edit)
        layout.addWidget(QtWidgets.QLabel("Wiederholung:"))
        layout.addWidget(repeate_combo)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        layout.addWidget(buttons)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return

        name = name_edit.text().strip()
        ort = ort_edit.text().strip()
        repeate = repeate_combo.currentText()

        try:
            datum = parse_date(datum_edit.text().strip())
            von = parse_time(von_edit.text().strip()) if von_edit.text() else None
            bis = parse_time(bis_edit.text().strip()) if bis_edit.text() else None
        except ValueError:
            QtWidgets.QMessageBox.warning(
                self, "Fehler", "Datum oder Uhrzeit haben ein falsches Format!"
            )
            return

        if not name:
            QtWidgets.QMessageBox.warning(self, "Fehler", "Name darf nicht leer sein!")
            return

        try:
            # ---------- PostgreSQL ----------
            conn = get_pg_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO termine (name, datum, uhrzeitstart, uhrzeitende, ort, repeate)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (name) DO UPDATE
                SET datum = EXCLUDED.datum,
                    uhrzeitstart = EXCLUDED.uhrzeitstart,
                    uhrzeitende = EXCLUDED.uhrzeitende,
                    ort = EXCLUDED.ort,
                    repeate = EXCLUDED.repeate
            """, (name, datum, von, bis, ort, repeate))
            conn.commit()
            conn.close()

            # ---------- SQLite ----------
            conn_sqlite = sqlite3.connect(DB_PATH)
            cur_sqlite = conn_sqlite.cursor()

            cur_sqlite.execute("""
                INSERT OR REPLACE INTO termine
                (name, datum, uhrzeitstart, uhrzeitende, ort, repeate, synchronized, deletflag)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                name,
                datum.isoformat(),
                von.isoformat() if von else None,
                bis.isoformat() if bis else None,
                ort,
                repeate, True, False
            ))

            conn_sqlite.commit()
            conn_sqlite.close()

            QtWidgets.QMessageBox.information(
                self, "Erfolg", f"'{name}' wurde hinzugefügt/aktualisiert."
            )
            self.load_data()

        except Exception as e:
            conn_sqlite = sqlite3.connect(DB_PATH)
            cur_sqlite = conn_sqlite.cursor()

            cur_sqlite.execute("""
                INSERT OR REPLACE INTO termine
                (name, datum, uhrzeitstart, uhrzeitende, ort, repeate, synchronized, deletflag)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                name,
                datum.isoformat(),
                von.isoformat() if von else None,
                bis.isoformat() if bis else None,
                ort,
                repeate, False, False
            ))

            conn_sqlite.commit()
            conn_sqlite.close()

            QtWidgets.QMessageBox.information(
                self, f"'{name}' wurde offline hinzugefügt/aktualisiert."
            )
            self.load_data()
           

            
            

            
            
            

