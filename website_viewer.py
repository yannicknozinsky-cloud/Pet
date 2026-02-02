from PyQt5 import QtWidgets, QtCore
import psycopg2
from config import * 
import sqlite3



class WebsiteViewer(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gespeicherte Websites")
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        self.setMinimumSize(650, 420)

        layout = QtWidgets.QVBoxLayout(self)

        title = QtWidgets.QLabel("Alle gespeicherten Websites:")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Name", "URL", ""])
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        layout.addWidget(self.table)

        btn_layout = QtWidgets.QHBoxLayout()
        add_btn = QtWidgets.QPushButton("Website hinzufügen")
        add_btn.setStyleSheet("background-color: #2a9d8f; color: white; padding: 6px 12px; border-radius: 5px;")
        add_btn.clicked.connect(self.add_website)
        btn_layout.addWidget(add_btn)

        close_btn = QtWidgets.QPushButton("Schließen")
        close_btn.setStyleSheet("padding: 6px 12px;")
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)
        self.load_data()

    def load_data(self):
        try:
            connectionOffline = sqlite3.connect(DB_PATH)
            cursorOffline = connectionOffline.cursor()
            
            cursorOffline.execute("SELECT name, url FROM websites ORDER BY name ASC")
            data = cursorOffline.fetchall()
            connectionOffline.close()

            self.table.setRowCount(len(data))
            for row_index, (name, url) in enumerate(data):
                self.table.setItem(row_index, 0, QtWidgets.QTableWidgetItem(name))
                self.table.setItem(row_index, 1, QtWidgets.QTableWidgetItem(url))

                delete_btn = QtWidgets.QPushButton("🗑️")
                delete_btn.setFixedSize(28, 28)
                delete_btn.setStyleSheet("""
                    QPushButton { background-color: #e63946; color: white; border-radius: 5px; font-size: 14px;}
                    QPushButton:hover { background-color: #d62828; }
                """)
                delete_btn.clicked.connect(lambda _, n=name: self.delete_website(n))
                self.table.setCellWidget(row_index, 2, delete_btn)

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Fehler", str(e))

    def delete_website(self, name):
        confirm = QtWidgets.QMessageBox.question(
            self,
            "Bestätigung",
            f"Soll die Website '{name}' wirklich gelöscht werden?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if confirm != QtWidgets.QMessageBox.Yes:
            return

        try:
            conn = get_pg_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM websites WHERE name = %s", (name,))
            conn.commit()
            rows_deleted = cur.rowcount
            conn.close()

            if rows_deleted > 0:
                connectionOffline = sqlite3.connect(DB_PATH)
                cursorOffline = connectionOffline.cursor()
                cursorOffline.execute("DELETE FROM websites WHERE name = %s", (name,))
                connectionOffline.commit()
                connectionOffline.close()
                QtWidgets.QMessageBox.information(self, "Erfolg", f"'{name}' wurde gelöscht.")
                self.load_data()
            else:
                QtWidgets.QMessageBox.warning(self, "Fehler", f"Website '{name}' nicht gefunden.")
        except Exception as e:
            connectionOffline = sqlite3.connect(DB_PATH)
            cursorOffline = connectionOffline.cursor()
            cursorOffline.execute("UPDATE websites SET deletflag = 1, synchronized = 0 WHERE name = %s", (name,))
            connectionOffline.commit()
            connectionOffline.close()
            QtWidgets.QMessageBox.information(self, f"'{name}' wurde offline gelöscht.")

    def add_website(self):
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Website hinzufügen")
        dialog.setFixedSize(350, 180)
        layout = QtWidgets.QVBoxLayout(dialog)

        name_label = QtWidgets.QLabel("Name:")
        name_edit = QtWidgets.QLineEdit()
        url_label = QtWidgets.QLabel("URL:")
        url_edit = QtWidgets.QLineEdit()

        layout.addWidget(name_label)
        layout.addWidget(name_edit)
        layout.addWidget(url_label)
        layout.addWidget(url_edit)

        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        layout.addWidget(button_box)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)

        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return

        name = name_edit.text().strip()
        url = url_edit.text().strip()
        if not name or not url:
            QtWidgets.QMessageBox.warning(self, "Fehler", "Bitte Name und URL eingeben.")
            return

        try:
            conn = get_pg_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO websites (name, url)
                VALUES (%s, %s)
                ON CONFLICT (name) DO UPDATE SET url = EXCLUDED.url
            """, (name, url))
            conn.commit()
            conn.close()
            connectionOffline = sqlite3.connect(DB_PATH)
            cursorOffline = connectionOffline.cursor()
            cursorOffline.execute("""
                INSERT INTO websites (name, url, synchronized, deletflag)
                VALUES (%s, %s, ?, ?)
                ON CONFLICT (name) DO UPDATE SET url = EXCLUDED.url
            """, (name, url, True, False))
            connectionOffline.commit()
            connectionOffline.close()
            QtWidgets.QMessageBox.information(self, "Erfolg", f"'{name}' wurde hinzugefügt/aktualisiert.")
            self.load_data()
        except Exception as e:
            connectionOffline = sqlite3.connect(DB_PATH)
            cursorOffline = connectionOffline.cursor()
            cursorOffline.execute("""
                INSERT INTO websites (name, url, synchronized, deletflag)
                VALUES (%s, %s, ?, ?)
                ON CONFLICT (name) DO UPDATE SET url = EXCLUDED.url
            """, (name, url, False, False))
            connectionOffline.commit()
            connectionOffline.close()
            QtWidgets.QMessageBox.information(self,f"'{name}' wurde offline hinzugefügt/aktualisiert.")
