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


class BidirectionalMap(dict):
    def __init__(self, *args, **kwargs):
        super(BidirectionalMap, self).__init__(*args, **kwargs)
        self.inverse = {}
        for key, value in self.items():
            self.inverse.setdefault(value, []).append(key)

    def __setitem__(self, key, value):
        if key in self:
            self.inverse[self[key]].remove(key)
        super(BidirectionalMap, self).__setitem__(key, value)
        self.inverse.setdefault(value, []).append(key)

    def __delitem__(self, key):
        self.inverse.setdefault(self[key], []).remove(key)
        if self[key] in self.inverse and not self.inverse[self[key]]:
            del self.inverse[self[key]]
        super(BidirectionalMap, self).__delitem__(key)


if __name__ == '__main__':
    # b = BidirectionalMap({('', None): '2', ('thing', 'thingy'): '4'})
    b = BidirectionalMap({
        ('buy', None): 'buy',
        ('my', None): 'my',
        ('income', 'my'): 'income',
        ('sell', None): 'sell',
        ('sell_everything', None): 'sell_everything',
        ('all', None): 'all',
        ('company', None): 'company',
        ('companies', None): 'companies',
        ('stocks', None): 'stocks',
        ('stonks', None): 'stocks',
        ('points', 'my'): 'points',
        ('mypoints', None): 'my points',
        ('profit', 'my'): 'profit',
        ('myprofit', None): 'my profit',
        ('income', 'my'): 'income',
        ('myincome', None): 'my income',
        ('stats', 'my'): 'stats',
        ('mystats', None): 'my stats',
        ('shares', 'my'): 'shares',
        ('myshares', None): 'my shares',
        ('month', 'next'): 'month',
        ('autoinvest', None): 'autoinvest',
        ('about', None): 'about',
        ('introduction', None): 'introduction',
    })
    print(b.inverse.items())
    # pre_made_choices = []
    # for (og_name, alias_and_group_name) in b.inverse.items():
    #     for alias, group_name in alias_and_group_name:
    #         accessible_from = group_name
    #         if ' ' in og_name.strip():  # added this check to handle situations where the key is 'my points' so it's accessible from 'root'
    #             group_name, _, og_name = og_name.partition(" ")
    #
    #         pre_made_choices.append({'command': (og_name, group_name), 'alias': alias, 'group': accessible_from})

    # pre_made_choices = [{'command': (og_name, group_name), 'alias': alias, 'group': accessible_from}
    #                     for (og_name, alias_and_group_name) in b.inverse.items() for alias, group_name in alias_and_group_name]
    # print(pre_made_choices)

