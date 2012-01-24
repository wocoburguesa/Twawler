# -*- coding: utf-8 -*-
import twitter
from apiclient.discovery import build
import ConfigParser
import MySQLdb as mdb
import sys
import sql_helper
from urllib2 import URLError

class Twawler(object):

    def __init__(self, config_path=None, mode=None):
        self.config_path = config_path
        self.mode = mode
        self.configuration = ConfigParser.SafeConfigParser()
        self.configuration.add_section('twitter_app_credentials')
        self.configuration.add_section('database_info')
        self.configuration.add_section('google_api_info')
        self.read_configuration()
        self.set_twitter_api()
        self.set_database()

    def get_default_config_path(self):
        return sys.path[0] + '/appconfig'
    
    def get_config_path(self):
        if self.config_path:
            return self.config_path
        else:
            return self.get_default_config_path()
        
    def read_configuration(self):
        try:
            self.configuration.read(self.get_config_path())
        except IOError, e:
            print e
            sys.exit(1)

    def set_twitter_api(self):
        self.api = twitter.Api(
            self.configuration.get('twitter_app_credentials', 'consumer_key'),
            self.configuration.get('twitter_app_credentials', 'consumer_secret'),
            self.configuration.get('twitter_app_credentials',
                                   'access_token_key'),
            self.configuration.get('twitter_app_credentials', 'access_token_secret'))

    def set_database(self):
        print self.configuration.get('database_info', 'server')
        self.db = mdb.connect(
            self.configuration.get('database_info', 'server'),
            self.configuration.get('database_info', 'username'),
            self.configuration.get('database_info', 'password'),
            self.configuration.get('database_info', 'database'))
        self.db_cursor = self.db.cursor(mdb.cursors.DictCursor)
        self.table_name = self.configuration.get('database_info', 'table_name')

    def set_google_api(self):
        self.developerKey = self.configuration.get('google_api_info',
                                                   'developerKey')
        self.custom_search_id = self.configuration.get('google_api_info',
                                                       'custom_search_id')
        self.service = build('customsearch', 'v1',
                             developerKey=self.developerKey)

    def check_peru(self, user):
        dict_user = user.AsDict()
        if not dict_user['protected']:
            location = dict_user.get('location', '').lower()
            return 'peru' in location or u'perú' in location
    
    def make_query(self, dict_follower):
        try:
            values = [
                dict_follower['screen_name'],
                dict_follower['name'].replace('\'', '').replace('"', ''),
                dict_follower['location'].replace('\'', '').replace('"', ''),
                0,
                dict_follower['followers_count']]
            helper = sql_helper.SQL_Helper()
            sql_query = helper.make_insert_query(self.table_name, values)
            print sql_query
            return sql_query
        except UnicodeEncodeError:
            return 'EncodingError'
        
    def get_by_google_search(self, google_search):
        self.set_google_api()
        res = self.service.cse().list(
            q = google_search,
            cx = self.custom_search_id,
            lr = 'lang_es' #hacer dinámica esta parte
            ).execute()
        screen_name = ''
        for s in res['items'][0]['link'][19:]:
            if s != '/':
                screen_name += s
            else:
                break
        return screen_name
        

    def run(self, start, mode='UserInput'):
        if mode == 'UserInput':
            query = start
        else:
            query = self.get_by_google_search(start)
    
        self.db_cursor.execute('SELECT screen_name FROM %s WHERE checked=1' %
                               self.table_name)
        checked = [record['screen_name']
                   for record in self.db_cursor.fetchall()]
        
        self.db_cursor.execute('SELECT screen_name FROM %s WHERE checked=0' %
                               self.table_name)
        peruvians = [record['screen_name']
                     for record in self.db_cursor.fetchall()]
        
        while True:
            waiting = True
            current_user=None
            while waiting:
                try:
                    current_user = self.api.GetUser(query)
                    waiting = False
                except:
                    waiting = True
            current_dict = current_user.AsDict()
            print 'PROCESANDO A %s:' % current_dict['screen_name']
            try:
                print current_dict['description']
            except KeyError:
                print 'No hay descripción, asswipe.'
            self.db_cursor.execute(
                "UPDATE %s SET checked=1 WHERE screen_name='%s'" %
                (self.table_name, current_dict['screen_name']))

            followers = self.api.GetFollowersOfUser(current_user)
                        
            for follower in followers:
                dict_follower = follower.AsDict()
                try:
                    if self.check_peru(follower) \
                    and dict_follower['screen_name'] not in checked \
                    and dict_follower['screen_name'] not in peruvians:
                        sql = self.make_query(dict_follower)
                        try:
                            self.db_cursor.execute(sql)
                        except UnicodeEncodeError:
                            pass
                except KeyError:
                    pass
                
            self.db_cursor.execute('SELECT screen_name FROM %s WHERE checked=1' %
                        self.table_name)
            checked = [record['screen_name']
                       for record in self.db_cursor.fetchall()]

            self.db_cursor.execute('SELECT screen_name FROM %s WHERE checked=0' %
                        self.table_name)
            peruvians = [record['screen_name']
                         for record in self.db_cursor.fetchall()]
            query = peruvians.pop(0)


if __name__ == '__main__':
    program = Twawler(sys.path[0] + '/appconfig.ini')
#    mode = raw_input("""Modo de ejecución
#UserInput: Requiere un Screen Name de Twitter como semilla
#GoogleSearch: Requiere una búsqueda de google como semilla
#""")
    if sys.argv[1] == 'UserInput':
        print 'Escribir el screen name de Twitter:'
    else:
        print 'Escribir la búsqueda de Google'
#    start = raw_input('> ')
    program.run(sys.argv[2], sys.argv[1])
