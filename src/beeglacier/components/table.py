import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
from .base import Base

# Relashionship between toga row and _data row.

class Table(Base):

    _headers = []
    _toga_table = None

    def __init__(self, **kwargs):
        super().__init__()

        # Observable for selected Row
        self._selected_row = None
        self._observers_selected_row = []

        # Observable for data change
        self._data = []
        self._observers_data_change = []

        if 'headers' in kwargs.keys():
            # set headers. Ex.:
            # [
            #   {'name': 'vaultname',label': 'Name'},
            #   {'name': 'numberofarchives', 'label': '# Archives'},
            #   {'name': 'sizeinbytes', 'label': 'Size (MB)'},
            # ]
            self._headers = kwargs['headers']

        # create Toga Table
        table_style = Pack(height=300,direction=COLUMN)
        self._toga_table =  toga.Table(self._get_header_labels(), 
                                      data=[], 
                                      style=table_style, 
                                      on_select=self._on_row_selected)
        self.getcontrols().add('Table', self._toga_table.id)
        self.basebox.add(self._toga_table)

    def _filter_columns(self, row):
        # filter headers to show
        headers = self._get_header_names()
        filtered_row = []
        for name in headers:
            filtered_row.append(row[name])
        return filtered_row

    @property
    def selected_row(self):
        return self._selected_row

    @selected_row.setter
    def selected_row(self, value):
        """ Only for internal use
        """
        self._selected_row = value
        for callback in self._observers_selected_row:
            callback(self._selected_row)

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value):
        """ Only for internal use
        """
        
        # [
        #   {'vaultname': 'test', 'numberofarchives': '2', 'sizeinbytes': '23.45' }
        #   {'vaultname': 'test 2', 'numberofarchives': '4', 'sizeinbytes': '60.45' }
        # ]
        
        #remove exsiting data
        self._toga_table.data = []

        self._data = value
        
        index = 0
        for row in self._data:
            self._append_wrapper(row, index)
            index += 1

        for callback in self._observers_data_change:
            callback(self._data)

        self.refresh()
    
    def _append_wrapper(self, row, index):
        """ append wrapper used by data property and append method
        """
        #filter columns
        filtered_row = self._filter_columns(row)

        # add row to table
        row_added = self._toga_table.data.append(*filtered_row)
        
        # set ids
        setattr(row_added, '___id', index)
        row['___id'] = index

        # add object row to self._data (row)
        row['_row'] = row_added

    def append(self, newrow):
        
        # get max index
        index = 0
        indexes = [ x['___id'] for x in self._data ]
        if indexes:
            index = max(indexes)

        # create new row in _data
        newrow['___id'] = index
        self._data.append(newrow)

        # add that new row to table
        row_to_add = self._data[-1]
        self._append_wrapper(row_to_add, index)

        # call the observers
        for callback in self._observers_data_change:
            callback(self._data)
    
        return index

    def update(self, index, *args, **kwargs):
        #row_to_update = list(filter(lambda x: x['___id'] == index, self._data))
        pass

    def remove(self, index):
        pass
        '''
        row_to_remove = list(filter(lambda x: x['___id'] == index, self._data))
        import pdb;pdb.set_trace()

        # call the observers
        for callback in self._observers_data_change:
            callback(self._data)
        '''

    def subscribe(self, event, callback):
        if event == 'on_select_row':
            self._observers_selected_row.append(callback)
        if event == 'on_data_change':
            self._observers_data_change.append(callback)

    def _get_header_labels(self):
        return [header['label'] for header in self._headers]

    def _get_header_names(self):
        return [header['name'] for header in self._headers]

    def _on_row_selected(self, table, row):
        """ Handler for toga.Table() on_select
        """
        if row:
            filter_row = list(filter(lambda x: x['___id'] == getattr(row, '___id'), self._data))
            if len(filter_row) > 0:
                self.selected_row = filter_row[0]

    def refresh(self):
        self._toga_table.refresh()