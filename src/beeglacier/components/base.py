class Base:
    self.element = None
    self.children = {}

    def get(self):
        return self.element

    def add(self, name, element):
        self.children[name] = element
        if self.element:
            self.element.add(self.children[name])
    