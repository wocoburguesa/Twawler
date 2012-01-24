import sys
f = open(sys.path[0] + '/creds.pyasasa')
print sys.path[0]
print [line.strip() for line in f.readlines()]
