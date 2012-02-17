# -*- coding: utf-8 -*-

import time

from view import ViewFactory
from browse import BrowseFactory
from oesocket import OEConnection


class DBExistError(Exception):
    pass


class ProxyObj(object):

    def __init__(self, model, db, credentials, context, oe_conn):
        self.cnx = oe_conn
        self.model = model
        self.database = db
        self.context = context
        self.credentials = credentials

    @property
    def uid(self):
        return self.credentials.get('uid')

    @property
    def password(self):
        return self.credentials.get('password')

    @property
    def connected(self):
        return self.uid and self.password

    def exec_workflow(self, obj_id, transition):
        assert self.uid and self.password
        self.cnx.send(('object', 'exec_workflow', self.database, self.uid,
                       self.password, self.model, transition, obj_id))
        return self.cnx.receive()

    def name_search(self, name='', args=None, operator='ilike', limit=80):
        message = (('object', 'execute', self.database, self.uid,
                    self.password, self.model, 'name_search', name, args,
                    operator, self.context.as_dict(), limit))
        self.cnx.send(message)
        return self.cnx.receive()

    def read(self, ids, fields=[]):
        return self.__getattr__('read')(ids, fields)

    def fields_view_get(self, view_id=None, view_form='form'):
        message = (('object', 'execute', self.database, self.uid,
                    self.password, self.model, 'fields_view_get', view_id,
                    view_form, self.context.as_dict()))
        self.cnx.send(message)
        return self.cnx.receive()

    def search(self, condition=None, offset=0, limit=None, order_by=None):
        if condition is None:
            condition = []
        return self.__getattr__('search')(condition, offset, limit, order_by)

    def __getattr__(self, name):
        def proxy(*attrs):
            assert self.uid and self.password
            message = (('object', 'execute', self.database, self.uid,
                        self.password, self.model, name)
                       + attrs + (self.context.as_dict(),))
            self.cnx.send(message)
            return self.cnx.receive()
        return proxy

    def __str__(self):
        return "<Proxy on %s@%s>" % (self.model, self.database)


class WizardProxy(object):

    def __init__(self, wiz_name, db_name, credentials, oe_conn, client):
        self.client = client
        self.cnx = oe_conn
        self.wiz_name = wiz_name
        self.db_name = db_name
        self.uid = credentials['uid']
        self.user = credentials['login']
        self.password = credentials['password']
        self.wiz_id = self.create()
        self.data = {}
        self.transitions = ['init']
        self.fields = {}

    def create(self):
        self.cnx.send(('wizard', 'create', self.db_name, self.uid,
                       self.password, self.wiz_name))
        return self.cnx.receive()

    def activate_state(self, state):
        self.cnx.send(('wizard', 'execute', self.db_name, self.uid,
                       self.password, self.wiz_id, self.data, state))
        response = self.cnx.receive()
        self.data.setdefault('form', {}).update(response['datas'])

        if response['type'] == 'form':
            self.transitions = [x[0] for x in response['state']]
            self.fields = response['fields']
            for key, value in response['fields'].items():
                if self.data['form'].get(key) is not None:
                    continue
                val = value.get('value')
                if val is not None:
                    self.data['form'][key] = val
                else:
                    if value['type'] == 'selection':
                        self.data['form'][key] = -1
            return self
        elif response['type'] == 'state':
            if response['state'] != 'end':
                return self.activate_state(response['state'])
            else:
                return
        elif response['type'] == 'action':
            action_def = response['action']
            if action_def['type'] == 'ir.actions.act_window':
                return self.client.create_proxy(self.db_name,
                                                action_def['res_model'])
            else:
                raise NotImplementedError
        elif response['type'] == 'print':
            raise NotImplementedError


class Credentials(object):

    def __init__(self):
        self.passwords = {}

    def __getitem__(self, key):
        return self.passwords.setdefault(key, {})


class Context(dict):

    def __init__(self, oe_cnx):
        self.cnx = oe_cnx

    def as_dict(self):
        return dict(self)

    def reload(self, database, user, password):
        self.clear()
        self.cnx.send(('object', 'execute', database, user, password,
                       'res.users', 'context_get'))
        self.update(self.cnx.receive() or {})


class OEClient(object):

    def __init__(self, host='localhost', port=8070):
        self.host = host
        self.port = port
        self.credentials = Credentials()
        self.oe_conn = OEConnection(self.host, self.port, self.credentials)
        self.context = Context(self.oe_conn)

    def execute(self, command):
        self.oe_conn.send(command)
        return self.oe_conn.receive()

    def create_db(self, dbname, dbpass, adminpass, demo=False, lang='fr_FR',
                  overwrite=False):
        dbs = self.execute(('db', 'list'))
        if dbname in dbs:
            if not overwrite:
                raise DBExistError
            self.execute(('db', 'drop', dbpass, dbname))
        db_id = self.execute(('db', 'create', dbpass, dbname, demo, lang, adminpass))
        db_created = False
        while not db_created:
            db_created, user = self.execute(('db', 'get_progress', adminpass,
                                             db_id))
            time.sleep(0.5)

        self.login(dbname, 'admin', adminpass)

        user_obj = self.create_proxy(dbname, 'res.users')
        actwiz_obj = self.create_proxy(dbname, 'ir.actions.wizard')
        admin = user_obj.read(1)
        wiz_id = admin['menu_id'][0]
        wiz_name = actwiz_obj.read(wiz_id)['wiz_name']
        return self.create_wizard(dbname, wiz_name)

    def create_proxy(self, db, object):
        return ProxyObj(object, db, self.credentials[db], self.context,
                        self.oe_conn)

    def create_browse(self, db, object):
        BrowseFactory._client = self
        return BrowseFactory.get(db, object)

    def create_wizard(self, db, wizard_name):
        return WizardProxy(wizard_name, db, self.credentials[db], self.oe_conn,
                           self)

    def create_view(self, db, view_id):
        """This method creates a View object.

        view_id is an ID defined in an xml file"""
        if not isinstance(view_id, basestring):
            raise TypeError
        module, view_name = view_id.split('.')
        data_obj = self.create_proxy(db, 'ir.model.data')
        (model, data_id) = data_obj.get_object_reference(module, view_name)
        assert model == 'ir.ui.view'

        view_proxy = self.create_proxy(db, 'ir.ui.view')
        view_info = view_proxy.read(data_id)
        return ViewFactory.get(self, db, view_info['model'], data_id)

    def login(self, db, user, password):
        self.credentials[db]['login'] = user
        self.credentials[db]['password'] = password
        if 'uid' in self.credentials[db]:
            del self.credentials[db]['uid']
        uid = self.execute(('common', 'login', db, user, password))
        if uid:
            self.credentials[db]['uid'] = uid
            self.context.reload(db, uid, password)
        return bool(uid)


# vim:tw=80
