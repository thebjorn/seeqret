import os


def secrets_init(dirname):
    print('Initializing seeqret for a new user')
    open(os.path.join(dirname, '.seeqret'), 'w').close()
