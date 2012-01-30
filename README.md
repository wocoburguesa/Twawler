1: instalar MySQLdb (sudo apt-get install python-mysqldb, no hay en pip.)

2: instalar python-twitter (pip install python-twitter)

3: instalar google-api-python-client (pip install google-api-python-client)

4: copiar y pegar el archivo twitter.py del repo en la carpeta en donde esté instalada la librería twitter (reemplazar)

5: la base dedatos es:
 server: localhost
 user: testdb
 password: test623
 table: twitter
 Esta base de datos se tiene que crear, o en todo caso modificar el appconfig.ini para que refleje una bd en su máquina. La base que yo tengo está en mi laptop.

6: Los logs están en una carpeta llamada logs en donde esté el archivo twawler.py

7: Para ver la base de datos en mi laptop hay que entrar a mysql (mysql -u root -p), sin password, USE testdb; y si ponen SHOW TABLES ahí está twitter.

8: creo que eso es todo.