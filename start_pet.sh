#!/bin/bash
# start_pet.sh – startet main.py automatisch mit 2 Sekunden Verzögerung

# 2 Sekunden warten
sleep 2

# Ins Projektverzeichnis wechseln
cd ~/Projects/DesktopPet/Pet/Source

# Virtuelles Environment aktivieren (vom übergeordneten Ordner)
source ../venv/bin/activate

# Python-Skript starten
python3 main.py
