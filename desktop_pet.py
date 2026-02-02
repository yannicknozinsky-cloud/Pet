import random
import datetime
import subprocess
import os
import time
import string
import sqlite3
from datetime import date, datetime
from PyQt5 import QtCore, QtGui, QtWidgets
from speachOnline import OnlineTTS
from config import *
from global_vars import clones
from website_viewer import WebsiteViewer
from termin_viewer import TerminViewer
from RoundedLabel import RoundedLabel
from datetime import date, time
import speak
import psycopg2
import socket
import warnings
from datetime import date as dt_date
from todo_viewer import ToDoViewer
from wakeup import WakeWordDetector
from PyQt5.QtCore import pyqtSignal
import time 

from saveconfig import *
warnings.filterwarnings("ignore", category=DeprecationWarning)

DB_PATH = "/home/yannick/Projects/DesktopPet/Pet/Desktop_pet.db"

# =========================
# DB-Hilfsfunktionen
# =========================
def get_pg_connection():
    return psycopg2.connect(
    host="db.qkmtybzdthrpjfkbgskw.supabase.co",
    port=5432,
    dbname="postgres",
    user="postgres",
    password="AfFiMaCeL26!",
    connect_timeout=10,
    options="-c search_path=public",
    sslmode="require",
)

def fetch_termine(dayfilter="no"):
    if dayfilter == "no":
        try:
            connectionOffline = sqlite3.connect(DB_PATH)
            cursorOffline = connectionOffline.cursor()
            cursorOffline.execute("SELECT id, name, datum, uhrzeitstart, uhrzeitende, ort, repeate FROM termine WHERE deletflag = ?", (0,))
            rows = cursorOffline.fetchall()
            connectionOffline.close()
            return rows
        except Exception as e:
            print(f"Fehler beim Laden der Termine: {e}")
            return []
    elif dayfilter=="today":
        try:
            connectionOffline = sqlite3.connect(DB_PATH)
            cursorOffline = connectionOffline.cursor()
            cursorOffline.execute("SELECT id, name, datum, uhrzeitstart, uhrzeitende, ort, repeate FROM termine WHERE deletflag = ? AND datum= ?", (0,date.today()))
            rows = cursorOffline.fetchall()
            connectionOffline.close()
            return rows
        except Exception as e:
            print(f"Fehler beim Laden der Heutigen Termine: {e}")
            return []
    
def fetch_todo():
    try:
        connectionOffline = sqlite3.connect(DB_PATH)
        cursorOffline = connectionOffline.cursor()
        cursorOffline.execute("SELECT id, name, date, text, state FROM todo WHERE deletflag = ? AND state != ? ORDER BY date", (0,"done"))
        rows = cursorOffline.fetchall()
        connectionOffline.close()
        return rows
    except Exception as e:
        print(f"Fehler beim Laden der To Do: {e}")
        return []

def fetch_websites():
    try:
        connectionOffline = sqlite3.connect(DB_PATH)
        cursorOffline = connectionOffline.cursor()
        cursorOffline.execute("SELECT id, name, url FROM websites WHERE deletflag = ?", (0,))
        rows = cursorOffline.fetchall()
        connectionOffline.close()
        return rows
    except Exception as e:
        print(f"Fehler beim Laden der Websites: {e}")
        return []



