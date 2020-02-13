import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
from .base import Base

class Table(Base):

    headers = []
    data = []

    toga_table = None

    def __init__(self, **kwargs):
        super().__init__()

        if 'headers' in kwargs.keys():
            # set headers. Ex.:
            # [
            #   {'name': 'vaultname',label': 'Name'},
            #   {'name': 'numberofarchives', 'label': '# Archives'},
            #   {'name': 'sizeinbytes', 'label': 'Size (MB)'},
            # ]
            self.headers = kwargs['headers']

        if 'on_row_selected' in kwargs.keys():
            # Save callback fn for row selected
            self.on_row_selected = kwargs['on_row_selected']

        # create Toga Table
        table_style = Pack(height=300,direction=COLUMN)
        self.toga_table =  toga.Table(self._get_header_labels(), 
                                      data=[], 
                                      style=table_style, 
                                      on_select=self.on_row_selected)
        self.basebox.add(self.toga_table)

    def _get_header_labels(self):
        return [header['label'] for header in self.headers]

    def _get_header_names(self):
        return [header['name'] for header in self.headers]

    def set_data(self, data):
        # [
        #   {'vaultname': 'test', 'numberofarchives': '2', 'sizeinbytes': '23.45' }
        #   {'vaultname': 'test 2', 'numberofarchives': '4', 'sizeinbytes': '60.45' }
        # ]

        filtered_data = []
        headers = self._get_header_names()
        for row in data:
            filtered_row = []
            for name in headers:
                filtered_row.append(row[name])
            filtered_data.append(filtered_row)
        
        self.toga_table.data = filtered_data
