# encoding: utf8

# Some part of the code is taken from proteus a python library to access tryton
# Copyright (C) 2010 Cédric Krier and B2CK SPRL


import base64
import datetime
import decimal
import os


class DefaultDescriptor(object):

    def __init__(self, attrname, field_def):
        self.attrname = attrname

    def __get__(self, instance, owner):
        if self.attrname not in instance._browse_values:
            try:
                instance._browse_values[self.attrname] = \
                        self.attrgetter(instance, owner)
            except KeyError:
                raise AttributeError(self.attrname)
        return instance._browse_values[self.attrname]

    def attrgetter(self, instance, owner):
        return instance._oe_values[self.attrname]

    def __set__(self, instance, value):
        instance._changed.add(self.attrname)
        instance._browse_values[self.attrname] = value
        instance._oe_values[self.attrname] = value


class FloatDescriptor(DefaultDescriptor):

    def attrgetter(self, instance, owner):
        value = instance._oe_values.get(self.attrname)
        if value:
            return decimal.Decimal(str(value))
        else:
            return decimal.Decimal(0)

    def __set__(self, instance, value):
        super(FloatDescriptor, self).__set__(instance, value)
        instance._oe_values[self.attrname] = float(value)


class M2ODescriptor(DefaultDescriptor):

    def __init__(self, attrname, field_def):
        super(M2ODescriptor, self).__init__(attrname, field_def)
        self.relation = field_def['relation']

    def attrgetter(self, instance, owner):
        browse_klass = BrowseFactory.get(instance._proxy.database,
                                         self.relation)
        if instance._oe_values[self.attrname]:
            return browse_klass(instance._oe_values[self.attrname][0])
        else:
            return None

    def __set__(self, instance, value):
        if not value:
            return
        instance._changed.add(self.attrname)
        if isinstance(value, int):
            instance._oe_values[self.attrname] = (value, '')
            if self.attrname in instance._browse_values:
                del instance._browse_values[self.attrname]
        elif isinstance(value, Browse):
            instance._oe_values[self.attrname] = (value.id, value.name)
            instance._browse_values[self.attrname] = value


class O2MDescriptor(DefaultDescriptor):

    def __init__(self, attrname, field_def):
        super(O2MDescriptor, self).__init__(attrname, field_def)
        self.relation = field_def['relation']

    def attrgetter(self, instance, owner):
        browse_klass = BrowseFactory.get(instance._proxy.database,
                                         self.relation)
        return BrowseList([browse_klass(oid)
                           for oid in instance._oe_values[self.attrname]],
                          instance, self.attrname)

    def __set__(self, instance, value):
        super(O2MDescriptor, self).__set__(instance, value)


class DTDescriptor(DefaultDescriptor):

    def attrgetter(self, instance, owner):
        value = instance._oe_values[self.attrname]
        if not value:
            return None
        return datetime.datetime.strptime(value, '%Y-%m-%d %H:%M:%S')

    def __set__(self, instance, value):
        if isinstance(value, basestring):
            value = datetime.datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        instance._changed.add(self.attrname)
        instance._browse_values[self.attrname] = value
        instance._oe_values[self.attrname] = value.strftime('%Y-%m-%d %H:%M:%S')


class DDescriptor(DTDescriptor):

    def attrgetter(self, instance, owner):
        value = instance._oe_values[self.attrname]
        if not value:
            return None
        return datetime.datetime.strptime(value, '%Y-%m-%d')

    def __set__(self, instance, value):
        if isinstance(value, basestring):
            value = datetime.datetime.strptime(value, '%Y-%m-%d')
        instance._changed.add(self.attrname)
        instance._browse_values[self.attrname] = value
        instance._oe_values[self.attrname] = value.strftime('%Y-%m-%d')


class MetaBrowser(type):

    descriptors = {'float': FloatDescriptor,
                   'many2one': M2ODescriptor,
                   'one2many': O2MDescriptor,
                   'many2many': O2MDescriptor,
                   'datetime': DTDescriptor,
                   'date': DDescriptor}

    def __init__(cls, klassname, bases, properties):
        super(MetaBrowser, cls).__init__(klassname, bases, {})
        proxy = properties['proxy']
        cls._fields = proxy.fields_get([])
        cls._proxy = proxy
        for name, field_def in cls._fields.items():
            if name == 'id':
                continue
            factory = cls.descriptors.get(field_def['type'], DefaultDescriptor)
            setattr(cls, name, factory(name, field_def))

    def __getattr__(self, attrname):
        return getattr(self._proxy, attrname)


