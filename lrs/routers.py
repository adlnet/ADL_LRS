import pdb

class LRSRouter(object):
    """
    A router to control all database operations on models in the
    default application.
    """
    def db_for_read(self, model, **hints):
        """
        Attempts to read auth models go to the default db.
        """
        if model._meta.app_label == 'default':
            return 'default'
        return None

    def db_for_write(self, model, **hints):
        """
        Attempts to write auth models go to default db.
        """
        if model._meta.app_label == 'default':
            return 'default'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations if a model in the default app is involved.
        """
        if obj1._meta.app_label == 'default' or \
           obj2._meta.app_label == 'default':
           return True
        return None

    def allow_syncdb(self, db, model):
        """
        Make sure the default app only appears in the default db
        database.
        """
        # pdb.set_trace()
        if db == 'default':
            return model._meta.app_label != 'oauth_provider'
        elif model._meta.app_label == 'oauth_provider':
            return False
        return None