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
