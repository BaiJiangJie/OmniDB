import logging
from django.contrib.sessions.backends.db import SessionStore
from OmniDB import settings
import OmniDB_app.include.OmniDatabase as OmniDatabase


logger = logging.getLogger('JumpServer_app.manager.replay')


class DatabaseManager(object):

    def __init__(self):
        self.database = self.get_database()
        self.tables_related_conn_id = [
            'tabs', 'cgroups_connections', 'command_list', 'units_users_connections',
            'console_history', 'connections'
        ]
        self.tables_related_user_id = [
            'cgroups', 'users', 'command_list', 'connections', 'console_history', 'conversions',
            'messages_users', 'messages', 'mon_units', 'shortcuts', 'snippets_texts', 'tabs',
            'units_users_connections', 'users'
        ]

    @staticmethod
    def get_database():
        v_omnidb_database = OmniDatabase.Generic.InstantiateDatabase(
            'sqlite',
            '',
            '',
            settings.OMNIDB_DATABASE,
            '',
            '',
            '0',
            '',
            True
        )
        return v_omnidb_database

    def delete_user(self, user_id):
        if user_id is not None:
            self.database.v_connection.Execute('''
                delete from users where user_id={0}
            '''.format(user_id))

    def delete_connection(self, conn_id):
        if conn_id is not None:
            self.database.v_connection.Execute('''
                delete from connections where conn_id={0}
            '''.format(conn_id))

    def clear_datatable_related_conn_id(self, conn_id):
        logger.info(f'清除OmniDB数据库conn_id({conn_id})相关数据')
        for table in self.tables_related_conn_id:
            self.database.v_connection.Execute('''
                delete from {0} where conn_id={1}
            '''.format(table, conn_id))

    def clear_datatable_related_user_id(self, user_id):
        logger.info(f'清除OmniDB数据库user_id({user_id})相关数据')
        for table in self.tables_related_user_id:
            self.database.v_connection.Execute('''
                delete from {0} where user_id={1}
            '''.format(table, user_id))


class User(object):

    def __init__(self, _id):
        self.id = _id
        self._active_conn_ids = {}

    def add_active_conn_id(self, conn_id):
        self._active_conn_ids[conn_id] = conn_id

    def remove_active_conn_id(self, conn_id):
        self._active_conn_ids.pop(conn_id, None)

    def get_active_conn_ids(self):
        return list(self._active_conn_ids.keys())


class UserManager(object):

    def __init__(self):
        self._active_users = {}

    def add_active_user(self, user):
        self._active_users[user.id] = user

    def remove_active_user(self, user):
        self._active_users.pop(user.id, None)

    def get_active_user(self, user_id):
        return self._active_users.get(user_id)

    def get_user(self, user_id):
        user = self.get_active_user(user_id)
        if user is None:
            user = User(user_id)
            self.add_active_user(user)
        return user

    def get_user_active_conn_ids(self, user_id):
        user = self.get_user(user_id)
        return user.get_active_conn_ids()

    def add_user_active_conn_id(self, user_id, conn_id):
        user = self.get_user(user_id)
        user.add_active_conn_id(conn_id)

    def remove_user_active_conn_id(self, user_id, conn_id):
        user = self.get_user(user_id)
        user.remove_active_conn_id(conn_id)
        active_conn_ids = user.get_active_conn_ids()
        if len(active_conn_ids) == 0:
            self.remove_active_user(user)


class OmniDBManager(object):

    def __init__(self):
        self.user_manager = UserManager()
        self.database_manager = DatabaseManager()

    def end_connection(self, user_id, conn_id):
        self.database_manager.clear_datatable_related_conn_id(conn_id)
        self.user_manager.remove_user_active_conn_id(user_id=user_id, conn_id=conn_id)

    def try_end_session(self, user_id, session_key):
        active_conn_ids = self.user_manager.get_user_active_conn_ids(user_id)
        logger.info(f'用户活跃的conn_id数量({len(active_conn_ids)}), 列表({active_conn_ids})')
        if len(active_conn_ids) == 0:
            self.database_manager.clear_datatable_related_user_id(user_id)
            logger.info('删除OmniDB-User-SessionStore')
            SessionStore(session_key=session_key).delete()
        else:
            logger.info('保留OmniDB-User-Session')


omnidb_manager = OmniDBManager()
