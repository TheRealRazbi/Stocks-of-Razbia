# The reason we're using this file for stuff instead of custom_tools.py is because custom_tools.py is packaged
# therefore not update-able


class CachedProperty:
    def __init__(self, func, name=None):
        self.name = name or func.__name__
        self.func = func

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        if self.name in instance._cache:
            return instance._cache[self.name]
        instance._cache[self.name] = ret = self.func(instance)
        return ret







