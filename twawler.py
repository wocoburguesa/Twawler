# -*- coding: utf-8 -*-
import twitter
from apiclient.discovery import build
import ConfigParser
import MySQLdb as mdb
import sys
import sql_helper
import datetime
import time
from urllib2 import URLError

class TwawlerError(Exception):
    @property
    def message(self):
        return self.args[0]

class Twawler(object):
    """
    Main class, searches for users matching the location criteria,

    either starting with a Twitter screen name specified explicitly

    or by picking the top result in a Google search input by the user.

    Usage:

      Create an instance of the class, either specifying a path to a

      config file (which has to be named 'appconfig.ini', without

      apostrophes) or with no parameters if the appconfig.ini file is

      in the same folder as this script.

        >>> import twawler
        >>> crawler = twawler.Crawler()
        OR
        >>> crawler = twawler.Crawler('/path/to/config/appconfig.ini')

      Configuration file:

        The appconfig.ini file should have the following structure:

        [twitter_app_credentials]
        consumer_key = YourConsumerKey
        consumer_secret = YourConsumerSecret
        access_token_key = YourOAuthAccessTokenKey
        access_token_secret = YourOAuthAccessTokenSecret

        [database_info]
        server = InWhichUserInformationGatheredWillBeStored
        username = Yep
        password = ***
        database = Yeppers
        table_name = Indeed

        [google_api_info]
        developerKey = ProvidedByGoogleCustomSearchAPI
        custom_search_id = Same

        That's it. Note that none of these values have quotation marks

        around them.

      Lastly, just call the run() method on the Crawler object and you're

      set to go.
    """
    
    def __init__(self, config_path=None, mode=None, query=None):
        """
        If mode and query are provided, the crawling function will

        start automatically.
        """
        now = datetime.datetime.now()
        self.logfile = open(now.strftime('logs/%Y%m%d%H%M.log'), 'w')    
        self.logfile.write('INITIALIZED ON %s\n' %
                           now.strftime('%Y-%m-%d AT %H:%M'))
        
        self.config_path = config_path    
        self.configuration = ConfigParser.SafeConfigParser()
        self.configuration.add_section('twitter_app_credentials')
        self.configuration.add_section('database_info')
        self.configuration.add_section('google_api_info')
        self.read_configuration()
        self.set_twitter_api()
        self.set_database()
        if mode:
            if query:
                self.run(mode, query)
            else:
                raise TwawlerError('Need to specify query.')

    def get_default_config_path(self):
        """
        If no path is passed as a parameter during instantiation,

        this method is called to get the appconfig.ini file.
        """
        
        return sys.path[0] + '/appconfig'
    
    def get_config_path(self):
        """
        Locates the appconfig.ini file to gather information relevant

        to both API's (Twitter and Google).
        """
        
        if self.config_path:
            return self.config_path
        else:
            return self.get_default_config_path()

    def log_event(self, event):
        """
        Writes a line on the current .log file with the following

        format:

          YYYY-MM-DD HH:SS EVENT OCURRED
        """
        
        header = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.logfile.write('%s: %s\n' % (header, event))
        
    def read_configuration(self):
        """
        Checks wether a path to the configuration path has been provided,

        otherwise calls get_default_config_path() for setting the

        appconfig.ini file.

        Note that if a bad path has been provided the program will exit.
        """
        
        try:
            self.configuration.read(self.get_config_path())
        except IOError, e:
            self.log_event('Couldn\'t find appconfig.ini file.')
            print e
            raise TwawlerError('Bad path to configuration file.')

    def set_twitter_api(self):
        """
        Initializes a twitter.Api() object, passing the authorization

        credentials provided in the appconfig.ini file.

        Note that with invalid credentials the request limit per hour is

        150. This changes to 350 while being authorized.
        """
        
        self.api = twitter.Api(
            consumer_key=
            self.configuration.get('twitter_app_credentials', 'consumer_key'),
            consumer_secret=
            self.configuration.get('twitter_app_credentials', 'consumer_secret'),
            access_token_key=
            self.configuration.get('twitter_app_credentials',
                                   'access_token_key'),
            access_token_secret=
            self.configuration.get('twitter_app_credentials',
                                   'access_token_secret'))
        self.log_event('INITIALIZED TWITTER API WITH consumer key %s SUCCESFULLY' %
                       self.configuration.get('twitter_app_credentials',
                                              'consumer_key'))

    def set_database(self):
        """
        Initializes a MySQLdb.connect object which acts as a liaison

        to the MySQL database in which we'll store retrieved data.

        Nothing fancy here.
        """
        
        print self.configuration.get('database_info', 'server')
        self.db = mdb.connect(
            self.configuration.get('database_info', 'server'),
            self.configuration.get('database_info', 'username'),
            self.configuration.get('database_info', 'password'),
            self.configuration.get('database_info', 'database'))
        self.db_cursor = self.db.cursor(mdb.cursors.DictCursor)
        self.table_name = self.configuration.get('database_info', 'table_name')
        self.log_event('SET DATABASE SUCCESFULLY')

    def set_google_api(self):
        """
        Just initializin'.
        """
        
        self.developerKey = self.configuration.get('google_api_info',
                                                   'developerKey')
        self.custom_search_id = self.configuration.get('google_api_info',
                                                       'custom_search_id')
        self.service = build('customsearch', 'v1',
                             developerKey=self.developerKey)
        self.log_event('INITIALIZED GOOGLE CUSTOM SEARCH API SUCCESFULLY')

    def check_criterion(self, user):
        """
        This will return True if the twitter.User() object passed as

        parameter matches the search criterion (or criteria).

        THIS SECTION SHOULD BE EDITED ACCORDING TO WHAT YOU'RE LOOKING

        FOR. Remember, it just returns a Boolean.
        """
        
        dict_user = user.AsDict()
        #For this script we're checking is the user is peruvian
        #This can be further improved. Geolocalization, perhaps.
        #Or relevant statuses and whatnot.
        location = dict_user.get('location', '').lower()
        timezone = dict_user.get('time_zone', '').lower()
        return 'peru' in location or u'perú' in location \
            or 'lima' in timezone.lower()
    
    def make_query(self, dict_follower):
        """
        A helper function for making an SQL-compliant query.

        It checks for Unicode because (I'm no expert on databases)

        I couldn't get MySQL to store strings with Unicode chars in

        them. Room for improvement here.

        Also: NEEDS TO BE EDITED TO MATCH THE TABLE COLUMNS. Obviously.
        """
        
        try:
            values = [
                dict_follower['screen_name'],
        #Stripping ' and " to avoid screwing up the SQL syntax.
                dict_follower['name'].replace('\'', '').replace('"', ''),
        #Not all Twitter accounts have set their location.
                dict_follower.get('location', '').replace('\'', '').replace('"', ''),
                0,
        #A lot of Twitter accounts have set this to private.
                dict_follower.get('followers_count', 0)]
        #SQL_Helper is a module with a single SQL-query-making function.
            helper = sql_helper.SQL_Helper()
            sql_query = helper.make_insert_query(self.table_name, values)
            return sql_query
        except UnicodeEncodeError:
            return 'EncodingError'

    def delete_from_table(self, user):
        """
        This gets called whenever the program tries to process

        an account that can no longer be found by the Twitter API.

        Pretty self-explanatory.
        """
        
        query = 'DELETE FROM %s WHERE screen_name = \'%s\'' % (
            self.table_name, user)
        return query
        
    def get_by_google_search(self, google_search):
        """
        Performs a Google Custom Search on the engine provided in

        the configuration file.

        THIS ALSO NEEDS TO BE HEAVILY MODIFIED DEPENDING ON HOW

        YOU WANT TO USE THE RESULTS FROM THAT SEARCH.

        In this case it just returns the Twitter screen name of the

        first element returned by the search. Clearly there's room

        for major improvement.

        """
        
        self.set_google_api()
        res = self.service.cse().list(
            q = google_search,
            cx = self.custom_search_id,
            lr = 'lang_es'
            ).execute()
        screen_name = ''
        #Container within container within container... Conception.
        #This gets the string starting at character 19 and ending upon
        #encountering a /. This string is under the key 'link' in the
        #first element of the list under the key 'items' of the search.
        for s in res['items'][0]['link'][19:]:
            if s != '/':
                screen_name += s
            else:
                break
        return screen_name

    def show_time_remaining(self, reset_time):
        """
        For debugging purposes, or the impatient.

        This prints in a terminal the time remaining until the request

        limit is reset by the API.
        """

        #This is now converted to seconds, which is the format returned
        #by the GetRateLimitStatus() method of the twitter library.
        #it also susbstracts five hours because of time zone differences.
        #If you live in a time zone other than Greenwich, change the 5
        #to -(whatever your time zone is). Mine is -5, so the factor is 5.
        now = int(time.mktime(time.gmtime())) - (5 * 3600)
        dif = reset_time - now
        h, s = divmod(dif, 60)
        return 'Resuming in %d:%d' % (h, s)

    def get_resume_data(self):
        """
        Returns whatever is in the resume.data file (in the same folder)

        in case mode is set to Resume.
        """
        return [line.strip() for line in open('resume.data').readlines()]
        
    def run(self, mode, start):
        """
        This method receives two arguments, the mode and the starting query.

        Upon checking which mode it's running on it calls the Api.GetUser()

        method to get an actual User object.

        After that the program enters an infinite loop in which it'll cycle

        through everyone on the database, gathering their followers on the way.

        The loop isn't infinite because it's bound to stop when the database

        has no more consumable individuals.

        For further detail into this method check the source code, there's

        plenty of notes in there, waiting to be read.
        """
        
        resuming = False
        if mode == 'UserInput':
            query = start
        elif mode == 'GoogleSearch':
            query = self.get_by_google_search(start)
        #else means it's resuming. This would usually be the option chosen.
        #Except the first time, of course.
        else:
            query = self.get_resume_data()[0]
            resuming = True

        #Retrieving anyone that has been processed already.
        self.db_cursor.execute('SELECT screen_name FROM %s WHERE checked=1' %
                               self.table_name)
        #Storing their screen names on a list.
        checked = [record['screen_name']
                   for record in self.db_cursor.fetchall()]

        #Same for those unchecked.
        self.db_cursor.execute('SELECT screen_name FROM %s WHERE checked=0' %
                               self.table_name)
        eligible = [record['screen_name']
                     for record in self.db_cursor.fetchall()]

        #Infinite loop, to end the program just Ctrl-C or Ctrl-Z
        while True:
            waiting = True
            limit_reached = False
            limit_reached_time = None
            current_user=None
            
            while waiting:
                try:
                    current_user = self.api.GetUser(query)
                    limit_reached = False
                    waiting = False
                #There can happen 2 things here (usually), either
                #the limit of requests per hour has been exceeded or
                #Twitter can't find the user passed.
                except twitter.TwitterError, e:
                #Then it deletes this user from the table and proceeds to
                #the next one.
                    if not str(e.message).startswith('Rate limit'):
                        self.db_cursor.execute(self.delete_from_table(query))
                        query = eligible.pop(0)
                #Or the program waits until the request limit is reset.
                #This displays the remaining time on a terminal
                    else:
                        if not limit_reached:
                            self.log_event('RATE LIMIT REACHED.')
                            limit_reached = True
                            reset_time = self.api.GetRateLimitStatus()[
                                'reset_time_in_seconds']
                        waiting = True
                        print self.show_time_remaining(reset_time)

            #Begin processing of User object.
            current_dict = current_user.AsDict()
            self.log_event('PROCESSING %d FOLLOWERS OF USER %s' %
                           (current_dict.get('followers_count', 0),
                            current_dict['screen_name'])
                           )

            #For debugging purposes
            print 'Processing user: %s' % current_dict['screen_name']
            print current_dict.get('description', 'No hay descripción, assfest.')

            #Marking the current user as processed on the database.
            #Kinda slow, maybe improve this?
            self.db_cursor.execute(
                "UPDATE %s SET checked=1 WHERE screen_name='%s'" %
                (self.table_name, current_dict['screen_name']))

            if resuming:
            #If resuming, read last session's data from resume.data file
            #(this file is created automatically).
                cursor = int(self.get_resume_data()[2])
                page = int(self.get_resume_data()[1])
            else:
            #-1 is the default cursor for the first page by Twitter's standards.
                cursor = -1
                page = 1
            #Looping through pages.
            while cursor != 0:
                waiting = True
                while waiting:
            #This is the same as before, checks for request limit status.
                    try:
                        followers = self.api.GetFollowersOfUser(
                            current_user, cursor)
                        limit_reached = False
                        waiting = False
                    except twitter.TwitterError:
                        if not limit_reached:
                            self.log_event('RATE LIMIT REACHED')
                            limit_reached = True
                            reset_time = self.api.GetRateLimitStatus()[
                                'reset_time_in_seconds']
                            print self.show_time_remaining(reset_time)
                        waiting = True
                
                self.log_event('READING PAGE %d WITH CURSOR %d' %
                               (page, cursor)
                               )
                #Debugging.
                print 'Page: %d' % page
                print 'Cursor: %d' % cursor
                #Updating cursor and page for next iteration.
                cursor = followers[2]
                page += 1
                
                resume_data = open('resume.data', 'w')
                #This check is here to avoid resuming at cursor 0, which
                #makes this program loop through users but not store
                #anything(because it won't enter this loop if cursor == 0)
                if cursor:
                    resume_data.write('%s\n%s\n%s' %
                                      (query, page, cursor))
                else:
                    resume_data.write('%s\n%s\n%s' %
                                      (query, page, '-1'))
                    
                #Never forget to close a file!(this comment is for me, actually)
                resume_data.close()

                #Looping through followers on this page.
                for follower in followers[0]:
                    dict_follower = follower.AsDict()
                    
                    #Check if they're eligible.
                    if self.check_criterion(follower) \
                    and dict_follower['screen_name'] not in checked \
                    and dict_follower['screen_name'] not in eligible:
                        sql = self.make_query(dict_follower)
                        try:
                            #Inserting in database.
                            self.db_cursor.execute(sql)
                            #Debugging
                            print dict_follower['screen_name']
                            self.log_event(
                                'STORING USER %s WITH %d FOLLOWERS' %
                                (dict_follower['screen_name'],
                                 dict_follower.get('followers_count', 0))
                                )
                        except UnicodeEncodeError:
                            pass
                #We're no longer resuming here, so this isn't needed anymore.
                resuming = False

            #Updating checked and eligible lists.
            self.db_cursor.execute('SELECT screen_name FROM %s WHERE checked=1' %
                        self.table_name)
            checked = [record['screen_name']
                       for record in self.db_cursor.fetchall()]

            self.db_cursor.execute('SELECT screen_name FROM %s WHERE checked=0' %
                        self.table_name)
            eligible = [record['screen_name']
                         for record in self.db_cursor.fetchall()]
            #And up we go again :)
            query = eligible.pop(0)


if __name__ == '__main__':
    program = Twawler(sys.path[0] + '/appconfig.ini')
#UserInput: Requiere un Screen Name de Twitter como semilla
#GoogleSearch: Requiere una búsqueda de google como semilla
    program.run(sys.argv[2], sys.argv[1])
