import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from whatsapp_handlers import *
from .menu_data import MENU
from .strings import t
import whatsapp_handlers as wh
wh.set_menu_and_strings(MENU, t)
# Then re-export all functions
from whatsapp_handlers import *
