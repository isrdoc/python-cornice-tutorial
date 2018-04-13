import os
import binascii
import json

from cornice import Service
from pyramid.httpexceptions import HTTPUnauthorized


_USERS = {}
_MESSAGES = []

users = Service(name='users', path='/users', description="User registration")
messages = Service(name='messages', path='/', description="Messages")


def _create_token():
    return binascii.b2a_hex(os.urandom(20)).decode('utf-8')

def valid_token(request, **kargs):
    header = 'X-Messaging-Token'
    htoken = request.headers.get(header)
    
    if htoken is None:
        raise HTTPUnauthorized()
    
    try:
        user, token = htoken.split('-', 1)
    except ValueError:
        raise HTTPUnauthorized()
    
    valid = user in _USERS and _USERS[user] == token
    
    if not valid:
        raise HTTPUnauthorized()

    request.validated['user'] = user

def unique(request, **kargs):
    name = request.text
    
    if name in _USERS:
        request.errors.add('url', 'name', 'This user exists!')
    else:
        user = {'name': name, 'token': _create_token()}
        request.validated['user'] = user

def valid_message(request, **kargs):
    try:
        message = json.loads(request.body.decode('utf-8'))
    except ValueError:
        request.errors.add('body', 'message', 'Not valid JSON')
        return

    # make sure we have the fields we want
    if 'text' not in message:
        request.errors.add('body', 'text', 'Missing text')
        return

    if 'color' in message and message['color'] not in ('red', 'black'):
        request.errors.add('body', 'color', 'only red and black supported')
    elif 'color' not in message:
        message['color'] = 'black'

    message['user'] = request.validated['user']
    request.validated['message'] = message


@users.get(validators=valid_token)
def get_users(request):
    """Returns a list of all users."""
    return {'users': list(_USERS)}

@users.post(validators=unique)
def create_user(request):
    """Adds a new user."""
    user = request.validated['user']
    _USERS[user['name']] = user['token']
    return {'token': '%s-%s' % (user['name'], user['token'])}

@users.delete(validators=valid_token)
def delete_user(request):
    """Removes the user."""
    name = request.validated['user']
    del _USERS[name]
    return {'Goodbye': name}


@messages.get()
def get_messages(request):
    """Returns the 5 latest messages"""
    return _MESSAGES[:5]


@messages.post(validators=(valid_token, valid_message))
def post_message(request):
    """Adds a message"""
    _MESSAGES.insert(0, request.validated['message'])
    return {'status': 'added'}
