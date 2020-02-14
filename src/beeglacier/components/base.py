import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
from ..utils import Controls

class Base:

    basebox = None
    __controls = None

    def __init__(self, **kwargs):
        self.__controls = Controls()
        self.basebox = toga.Box(style=Pack(direction=COLUMN, flex=1, padding=5))
        self.getcontrols().add('BaseBox', self.basebox.id)

    def getbox(self):
        return self.basebox

    def getcontrols(self):
        return self.__controls