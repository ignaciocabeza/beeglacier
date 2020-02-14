class ObsData(object):
    def __init__(self, initial = []):
        self._data = initial
        self._observers = []

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value):
        self._data = value
        for callback in self._observers:
            callback(self._data)

    def bind_to(self, callback):
        self._observers.append(callback)

class StoreContainer:
    containers = {}

    def __init__(self):
        pass

    def add(self, name, container):
        self.containers[name] = container

class Controls:
    _controls = None
    _toga_window = None

    def __init__(self):
        self._controls = {}

    def set_window(self, window):
        self._toga_window = window

    def getall(self):
        return self._controls

    def add(self, name, id):
        if id not in self._controls.keys():
            if not self.get_id(name):
                self._controls[id] = name
            else:
                raise Exception('Name already used')    
        else: 
            raise Exception('ID already used')

    def add_from_controls(self, new_controls, prefix = ''):
        for key,value in new_controls.getall().items():
            self.add(prefix+value,key)

    def get_name(self,id):
        return self._controls[id]

    def get_id(self,name):
        
        for k,v in self._controls.items():
            if v == name:
                return k
        return None

    def get_control_by_id(self, id):

        if not self._toga_window.content:
            return None

        elements = []
        elements.append(self._toga_window.content)

        while elements:
            current = elements.pop(0)
            
            # found control
            if current.id == id:
                return current

            # check if children are in content or children attr
            content = getattr(current, 'content', None)
            to_add = None
            if content:
                to_add = content
            else:
                children = getattr(current, 'children', None)
                if children:
                    to_add = children

            # add children to next elements to check
            if to_add:
                if type(to_add) == list:
                    for el in to_add:
                        elements.append(el)
                else:
                    elements.append(el)

        return None

    def get_control_by_name(self, name):
        id = self.get_id(name)
        return self.get_control_by_id(id)