class DesktopPet(QtWidgets.QLabel):
    wakeword_signal = pyqtSignal()
    def __init__(self):
        super().__init__()
        self.online_status = False
        self.tts = OnlineTTS()
        if self.internet_verfuegbar:
            self.online_status=True
            self.talk("Willkommen zurück! Ich bin Online")
        else:
            self.talk("Willkommen zurück! Offline Model")
        

        # Beispiel: Text sprechen
        
        self.DB_Update_Status = False
        self.timer_target_x=None
        self.current_path=None
        self.behavior_bevor_timer=None
        options = [BLUE, GREEN, PURPLE, RED]
        self.colour=random.choice(options)
        self.direktion=PetDirektion.LEFT
        self.walking_step=0 #0 standing, 1 first step, 2 second step
        self.behavior = PetBehavior.WALK
        self.behavior_bevor_fall = PetBehavior.WALK
        self.pet_width = 128
        self.pet_height = 128
        self.original_pixmap = QtGui.QPixmap(
            "/home/yannick/Projects/DesktopPet/Pet/blue_black_boy/"+self.colour+"_shime1-1.png.png"
        ).scaled(
            self.pet_width,
            self.pet_height,
            QtCore.Qt.KeepAspectRatio,
            QtCore.Qt.SmoothTransformation
        )
        self.setPixmap(self.original_pixmap)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnTopHint |
            QtCore.Qt.Tool  
        )
        self.total_geometry = self.get_total_screen_geometry()
        self.screen_geometries = [s.geometry() for s in QtWidgets.QApplication.instance().screens()]

        # Untersten Bildschirm finden (höchster y-Wert)
        screens = QtWidgets.QApplication.instance().screens()
        lowest_screen = max(screens, key=lambda s: s.geometry().y() + s.geometry().height())
        screen_geo = lowest_screen.geometry()

        # Starte unten rechts auf diesem Bildschirm
        self.position_x = screen_geo.x() + screen_geo.width() - self.pet_width
        self.position_y = screen_geo.y() + screen_geo.height() - self.pet_height
        

       
        self.move(int(self.position_x), int(self.position_y))
        self.target_x=self.position_x
        self.target_y=self.position_y

        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        
        self.walk_step_timer = QtCore.QTimer()
        self.walk_step_timer.timeout.connect(self.take_step)
        self.walk_step_timer.start(80)

        self.run_step_timer = QtCore.QTimer()
        self.run_step_timer.timeout.connect(self.take_run_step)
        self.run_step_timer.stop()
        

        self.wait_at_target_timer=QtCore.QTimer()
        self.wait_at_target_timer.timeout.connect(self.resume_walk)
        self.wait_at_target_timer.start(2000)        
        self.wait_at_target_timer.stop()        


        self.dragging = False
        self.drag_offset = QtCore.QPoint()
        self.drag_target_pos = self.pos()
        self.drag_follow_timer = QtCore.QTimer()
        self.drag_follow_timer.timeout.connect(self.drag_follow_step)

        self.fall_timer = QtCore.QTimer()
        self.fall_timer.timeout.connect(self.fall_step)
        

       
        self.minutes_input = QtWidgets.QLineEdit(self)
        self.minutes_input.setFixedSize(30, 20)
        self.minutes_input.setPlaceholderText("Min")
        self.minutes_input.setStyleSheet("background-color: white; border-radius: 5px;")
        self.minutes_input.hide()

        self.seconds_input = QtWidgets.QLineEdit(self)
        self.seconds_input.setFixedSize(30, 20)
        self.seconds_input.setPlaceholderText("Sek")
        self.seconds_input.setStyleSheet("background-color: white; border-radius: 5px;")
        self.seconds_input.hide()

        # Positionieren:
        self.minutes_input.move(10, self.pet_height//2)
        self.seconds_input.move(50, self.pet_height//2)
        self.minutes_input.returnPressed.connect(self.start_countdown)
        self.seconds_input.returnPressed.connect(self.start_countdown)

        # Timer-Label erzeugen
        self.timer_label = QtWidgets.QLabel(self)
        self.timer_option_enabled = False
        self.timer_label.setStyleSheet("color: red; font-weight: bold; font-size: 16px; background-color: rgba(255,255,255,200); border-radius: 5px; padding: 2px;")
        self.timer_label.setAlignment(QtCore.Qt.AlignCenter)
        self.timer_label.setFixedSize(50, 20)
        self.timer_label.hide()
        self.countdown_time = 0
        self.countdown_timer = QtCore.QTimer()
        self.countdown_timer.timeout.connect(self.update_countdown)
        self.jump_timer = QtCore.QTimer()
        self.jump_timer.timeout.connect(self.perform_jump)
        self.jump_count = 0
        self.wakeword_state=False
        self.show()
        self.hello_label = RoundedLabel("Synchronising...", width=100, colour="red", parent=self)
        self.hello_label.show()
        self.updateLabelPosition()
        QtCore.QTimer.singleShot(2000, self.start)
        
        self.last_wakeword_time = 0 # Timestamp der letzten Erkennung
        self.wakeword_cooldown = 2.0  # Sekunden, in denen weitere Erkennungen ignoriert werde
        self.wakeword_signal.connect(self.on_wakeword_gui)
        # statt direkt im __init__ starten:
        QtCore.QTimer.singleShot(2000, self.start_wakeword)


    def talk(self,text):
        if self.online_status:
            self.tts.speak(text,rate="1.2",pitch=9)
        #else:
            #speak.readtext(text)

    def start_wakeword(self):
        MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "vosk-model-small-de-0.15")
        MODEL_PATH = os.path.abspath(MODEL_PATH)  # optional, macht den Pfad absolut

        self.detector = WakeWordDetector(model_path=MODEL_PATH)
        
        # Startet den Detector direkt mit der Callback-Funktion
        self.detector.start(self.wakeword_detected)

        # Safe-Zeitstempel, damit beim Start nichts feuert
        self.last_wakeword_time = time.time()




    def wakeword_detected(self):
        now = time.time()
        # Cooldown abfragen
        if now - getattr(self, 'last_wakeword_time', 0) < self.wakeword_cooldown :
            return
        self.last_wakeword_time = now
        self.wakeword_signal.emit()



    def on_wakeword_gui(self):
        # 🔥 Thread-sicher, läuft im GUI-Thread
        if self.wakeword_state:
            self.talk("Hallo.")
            self.perform_jump()
            


    def start(self):
        
        text=""
        c="black"
        if self.internet_verfuegbar():
            self.online_status = True
            if self.updateTermineDB() and self.updateWebsiteDB() and self.updateToDoDB():
                self.talk("synchronisiert.")
                text="Synchronised"
                c="green"
                self.DB_Update_Status=True
            else:
                self.talk("fehlgeschlagen.")
                text="Failed"
                c="red"
        else:
            self.talk("keine Internet verbindung.")
            text="No Internet"
            c="red"
        self.hello_label.hide()
        self.hello_label = RoundedLabel(text, width=100, colour=c, parent=self)
          # Position über dem Pet
        self.hello_label.show()
        self.updateLabelPosition()

        # Timer erstellen, um Label nach 4 Sekunden zu verstecken
        QtCore.QTimer.singleShot(2000, self.hello_label.hide)
        QtCore.QTimer.singleShot(2000, self.showTermine)

    def showTermine(self):
        #self.talk("Deine heutigen Termine sind.")
        rows = fetch_termine(dayfilter="today")
        if rows:
            heute = date.today()
            text = "<b>Hallo Yannick</b>,"
            if self.DB_Update_Status:
                text += '<b style="color:green;">     &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;●</b>'
            else:
                text += '<b style="color:red;">     &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;●</b>'
            text+="<br>deine heutigen Termine:<br>"
            waittime=2000
            speak_text="Deine heutigen Termine sind."
            for row in rows:
                datum_str = row[2]
                datum = datetime.strptime(datum_str, "%Y-%m-%d").date()
                if datum == heute or (row[6].lower() == "weekly" and datum.weekday() == heute.weekday()):
                    start = row[3][:5] if row[3] else ""  
                    ende = row[4][:5] if row[4] else ""
                    speak_text+=(f"von {start} bis {ende} Uhr {row[1]}.")
                    text += f"{start}-{ende} {row[1]} <br>"
                    waittime+=4000
            # Neues unabhängiges Label-Fenster
            self.talk(speak_text)
            self.termine_label = RoundedLabel(text, width=200, parent=self)
            QtCore.QTimer.singleShot(2000, self.termine_label.show)
            QtCore.QTimer.singleShot(waittime, self.termine_label.hide)
            QtCore.QTimer.singleShot(waittime+100, self.showToDo)
        else:
            text = "<b>Hallo Yannick</b>,"
            if self.DB_Update_Status:
                text += '<b style="color:green;">     &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;●</b>'
            else:
                text += '<b style="color:red;">     &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;●</b>'
            text+="<br>Du hast heute keine Termine:<br>"
            waittime=4000
            speak_text="Du hast heute keine Termine, entspannt" 
           
            self.talk(speak_text)
            self.termine_label = RoundedLabel(text, width=200, parent=self)
            QtCore.QTimer.singleShot(2000, self.termine_label.show)
            QtCore.QTimer.singleShot(waittime, self.termine_label.hide)
            QtCore.QTimer.singleShot(waittime+100, self.showToDo)

    def showToDo(self):
        #self.talk("Deine heutigen Termine sind.")
        rows = fetch_todo()
        if rows:
            heute = date.today()
            text = ""
            if self.DB_Update_Status:
                text += '<b style="color:green;">     &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;●</b>'
            else:
                text += '<b style="color:red;">     &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;●</b>'
            text+="<br><b>To Do:</b><br>"
            waittime=2000
            speak_text="Deine offenen Aufgaben sind."
            for row in rows:
                datum_str = row[2]
                datum = datetime.strptime(datum_str, "%Y-%m-%d").date()
                if row[4] != "done":
                    days = (datum - heute).days
                    if days < -1:
                        text += '<b style="color:red;">'
                        text += f"- {row[1]} Überfällig seit {days * (-1)} Tagen<br>"
                        text +=  '</b>'
                        speak_text+= f"{row[1]} Überfällig {days * (-1)} Tagen."
                    elif days == 1:
                        text += f"- {row[1]} fällig morgen <br>"
                        speak_text+= f"{row[1]} fällig morgen."
                    elif days == -1:
                        text += '<b style="color:red;">'
                        text += f"- {row[1]} Überfällig seit Gestern <br>"
                        text +=  '</b>'
                        speak_text+=f"{row[1]} Überfällig seit Gestern."
                    elif days > 0:
                        text += f"- {row[1]} fällig in {days} Tagen <br>"
                        speak_text+=f"{row[1]} fällig in {days} Tagen."
                    elif days == 0:
                        text += '<b style="color:yellow;">'
                        text += f"- {row[1]} fällig heute  <br>"
                        text +=  '</b>'
                        speak_text+=f"{row[1]} fällig heute."
                    waittime+=2000
            # Neues unabhängiges Label-Fenster
            self.talk(speak_text)
            self.todo_label = RoundedLabel(text, width=250, parent=self)
            QtCore.QTimer.singleShot(2000, self.todo_label.show)
            QtCore.QTimer.singleShot(waittime, self.todo_label.hide)
        else:
            text = ""
            if self.DB_Update_Status:
                text += '<b style="color:green;">     &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;●</b>'
            else:
                text += '<b style="color:red;">     &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;●</b>'
            text+="<br><b>Du hast keine offenen Aufgaben</b><br>"
            waittime=4000
            speak_text="Du hast keine offenen Aufgaben, gratulation."
            # Neues unabhängiges Label-Fenster
            self.talk(speak_text)
            self.todo_label = RoundedLabel(text, width=200, parent=self)
            QtCore.QTimer.singleShot(2000, self.todo_label.show)
            QtCore.QTimer.singleShot(waittime, self.todo_label.hide)
        QtCore.QTimer.singleShot(waittime,self.aktivate_wakeword_state)
    
    def aktivate_wakeword_state(self):
        self.wakeword_state = True
        print("Wake-Word aktivated")

    def updateLabelPosition(self):
        if hasattr(self, "termine_label") and self.termine_label.isVisible():
            x = self.x() + (self.pet_width - self.termine_label.width()) // 2
            y = self.y() - self.termine_label.height() - 10  # 10px Abstand über dem Pet
            self.termine_label.move(max(0, x), max(0, y))  # nicht außerhalb vom Bildschirm
        if hasattr(self, "hello_label") and self.hello_label.isVisible():
            x = self.x() + (self.pet_width - self.hello_label.width()) // 2
            y = self.y() - self.hello_label.height() - 10  # 10px Abstand über dem Pet
            self.hello_label.move(max(0, x), max(0, y))  # nicht außerhalb vom Bildschirm
        if hasattr(self, "todo_label") and self.todo_label.isVisible():
            x = self.x() + (self.pet_width - self.todo_label.width()) // 2
            y = self.y() - self.todo_label.height() - 10  # 10px Abstand über dem Pet
            self.todo_label.move(max(0, x), max(0, y))  # nicht außerhalb vom Bildschirm

    def internet_verfuegbar(self, host="8.8.8.8", port=53, timeout=3):

        try:
            socket.setdefaulttimeout(timeout)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((host, port))
            s.close()
            return True
        except Exception:
            return False

    def updateTermineDB(self):
        try:
            # -------- ONLINE DB --------
            connectionOnline = get_pg_connection()
            cursorOnline = connectionOnline.cursor()

            cursorOnline.execute("""
                SELECT name, datum, uhrzeitstart, uhrzeitende, ort, repeate
                FROM termine
                ORDER BY datum
            """)
            dataOnline = cursorOnline.fetchall()
            connectionOnline.close()

            # -------- OFFLINE SQLite --------
            connectionOffline = sqlite3.connect(DB_PATH)
            cursorOffline = connectionOffline.cursor()

            for name, datum, uhrzeitstart, uhrzeitende, ort, repeate in dataOnline:

                # 🔑 KONVERTIEREN
                datum_str = datum.isoformat() if datum else None
                start_str = uhrzeitstart.isoformat() if uhrzeitstart else None
                ende_str = uhrzeitende.isoformat() if uhrzeitende else None

                cursorOffline.execute("""
                    SELECT 1
                    FROM termine
                    WHERE name = ? AND datum = ?
                    LIMIT 1
                """, (name, datum_str))

                exists = cursorOffline.fetchone() is not None

                if not exists:
                    cursorOffline.execute("""
                        INSERT INTO termine
                        (name, datum, uhrzeitstart, uhrzeitende, ort, repeate, synchronized, deletflag)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (name, datum_str, start_str, ende_str, ort, repeate,True,False))

            connectionOffline.commit()
            connectionOffline.close()

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Fehler", str(e))
            return False
        try:
            
            connectionOffline = sqlite3.connect(DB_PATH)
            cursorOffline = connectionOffline.cursor()
            
            connectionOnline = get_pg_connection()
            cursorOnline = connectionOnline.cursor()

            cursorOffline.execute("""
                SELECT name, datum
                FROM termine WHERE deletflag = ?
            """,(1,))
            dataOffline = cursorOffline.fetchall()

            for name, datum_str in dataOffline:
                cursorOnline.execute("""
                    DELETE FROM termine
                    WHERE name = %s AND datum = %s
                """, (name, datum_str))

                        
            cursorOffline.execute("""
                DELETE
                FROM termine WHERE deletflag = ?
            """,(1,))

            connectionOffline.commit()
            connectionOffline.close()
            connectionOnline.commit()
            connectionOnline.close()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Fehler", str(e))
            return False
        return True
    
    def updateToDoDB(self):
        try:
            # -------- ONLINE DB --------
            connectionOnline = get_pg_connection()
            cursorOnline = connectionOnline.cursor()

            cursorOnline.execute("""
                SELECT name, text, date, status
                FROM todo
                ORDER BY date
            """)
            dataOnline = cursorOnline.fetchall()
            connectionOnline.close()

            # -------- OFFLINE SQLite --------
            connectionOffline = sqlite3.connect(DB_PATH)
            cursorOffline = connectionOffline.cursor()

            for name, text, date, state_online in dataOnline:
       

                # 🔑 KONVERTIEREN
                datum_str = date.isoformat() if date else None
                

                cursorOffline.execute("""
                    SELECT text, state
                    FROM todo
                    WHERE name = ? AND date = ? 
                    LIMIT 1
                """, (name, datum_str))

                row = cursorOffline.fetchone() 

                if row is None:
                    # ---- INSERT ----
                    cursorOffline.execute("""
                        INSERT INTO todo
                        (name, date, text, state, synchronized, deletflag)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (name, datum_str, text, state_online, 1, 0))
                else:
                    text_offline, state_offline = row

                    if text_offline != text or state_offline != state_online:
                        # ---- UPDATE ----
                        cursorOffline.execute("""
                            UPDATE todo
                            SET text=?, state=?, synchronized=?, deletflag=?
                            WHERE name=? AND date=?
                        """, (text, state_online, 1, 0, name, datum_str))



                
    

            connectionOffline.commit()
            connectionOffline.close()

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Fehler online -> offline", str(e))
            return False
        
        #delet offline -> online
        try:
            
            connectionOffline = sqlite3.connect(DB_PATH)
            cursorOffline = connectionOffline.cursor()
            
            connectionOnline = get_pg_connection()
            cursorOnline = connectionOnline.cursor()

            cursorOffline.execute("""
                SELECT name, date
                FROM todo WHERE deletflag = ?
            """,(1,))
            dataOffline = cursorOffline.fetchall()

            for name, datum_str in dataOffline:
                cursorOnline.execute("""
                    DELETE FROM todo
                    WHERE name = %s AND date = %s
                """, (name, datum_str))

                        
            cursorOffline.execute("""
                DELETE
                FROM todo WHERE deletflag = ?
            """,(1,))

            connectionOffline.commit()
            connectionOffline.close()
            connectionOnline.commit()
            connectionOnline.close()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Fehler delet offline -> online", str(e))
            return False
        return True


    def updateWebsiteDB(self):
        try:
            # -------- ONLINE DB --------
            connectionOnline = get_pg_connection()
            cursorOnline = connectionOnline.cursor()

            cursorOnline.execute("""
                SELECT name, url
                FROM websites
            """)
            dataOnline = cursorOnline.fetchall()
            connectionOnline.close()

            # -------- OFFLINE SQLite --------
            connectionOffline = sqlite3.connect(DB_PATH)
            cursorOffline = connectionOffline.cursor()

            for name, url in dataOnline:

                cursorOffline.execute("""
                    SELECT 1
                    FROM websites
                    WHERE name = ? AND url = ?
                    LIMIT 1
                """, (name, url))

                exists = cursorOffline.fetchone() is not None

                if not exists:
                    cursorOffline.execute("""
                        INSERT INTO websites
                        (name, url,synchronized,deletflag)
                        VALUES (?, ?,?,?)
                    """, (name, url,True,False))

            connectionOffline.commit()
            connectionOffline.close()

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Fehler", str(e))
            return False
        try:
            
            connectionOffline = sqlite3.connect(DB_PATH)
            cursorOffline = connectionOffline.cursor()
            
            connectionOnline = get_pg_connection()
            cursorOnline = connectionOnline.cursor()

            cursorOffline.execute("""
                SELECT name, url
                FROM websites WHERE deletflag = ?
            """,(True,))
            dataOffline = cursorOffline.fetchall()

            for name, url in dataOffline:

                cursorOnline.execute("""
                    DELETE
                    FROM websites
                    WHERE name = %s AND url = %s
                """, (name, url))
            
            cursorOffline.execute("""
                DELETE FROM websites WHERE deletflag = ?
            """,(True,))

            connectionOffline.commit()
            connectionOffline.close()

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Fehler", str(e))
            return False
        return True

    def resume_walk(self):
        self.behavior=PetBehavior.WALK
        self.wait_at_target_timer.stop()
        self.walk_step_timer.start()

    def start_countdown(self):
        try:
            minutes = int(self.minutes_input.text()) if self.minutes_input.text() else 0
            seconds = int(self.seconds_input.text()) if self.seconds_input.text() else 0
            total_seconds = minutes * 60 + seconds
            if total_seconds <= 0:
                raise ValueError
        except ValueError:
            self.minutes_input.setText("")
            self.seconds_input.setText("")
            self.minutes_input.setPlaceholderText("Min>0")
            self.seconds_input.setPlaceholderText("Sek>0")
            return

        self.countdown_time = total_seconds
        self.minutes_input.hide()
        self.seconds_input.hide()

        self.update_timer_label()
        self.timer_label.show()
        self.countdown_timer.start(1000)

    def update_timer_label(self):
        minutes = self.countdown_time // 60
        seconds = self.countdown_time % 60
        self.timer_label.setText(f"{minutes:02}:{seconds:02}")
        x = (self.pet_width - self.timer_label.width()) // 2
        y = 5
        self.timer_label.move(x, y)

    def update_timer_label_position(self):
        x = (self.pet_width - self.timer_label.width()) // 2
        y = 5  # z.B. oben innerhalb des Pets
        self.timer_label.move(x, y)

    def calculate_run_start(self):
        if self.timer_target_x is None:
            self.timer_target_x = self.get_screen_center()

        distance = abs(self.timer_target_x - self.position_x)
        step_time_sec = RUNSPEED / 1000  
        steps_needed = distance / RUNSTEPSIZE
        
        total_time = steps_needed * step_time_sec
        return total_time + 1  

    def update_countdown(self):
        self.countdown_time -= 1

        self.timer_target_x = self.get_screen_center()

        time_needed = self.calculate_run_start()
        if self.countdown_time <= time_needed and self.behavior != PetBehavior.TIMER:
            self.behavior_bevor_timer = self.behavior
            self.behavior = PetBehavior.TIMER
            self.walk_step_timer.stop()
            self.run_step_timer.start(RUNSPEED)
            if self.position_x > self.timer_target_x:
                self.direktion = PetDirektion.LEFT
            else:
                self.direktion = PetDirektion.RIGTH
        if self.countdown_time <= 0:
            self.timer_label.hide()
            self.countdown_timer.stop()
        else:
            minutes = self.countdown_time // 60
            seconds = self.countdown_time % 60
            self.timer_label.setText(f"{minutes:02}:{seconds:02}")
            self.update_timer_label_position()

    def get_screen_center(self):
        mouse_pos = QtGui.QCursor.pos()
        app = QtWidgets.QApplication.instance()
        screen = app.screenAt(mouse_pos)
        if not screen:
            screen = app.primaryScreen()
        screen_geo = screen.geometry()
        return screen_geo.x() + (screen_geo.width() - self.pet_width) // 2

    def start_jump_sequence(self, message):

        self.move(self.position_x, self.position_y)
        self.show()
        self.timeout_label = QtWidgets.QLabel(message)
        self.timeout_label.setWindowFlags(
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnTopHint |
            QtCore.Qt.Tool  
        )
        self.timeout_label.setStyleSheet("""
            background-color: rgba(0, 0, 0, 200);
            color: red;
            font-weight: bold;
            border-radius: 5px;
            padding: 5px;
        """)
        self.timeout_label.adjustSize()
        x = self.x() + (self.pet_width - self.timeout_label.width()) // 2
        y = self.y() - self.timeout_label.height() - 10  # 10px Abstand nach oben

        self.timeout_label.move(x, y)

        self.timeout_label.show()
 
        QtCore.QTimer.singleShot(3000, self.timeout_label.hide)
        

        self.jump_timer = QtCore.QTimer()
        self.jump_timer.timeout.connect(self.perform_jump)
        self.jump_timer.start(600)

    def get_total_screen_geometry(self):
        app = QtWidgets.QApplication.instance()
        screens = app.screens()

        # Gesamtfläche berechnen (damit es sich zwischen allen bewegen kann)
        rect = QtCore.QRect()
        for screen in screens:
            rect = rect.united(screen.geometry())

        # Alle Screen-Geometrien speichern, damit das Pet weiß, wo Böden sind
        self.screen_geometries = [s.geometry() for s in screens]

        return rect

    def get_current_screen_geometry(self):
        app = QtWidgets.QApplication.instance()
        for screen in app.screens():
            geo = screen.geometry()
            if (geo.x() <= self.position_x <= geo.x() + geo.width() and
                geo.y() <= self.position_y <= geo.y() + geo.height()):
                return geo
        # Fallback: Hauptbildschirm
        return app.primaryScreen().geometry()

    def get_current_screen_bottom(self):
        """Finde den Boden (unteren Rand) des Bildschirms, auf dem das Pet gerade steht."""
        for geo in self.screen_geometries:
            if geo.x() <= self.position_x <= geo.x() + geo.width():
                return geo.y() + geo.height() - self.pet_height
        # Falls außerhalb – verwende globalen Boden
        return self.total_geometry.y() + self.total_geometry.height() - self.pet_height

    def perform_jump(self):
        self.jump_base_y = self.position_y
        sequence = [
            (0,  lambda: self.new_frame("_shime1-5.png.png")),
            (60,  lambda: self.new_frame("_shime1-1.png.png")),
            (100,  lambda: self.jump_offset(-7)),
            (140,  lambda: self.jump_offset(-15)),
            (180,  lambda: self.jump_offset(-22)),
            (220,  lambda: self.jump_offset(-30)),
            (260,  lambda: self.jump_offset(-38)),
            (300,  lambda: self.jump_offset(-45)),
            (340,  lambda: self.jump_offset(-38)),
            (380,  lambda: self.jump_offset(-30)),
            (420,  lambda: self.jump_offset(-22)),
            (460,  lambda: self.jump_offset(-15)),
            (500,  lambda: self.jump_offset(-7)),
            (540,  lambda: self.jump_offset(0)),
        ]
        for delay, action in sequence:
            QtCore.QTimer.singleShot(delay, action)

        if self.behavior == PetBehavior.TIMER:
            QtCore.QTimer.singleShot(530, self.check_jump_count)

        if self.behavior == PetBehavior.WECKER:
             QtCore.QTimer.singleShot(530, self.check_jump_count)
        
    def check_jump_count(self):
        self.jump_count += 1
        if self.jump_count == 4:
            self.jump_count = 0
            self.jump_timer.stop()
            self.behavior=self.behavior_bevor_timer
            if self.behavior== PetBehavior.WALK:
               self.resume_walk()
            if self.behavior==PetBehavior.STAY:
                self.stay()

    def jump_offset(self, rel_y: int):
        self.position_y = self.jump_base_y + rel_y
        self.move(self.position_x, self.position_y)

    def show_context_menu(self, position):
        menu = QtWidgets.QMenu()
        walk_text = "stop walk" if self.behavior == PetBehavior.WALK else "start walk"
        walk_action = menu.addAction(walk_text)
        stay_action = menu.addAction("Stay")
        go_home_action = menu.addAction("Go Home")
        clone_action = menu.addAction("Clone")
        updateDB_action = menu.addAction("updateDBs")
        # Work submenu
        work_menu = menu.addMenu("Work on")
        website_menu = menu.addMenu("Website")
        termine_menu = menu.addMenu("Termine")
        todo_menu = menu.addMenu("To Do")

        # Termine aus offlien DB laden
        self.termine_actions = {}
        rows = fetch_termine()
        heute = date.today()
        for row in rows:
            datum_str = row[2]  # z. B. "2026-01-14"
            datum = datetime.strptime(datum_str, "%Y-%m-%d").date()  # in date konvertieren
            if datum == date.today() or (row[6].lower() == "weekly" and datum.weekday() == date.today().weekday()):
                start = row[3][:5] if row[3] else ""  # "14:30:00" -> "14:30"
                ende = row[4][:5] if row[4] else ""
                action = termine_menu.addAction(f"{row[1]}  {start}-{ende} : {row[5]}")
                self.termine_actions[row[0]] = f"{row[2]}  {row[3]}-{row[4]} : {row[5]}"
        termine_menu.addSeparator()
        edit_termine_action = termine_menu.addAction("Edit")

        self.todo_actions = {}
        rows = fetch_todo()
        for row in rows:
            if row[4] != "done":
                datum_str = row[2]  # z. B. "2026-01-14"
                datum = datetime.strptime(datum_str, "%Y-%m-%d").date()  # in date konvertieren  
                action = todo_menu.addAction(f"{row[1]}  {row[2]} ")  
                self.todo_actions[row[0]] = f"{row[1]} "
        todo_menu.addSeparator()
        edit_todo_action = todo_menu.addAction("Edit")

        # Websites aus Supabase laden
        self.website_actions = {}
        rows = fetch_websites()
        for row in rows:
            action = website_menu.addAction(row[1])
            self.website_actions[action] = row[2]
        website_menu.addSeparator()
        edit_website_action = website_menu.addAction("Edit")

        # Restliche Menüaktionen
        menu.addSeparator()
        change_action = menu.addAction("Change")
        timer_toggle_action = menu.addAction("Timer")
        wecker_toggle_action = menu.addAction("Wecker")
        menu.addSeparator()
        exit_action = menu.addAction("Sleep")
        close_action = menu.addAction("Close")

        # Auswahl
        action = menu.exec_(self.mapToGlobal(position))
        if not action:
            return
        # Webseiten öffnen
        if action in getattr(self, "website_actions", {}):
            self.open_webpage(self.website_actions[action])
            return
        # Termine editieren
        if action == edit_termine_action:
            viewer = TerminViewer(self)
            viewer.exec_()
        if action == edit_todo_action:
            viewer = ToDoViewer(self)
            viewer.exec_()
        if action == edit_website_action:
            viewer = WebsiteViewer(self)
            viewer.exec_()
        if action == close_action:
            QtWidgets.QApplication.quit()
        if action == updateDB_action:
            text=""
            c="black"
            if self.internet_verfuegbar():
                if self.updateTermineDB() and self.updateWebsiteDB() and self.updateToDoDB():
                    text="Synchronised"
                    c="green"
                else:
                    text="Failed"
                    c="red"
            else:
                text="No Internet"
                c="red"
                
            self.hello_label = RoundedLabel(text, width=100, colour=c, parent=self)
            # Position über dem Pet
            self.hello_label.show()
            self.updateLabelPosition()

            # Timer erstellen, um Label nach 4 Sekunden zu verstecken
            QtCore.QTimer.singleShot(2000, self.hello_label.hide)
        # Walk / Stop Walk
        if action == walk_action:
            if self.behavior == PetBehavior.WALK:
                self.stay()
            else:
                self.behavior = PetBehavior.WALK
                self.walk_step_timer.start()

        # Stay
        if action == stay_action:
            self.stay()

        # Go Home
        if action == go_home_action:
            self.behavior = PetBehavior.GOHOME
            self.go_home()

        # Clone
        if action == clone_action:
            clone = DesktopPet()
            clone.show()
            clones.append(clone)

        # Timer
        if action == timer_toggle_action:
            self.minutes_input.show()
            self.seconds_input.show()
            self.minutes_input.setFocus()

        # Wecker
        if action == wecker_toggle_action:
            self.open_wecker_window()

        # Change (zufällige Farbe wechseln)
        if action == change_action:
            options = [BLUE, GREEN, PURPLE, RED]
            options.remove(self.colour)
            self.colour = random.choice(options)
            self.update_frame()

        # Sleep (Pet ausblenden)
        if action == exit_action:
            self.hide()

    def open_wecker_window(self):
    # Neues QDialog-Fenster
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Wecker stellen")
        dialog.setWindowModality(QtCore.Qt.ApplicationModal)
        dialog.setWindowFlags(dialog.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        dialog.setFixedSize(250, 120)

        layout = QtWidgets.QVBoxLayout(dialog)

        # Uhrzeit-Eingabe
        self.wecker_time_edit = QtWidgets.QTimeEdit()
        self.wecker_time_edit.setDisplayFormat("HH:mm")
        layout.addWidget(QtWidgets.QLabel("Wecker stellen:"))
        layout.addWidget(self.wecker_time_edit)

        # Start-Button
        start_btn = QtWidgets.QPushButton("Wecker starten")
        start_btn.clicked.connect(lambda: self.start_alarm(dialog))
        layout.addWidget(start_btn)

        # Timer vorbereiten
        self.wecker_timer = QtCore.QTimer()
        self.wecker_timer.timeout.connect(self.check_alarm)
        self.wecker_alarm_time = None

        dialog.exec_()

    def start_alarm(self, dialog):
        self.wecker_alarm_time = self.wecker_time_edit.time().toPyTime()
        QtWidgets.QMessageBox.information(self, "Wecker", f"Wecker gestellt auf {self.wecker_alarm_time}")
        self.wecker_timer.start(1000)  # jede Sekunde prüfen
        dialog.close()  # Fenster schließen

    def check_alarm(self):
        now = datetime.datetime.now().time()
        if self.wecker_alarm_time is None:
            return

        # Prüfen Stunde & Minute
        if now.hour == self.wecker_alarm_time.hour and now.minute == self.wecker_alarm_time.minute:
            self.wecker_timer.stop()

            # Pet auf Timer/Wecker-Modus setzen
            self.behavior_bevor_timer = self.behavior
            self.behavior = PetBehavior.WECKER
            self.walk_step_timer.stop()
            self.run_step_timer.start(RUNSPEED)

            
            self.timer_target_x = self.get_screen_center()
            if self.position_x > self.timer_target_x:
                self.direktion = PetDirektion.LEFT
            else:
                self.direktion = PetDirektion.RIGTH

    def open_webpage(self, url):
        import subprocess
        import time

        try:
            subprocess.Popen(["firefox", "--new-tab", url])
            time.sleep(0.5)  
            try:
                subprocess.Popen(["wmctrl", "-a", "Mozilla Firefox"])
            except FileNotFoundError:
                pass  
        except FileNotFoundError:
            import webbrowser
            webbrowser.open(url)

    def open_vscode(self):
        import subprocess
        try:
            subprocess.Popen(["code", "/home/yannick/Projekts"])
        except FileNotFoundError:
            print("Fehler: VS Code (code) wurde nicht gefunden. Stelle sicher, dass es im PATH ist.")

    def open_terminal(self):
        import subprocess
        import os

        # Pfad zum Projektordner
        project_path = "/home/yannick/Projekts"

        # Prüfen, ob Ordner existiert
        if not os.path.exists(project_path):
            print(f"❌ Ordner existiert nicht: {project_path}")
            return

        try:
            # Terminal öffnen und direkt in den Ordner wechseln
            subprocess.Popen(["gnome-terminal", "--working-directory", project_path])
        except FileNotFoundError:
            print("❌ Terminal nicht gefunden. Versuche x-terminal-emulator...")
            try:
                subprocess.Popen(["x-terminal-emulator", "--working-directory", project_path])
            except Exception as e:
                print("❌ Fehler beim Öffnen des Terminals:", e)

    def go_home(self):
        self.total_geometry = self.get_total_screen_geometry()
        self.screen_geometries = [s.geometry() for s in QtWidgets.QApplication.instance().screens()]
        screens = QtWidgets.QApplication.instance().screens()
        lowest_screen = max(screens, key=lambda s: s.geometry().y() + s.geometry().height())
        screen_geo = lowest_screen.geometry()
        self.target_x=self.total_geometry.x() + self.total_geometry.width() - self.pet_width
        self.walk_step_timer.start()
        
    def stay(self):
        self.behavior=PetBehavior.STAY
        self.walk_step_timer.stop()
        self.walking_step=0
        self.new_frame("_shime1-5.png.png")
        
    def fall_step(self):
        dy = self.target_y - self.position_y
        if dy > 0:
            # Sanftes Fallen
            step = min(FALLSTEP, dy)
            self.position_y += step
            self.move(int(self.position_x), int(self.position_y))
            self.new_frame("_shime1-4.png.png")
            
        else: 
            self.fall_timer.stop()
            # Boden erreicht
            self.position_y = self.target_y
            self.move(int(self.position_x), int(self.position_y))
           
            self.behavior=self.behavior_bevor_fall
            # Kette von Frame-Änderungen mit Verzögerung
            self.new_frame("_shime1-6.png.png")
            QtCore.QTimer.singleShot(150, lambda: self.new_frame("_shime1-7.png.png"))
            QtCore.QTimer.singleShot(2000, lambda: self.new_frame("_shime1-5.png.png"))
            if not self.behavior==PetBehavior.STAY:
                QtCore.QTimer.singleShot(2100, lambda: self.new_frame("_shime1-1.png.png"))
            if self.behavior== PetBehavior.WALK:
                QtCore.QTimer.singleShot(2200, lambda: self.walk_step_timer.start())
                
    def take_step(self):
        if self.behavior==PetBehavior.WALK or self.behavior==PetBehavior.GOHOME:
            if self.check_target():
                return
            if self.behavior==PetBehavior.WALK or self.behavior==PetBehavior.GOHOME:
                if(self.walking_step==0 or self.walking_step==1 ):
                    self.walking_step +=1
                    new_image_path = "_shime1-1.png.png"
                elif(self.walking_step==2 or self.walking_step==3):
                    self.walking_step +=1
                    new_image_path = "_shime1-2.png.png"
                elif(self.walking_step==4 or self.walking_step==5):
                    self.walking_step +=1
                    new_image_path = "_shime1-1.png.png"
                elif(self.walking_step==6 or self.walking_step==7 ):
                    self.walking_step += 1
                    if(self.walking_step==8):
                        self.walking_step = 0
                    new_image_path = "_shime1-3.png.png"
                
                if self.direktion==PetDirektion.LEFT:
                    self.position_x -= STEPSIZE 
                elif self.direktion==PetDirektion.RIGTH:
                    self.position_x += STEPSIZE
                self.move(self.position_x,self.position_y)
                self.new_frame(new_image_path)
                self.updateLabelPosition()

    def take_run_step(self):
        if abs(self.position_x-self.timer_target_x) < 5:
            self.run_step_timer.stop()
            new_image_path = "_shime1-1.png.png"
            if(PetBehavior.TIMER==self.behavior):
                self.start_jump_sequence("Timer abgelaufen")
            if(PetBehavior.WECKER==self.behavior):
                self.start_jump_sequence("Wecker")
            return
        if(self.walking_step==0 or self.walking_step==1 ):
            self.walking_step +=1
            new_image_path = "_shime1-1.png.png"
        elif(self.walking_step==2 or self.walking_step==3):
            self.walking_step +=1
            new_image_path = "_shime1-2.png.png"
        elif(self.walking_step==4 or self.walking_step==5):
            self.walking_step +=1
            new_image_path = "_shime1-1.png.png"
        elif(self.walking_step==6 or self.walking_step==7 ):
            self.walking_step += 1
            if(self.walking_step==8):
                self.walking_step = 0
            new_image_path = "_shime1-3.png.png"

        if self.direktion==PetDirektion.LEFT:
            self.position_x -= RUNSTEPSIZE 
        elif self.direktion==PetDirektion.RIGTH:
            self.position_x += RUNSTEPSIZE
        self.move(self.position_x,self.position_y)
        self.new_frame(new_image_path)

    def check_target(self):
        if abs(self.position_x - self.target_x) < 6:
            self.new_frame("_shime1-1.png.png")
            if self.behavior == PetBehavior.GOHOME:
                self.walk_step_timer.stop()
                self.direktion = PetDirektion.LEFT
                self.stay()
                return True

            self.behavior = PetBehavior.WAIT

            # --- Bildschirmbegrenzung für Ziel ---
            screen_geo = self.get_current_screen_geometry()
            min_x = screen_geo.x()
            max_x = screen_geo.x() + screen_geo.width() - self.pet_width
            self.target_x = random.randint(min_x, max_x)

            self.wait_at_target_timer.start()
            self.walk_step_timer.stop()

        # Richtung setzen
        if self.position_x > self.target_x:
            self.direktion = PetDirektion.LEFT
        else:
            self.direktion = PetDirektion.RIGTH

    def new_frame(self, url:str): 
        self.original_pixmap = QtGui.QPixmap("/home/yannick/Projects/DesktopPet/Pet/blue_black_boy/"+self.colour+url).scaled(
            self.pet_width,
            self.pet_height,
            QtCore.Qt.KeepAspectRatio,
            QtCore.Qt.SmoothTransformation
        )
        if self.direktion==PetDirektion.LEFT:
            self.setPixmap(self.original_pixmap)
        elif self.direktion==PetDirektion.RIGTH:
            flipped = self.original_pixmap.transformed(QtGui.QTransform().scale(-1, 1))
            self.setPixmap(flipped)
        self.current_path=url
        self.show()

    def update_frame(self):
        self.original_pixmap = QtGui.QPixmap("/home/yannick/Projects/DesktopPet/Pet/blue_black_boy/"+self.colour+self.current_path).scaled(
            self.pet_width,
            self.pet_height,
            QtCore.Qt.KeepAspectRatio,
            QtCore.Qt.SmoothTransformation
        )
        if self.direktion==PetDirektion.LEFT:
            self.setPixmap(self.original_pixmap)
        elif self.direktion==PetDirektion.RIGTH:
            flipped = self.original_pixmap.transformed(QtGui.QTransform().scale(-1, 1))
            self.setPixmap(flipped)
        self.show()

    def drag_follow_step(self):
        current_pos = self.pos()
        target_pos = self.drag_target_pos

        dist_x = target_pos.x() - current_pos.x()
        dist_y = target_pos.y() - current_pos.y()

        speed_x = max(5, min(30, abs(dist_x) / 5))
        speed_y = max(5, min(30, abs(dist_y) / 5))

        new_x = target_pos.x() if abs(dist_x) <= speed_x else current_pos.x() + speed_x if dist_x > 0 else current_pos.x() - speed_x
        new_y = target_pos.y() if abs(dist_y) <= speed_y else current_pos.y() + speed_y if dist_y > 0 else current_pos.y() - speed_y
        
        self.move(int(new_x), int(new_y))

        if not self.dragging and abs(dist_x) == 0 and abs(dist_y) == 0:
            self.drag_follow_timer.stop()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.walk_step_timer.stop()
            self.wait_at_target_timer.stop()
            self.behavior_bevor_fall=self.behavior
            self.behavior = PetBehavior.FALLING
            self.new_frame("_shime1-1.png.png")
            self.dragging = True
            self.drag_offset = event.pos()
            if self.fall_timer.isActive():
                self.fall_timer.stop()
            if not self.drag_follow_timer.isActive():
                self.drag_follow_timer.start(30)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.dragging:
            global_pos = event.globalPos()
            new_x = global_pos.x() - self.drag_offset.x()
            new_y = global_pos.y() - self.drag_offset.y()

            self.position_x = int(max(self.total_geometry.x(), min(new_x, self.total_geometry.x() + self.total_geometry.width() - self.pet_width)))
            self.position_y = int(max(self.total_geometry.y(), min(new_y, self.total_geometry.y() + self.total_geometry.height() - self.pet_height)))

            self.drag_target_pos = QtCore.QPoint(new_x, new_y)
            self.move(self.position_x, self.position_y)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton and self.dragging:
            self.dragging = False
            self.behavior = PetBehavior.FALLING

            # Stelle sicher, dass Dragging stoppt
            if self.drag_follow_timer.isActive():
                self.drag_follow_timer.stop()

            # Bildschirm-Geometrien holen
            screens = QtWidgets.QApplication.instance().screens()
            screen_geos = [s.geometry() for s in screens]

            # Finde Bildschirm unter dem Pet
            current_geo = None
            for geo in screen_geos:
                if geo.x() <= self.position_x <= geo.x() + geo.width():
                    current_geo = geo
                    break

            # Wenn wir einen Bildschirm gefunden haben:
            if current_geo:
                # Boden dieses Screens
                screen_bottom = current_geo.y() + current_geo.height() - self.pet_height

                # Wenn das Pet unterhalb dieses Bodens ist (z. B. zwischen Screens)
                if self.position_y > screen_bottom:
                    # Suche nächsten tieferliegenden Screen (unterhalb)
                    lower_screens = [g for g in screen_geos if g.y() > current_geo.y()]
                    if lower_screens:
                        # Untersten nehmen
                        lower_screen = min(lower_screens, key=lambda g: g.y())
                        self.target_y = lower_screen.y() + lower_screen.height() - self.pet_height
                    else:
                        self.target_y = screen_bottom
                else:
                    # Bleibe auf dem aktuellen Screenboden
                    self.target_y = screen_bottom
            else:
                # Fallback: niedrigster Bildschirmboden
                lowest = max(screen_geos, key=lambda g: g.y() + g.height())
                self.target_y = lowest.y() + lowest.height() - self.pet_height

            # Starte sanftes Fallen
            if not self.fall_timer.isActive():
                self.fall_timer.start(5)
            event.accept()
        else:
            super().mouseReleaseEvent(event)



if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)

    pet = DesktopPet()
    pet.show()

    sys.exit(app.exec_())
