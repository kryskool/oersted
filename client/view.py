# encoding: utf8

import datetime
import re
import time

import lxml.etree

from browse import Browse, BrowseList


class ViewDescriptor(object):

    def __init__(self, attrname):
        self.attrname = attrname

    def __get__(self, instance, owner):
        return getattr(instance._browse, self.attrname)

    def __set__(self, instance, value):
        return setattr(instance._browse, self.attrname, value)


# We will try to mimic OpenERP's client. Bugs and wrong design decisions included
class OnchangeDescriptor(ViewDescriptor):

    FUNC_RE = re.compile('^(.*?)\((.*)\)$')

    def __init__(self, attrname, fct_call):
        super(OnchangeDescriptor, self).__init__(attrname)
        match = self.FUNC_RE.match(fct_call)
        assert match
        self.func_name = match.group(1)
        self.args_name = [a.strip() for a in match.group(2).split(',')]

    def __set__(self, instance, value):
        super(OnchangeDescriptor, self).__set__(instance, value)
        proxy = instance.Browse.proxy

        ids = [] if instance._browse.id is None else [instance._browse.id]
        args = self.eval_args(self.args_name, instance)
        onchange_data = getattr(proxy, self.func_name)(ids, *args)
        for field_name, value in onchange_data['value'].items():
            setattr(instance, field_name, value)

    def eval_args(self, args_name, view):
        "Builds the local context and evaluate argument list"
        local = {}
        local['uid'] = view.Browse.proxy.uid
        local['current_date'] = time.strftime('%Y-%m-%d')
        local['time'] = time
        for field in view._fields:
            val = getattr(view._browse, field, None)
            if isinstance(val, (Browse, BrowseList)):
                local[field] = val.id
            elif isinstance(val, (datetime.datetime, datetime.date)):
                local[field] = view._browse._oe_values.get(field, None)
            else:
                local[field] = val
        return [self.eval_arg(arg, local) for arg in args_name]

    def eval_arg(self, arg, context):
        "This function tries to evaluate safely expressions"
        return eval(arg, {'__builtins__': []}, context)

class View(object):

    def __init__(self, id=None):
        if id is None:
            default_val = self.Browse.proxy.default_get(self._fields)
            self._browse = self.Browse(**default_val)
        else:
            self._browse = self.Browse(id)


class MetaView(type):

    def create_properties(cls, view_id):
        view_data = cls.Browse.proxy.fields_view_get(view_id)
        cls._fields = view_data['fields'].keys()
        view_xml = lxml.etree.fromstring(view_data['arch'])

        for field_name in cls._fields:
            field_node = view_xml.xpath("//field[@name='%s']" % field_name)
            if not field_node:
                continue
            field_node = field_node[0]
            if 'on_change' in field_node.attrib:
                setattr(cls, field_name,
                        OnchangeDescriptor(field_name,
                                           field_node.attrib['on_change']))
            else:
                setattr(cls, field_name, ViewDescriptor(field_name))


class ViewFactory(object):
    _view_classes = {}

    @classmethod
    def get(cls, client, database, model, view_id):
        if (database, view_id) not in cls._view_classes:
            klassname = 'view_%s' % view_id
            # model is unicode which is not accepted by type()
            Browse = client.create_browse(database, str(model))
            metaview = MetaView(klassname, (View,), {'Browse': Browse})
            metaview.create_properties(view_id)
            cls._view_classes[(database, view_id)] = metaview
        return cls._view_classes[(database, view_id)]
