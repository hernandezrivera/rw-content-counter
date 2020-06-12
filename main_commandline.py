# from oauthlib.oauth2 import BackendApplicationClient  
from pip._vendor.distlib.compat import raw_input
from requests_oauthlib import OAuth2Session
import os
import json
import time
import datetime

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
debug = False
n_items = 100  # maximum number of articles to return. Max 100 . The higher, the less API calls.

client_id = r'999999707'
client_secret = r'Ic1LlZ3yaPOnOfepzUJ5MsyWLOo3CAlB'
redirect_uri = 'https://google.com'
days_back = 14

scope = ['read']
oauth = OAuth2Session(client_id, redirect_uri=redirect_uri,
                      scope=scope)
authorization_url, state = oauth.authorization_url(
    'https://www.inoreader.com/oauth2/auth',
    # access_type and prompt are Google specific extra
    # parameters.
    state="test")

print('Please go to %s and authorize access.\n' % authorization_url)

authorization_response = raw_input('Enter the value following the code parameter in the redirected URL\n')

while True:
    try:
        date_str = raw_input(
            'Enter the start date for the counting (yyyy-mm-dd) (Default: %i days ago)\n' % days_back)
        if date_str == '':
            today = datetime.date.today()
            date = today - datetime.timedelta(days=days_back)
        else:
            date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        date_unix = time.mktime(date.timetuple())
    except ValueError:
        print("Please, type a valid date format (yyyy-mm-dd).\n")
        continue
    else:
        break

non_read_str = raw_input('Do you want to get non-read articles? (Y = Non-read / N = all | Default is Y)\n')
non_read = not ((non_read_str == 'N') or (non_read_str == 'n') or (non_read_str == 'No'))

print(non_read)

token = oauth.fetch_token(
    'https://www.inoreader.com/oauth2/token',
    code=authorization_response,
    # Google specific extra parameter used for client
    # authentication
    client_secret=client_secret)


def make_call_to_json(url, debug=False):
    r = oauth.get(url)
    contents = r.content

    my_json = contents.decode('utf8').replace("'", '"')

    # Load the JSON to a Python list & dump it back out as formatted JSON
    data = json.loads(my_json)
    if debug:
        print('- ' * 20)
        s = json.dumps(data, indent=4, sort_keys=True)
        print(s)
        print('- ' * 20)
    return data


categories = {}
continuation = ""

while True:
    url = 'https://www.inoreader.com/reader/api/0/stream/contents?' \
          'n=' + str(n_items) + \
          '&ot=' + str(date_unix)
    # the parameter only gets non-read content, number of items and date_from
    if continuation != "":
        url = url + '&c=' + continuation
    if non_read:
        url = url + '&xt=user/-/state/com.google/read'

    contents = make_call_to_json(url, debug)
    for content in contents['items']:
        for category in content['categories']:
            if category not in categories:
                categories[category] = 1
            else:
                categories[category] += 1
    if 'continuation' not in contents:
        break
    else:
        continuation = contents['continuation']

print('- ' * 20)
print('Categories and number of items')
print('- ' * 20)

s = json.dumps(categories, indent=4, sort_keys=True)

print(s)

print('- ' * 20)
