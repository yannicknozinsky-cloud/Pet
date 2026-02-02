from enum import Enum

# Bewegungsschritte & Geschwindigkeit
STEPSIZE = 2
RUNSTEPSIZE = 4
FALLSPEED = 5
FALLSTEP = 1
RUNSPEED = 10

from saveconfig import *

# Verhalten des Pets
class PetBehavior(Enum):
    REST="rest"
    WALK = "walk"
    GOHOME="home"
    STAY="stay"
    FALLING="falling"
    WAIT="wait"
    TIMER ="timer"
    WECKER="wecker"

class PetDirektion(Enum):
    LEFT = "left"
    RIGTH = "rigth"

# Farben
BLUE = "blue"
GREEN = "green"
PURPLE = "purple"
RED = "red"

import psycopg2


