import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW

class Base:

    basebox = None

    def __init__(self, **kwargs):
        self.basebox = toga.Box(style=Pack(direction=COLUMN, flex=1, padding=5))

    def getbox(self):
        return self.basebox