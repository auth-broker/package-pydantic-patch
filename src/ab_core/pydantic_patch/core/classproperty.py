"""Why doesn't Python have class properties?!"""

class classproperty:
    def __init__(self, func):
        self.func = func

    def __get__(self, obj, owner):
        # owner is the class itself
        return self.func(owner)
