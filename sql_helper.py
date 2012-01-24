class SQL_Helper(object):
    """
    Makes MySQL queries, this file needs to be modified manually

    to conform to the columns of the target table
    """

    def __init__(self):
        pass

    def make_insert_query(self, table, values): 
        query = 'INSERT INTO %s(screen_name, name, location, checked, follower_count) VALUES' % table
        vals = []
        for s in values:
            try:
                numero = int(s)
                vals.append(str(numero))
            except ValueError:
                vals.append('\'' + s + '\'')

        query += '(%s)' % ', '.join(vals)
        return query
