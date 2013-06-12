
class OAuthRouter(object):
    """
    A router to control all database operations on models in the
    oauth application.
    """
    def db_for_read(self, model, **hints):
        """
        Attempts to read auth models go to oauth_db.
        """
        if model._meta.app_label == 'oauth_db':
            return 'oauth_db'
        return None

    def db_for_write(self, model, **hints):
        """
        Attempts to write auth models go to oauth_db.
        """
        if model._meta.app_label == 'oauth_db':
            return 'oauth_db'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations if a model in the oauth app is involved.
        """
        if obj1._meta.app_label == 'oauth_db' or \
           obj2._meta.app_label == 'oauth_db':
           return True
        return None

    def allow_syncdb(self, db, model):
        """
        Make sure the lrs app only appears in the oauth_db
        database.
        """
        if db == 'oauth_db':
            print 'model' + str(model)
            print 'label' + str(model._meta.app_label)
            return model._meta.app_label == 'oauth_db'
        elif model._meta.app_label != 'oauth_db':
            return False
        return None