class BrowseNotFoundError(Exception):

    def __init__(self, record_id):
        self.id = record_id


class Browse(object):

    def __init__(self, id=None, **kwargs):
        assert ((id is not None and not bool(kwargs))
                or (id is None and bool(kwargs)))
        self.id = id
        self._oe_values = {} # store the values of fields
        self._changed = set() # store the changed fields
        self._parent = None # store the parent record
        self._parent_field_name = None # store the field name in parent record
        self._browse_values = {}
        if id is not None:
            self._oe_values = self._proxy.read(id)
            if not self._oe_values:
                raise BrowseNotFoundError(id)
        else:
            for name, value in kwargs.items():
                setattr(self, name, value)

    @classmethod
    def search(cls, condition=None, offset=0, limit=None, order_by=None):
        'Return Browse instances matching condition'
        if condition is None:
            condition = []
        ids = cls._proxy.search(condition, offset, limit, order_by)
        return [cls(id) for id in ids]

    @classmethod
    def name_search(cls, name='', args=None, operator='ilike', limit=80):
        'Return Browse instances'
        return [cls(id) for id, name in cls._proxy.name_search(name, args,
                                                               operator, limit)]

    @property
    def oe_repr(self):
        value = {}
        for attrname in self._changed:
            browse_value = self._browse_values.get(attrname)
            if isinstance(browse_value, BrowseList):
                value[attrname] = browse_value.oe_repr
            elif isinstance(browse_value, Browse):
                if browse_value.id is None:
                    browse_value.save()
                value[attrname] = browse_value.id
            else:
                value[attrname] = self._oe_values[attrname]
                if isinstance(value[attrname], tuple):
                    value[attrname] = value[attrname][0]
        return value

    def save(self):
        if self.id is None:
            self.id = self._proxy.create(self.oe_repr)
        else:
            if not self._changed:
                return
            self._proxy.write([self.id], self.oe_repr)
        self.reload()

    def reload(self):
        for attrname in self._changed:
            browse_value = self._browse_values.get(attrname)
            if isinstance(browse_value, (Browse, BrowseList)):
                browse_value.reload()
        self._changed = set()
        self._browse_values = {}
        self._oe_values = self._proxy.read(self.id)

    def __cmp__(self, other):
        return cmp((self._proxy.database, self._proxy.model, self.id),
                   (other._proxy.database, other._proxy.model, other.id))

    def __str__(self):
        return '<%s %s@%s>' % (self._proxy.model, self.id,
                               self._proxy.database)

    def __getattr__(self, attrname):
        return getattr(self._proxy, attrname)


class BrowseList(list):

    def __init__(self, iterator, parent, parent_name):
        super(BrowseList, self).__init__(iterator)
        self.parent = parent
        self.parent_name = parent_name
        self.item_added = set()
        self.item_removed = set()

    def changed(self):
        self.parent._changed.add(self.parent_name)

    def reload(self):
        for item in self:
            item.reload()

    @property
    def oe_repr(self):
        value = []
        for item in self.item_added:
            if item.id is None:
                value.append((0, 0, item.oe_repr))
            else:
                value.append((4, item.id))
        for item in self.item_removed:
            if item.id is not None:
                value.append((2, item.id))
        return value

    def append(self, item):
        self.changed()
        self.item_added.add(item)
        super(BrowseList, self).append(item)

    def extend(self, iterable):
        self.changed()
        iterable = list(iterable)
        for item in iterable:
            self.item_added.add(item)
        super(BrowseList, self).extend(iterable)

    def insert(self, index, item):
        raise NotImplementedError

    def pop(self, index=-1):
        self.changed()
        item = super(BrowseList, self).pop(index)
        self.item_removed.add(item)
        self.item_added.remove(item)
        return item

    def remove(self, item):
        self.changed()
        self.item_removed.add(item)
        return super(BrowseList, self).remove(item)

    def reverse(self):
        raise NotImplementedError

    def sort(self):
        raise NotImplementedError

    def __contains__(self, item):
        return (item._proxy.database, item.id) in [(e._proxy.database, e.id)
                                                   for e in self]


class BrowseFactory(object):
    _browse_classes = {}
    _client = None

    @classmethod
    def get(cls, database, dotted_name):
        proxy = cls._client.create_proxy(database, dotted_name)
        if (database, dotted_name) not in cls._browse_classes:
            klass =  MetaBrowser(dotted_name, (Browse,), {'proxy': proxy})

            cls._browse_classes[(database, dotted_name)] = klass
        return cls._browse_classes[(database, dotted_name)]



