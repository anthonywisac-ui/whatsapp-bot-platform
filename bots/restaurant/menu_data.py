import json
MENU = {}
def load_menu():
    global MENU
    with open("menu.json", "r", encoding="utf-8") as f:
        MENU = json.load(f)
def reload_menu():
    load_menu()
load_menu()
