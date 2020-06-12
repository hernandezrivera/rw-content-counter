# from oauthlib.oauth2 import BackendApplicationClient  
from pip._vendor.distlib.compat import raw_input
from requests_oauthlib import OAuth2Session
import requests
import os
import json
import time
import datetime
import pandas as pd
import datetime
import yaml
from flask import Flask, request, jsonify, render_template, send_from_directory

app = Flask(__name__)

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
config = yaml.safe_load(open("config.yml"))

debug = config['debug']
n_items = 100  # maximum number of articles to return. Max 100 . The higher, the less API calls.

client_id = config['client_id']
client_secret = config['client_secret']
days_back = 1

scope = ['read']
port = config['port']

# redirect_uri = 'http://' + request.environ['REMOTE_ADDR'] + ':' + str(port) + '/code'
redirect_uri_local = config['local_url'] + ':' + str(port) + '/code'
redirect_uri_heroku = config['heroku_url'] + '/code'
if config['local_hosting']:
    redirect_uri = redirect_uri_local
else:
    redirect_uri = redirect_uri_heroku

oauth = OAuth2Session(client_id, redirect_uri=redirect_uri,
                      scope=scope)
authorization_url, state = oauth.authorization_url(
    'https://www.inoreader.com/oauth2/auth',
    # access_type and prompt are Google specific extra
    # parameters.
    state="test")


def make_oauth_call_to_json(url, debug=False):
    r = oauth.get(url)
    content_items = r.content
    my_json = content_items.decode('utf8').replace("'", '"')
    # Load the JSON to a Python list & dump it back out as formatted JSON
    data = json.loads(my_json)
    return data


def date_to_unix(date):
    date_str = date
    if (date_str is None) | (date_str == ''):
        today = datetime.date.today()
        date = today - datetime.timedelta(days=days_back)
    else:
        date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
    return time.mktime(date.timetuple())


def get_inoreader_data(content):
    item = {
        'ir_timestamp': content['timestampUsec'],
        'ir_id': content['id'],
        'ir_title': content['title'],
        'ir_origin_url': content['canonical'][0]['href'],
        'ir_origin_title': content['origin']['title'],
        'ir_origin_stream_id': content['origin']['title'],
        'ir_categories': ','.join(content['categories']),
        'ir_categories_array': content['categories']
    }
    if debug:
        item['ir_all_data'] = content
    return item


def get_reliefweb_data(item, origin_url):
\
    response = requests.get(
        "https://api.reliefweb.int/v1/reports?appname=content-stats&limit=1&filter[field]=origin&" + "filter[value]=" + origin_url + "&profile=full")
    rw_data = response.json()
    """
    # NOTE: This method looks for the origin URL as it. If inoreader URL finishes with "/" and not in RW, it won't match
    # anyway, analysis has shown that the number of cases like this is less than 1% so omitting double calling
    if (rw_data['count'] == 0) & (not origin_url.endswith('/')):
        # make the call with the url ending in "/" and without "/"
        origin_url = origin_url + '/'
        response = requests.get(
            "https://api.reliefweb.int/v1/reports?appname=content-stats&limit=1&filter[field]=origin&" + "filter[value]=" + origin_url + "&profile=full")
        rw_data = response.json()
    """
    if rw_data['count'] > 0:
        rw_data = rw_data['data'][0]['fields']
        try:
            item['rw_title'] = rw_data['title']
            item['rw_id'] = rw_data['id']
            item['rw_created'] = rw_data['date']['created']
            item['rw_primary_country'] = rw_data['primary_country']['iso3']
            item['rw_countries'] = [sub['iso3'] for sub in rw_data['country']]
            item['rw_format'] = [sub['name'] for sub in rw_data['format']]
            item['rw_language'] = [sub['code'] for sub in rw_data['language']]
            item['rw_source_shortname'] = [sub['shortname'] for sub in rw_data['source']]
            item['rw_node_url'] = rw_data['url']
            item['rw_url'] = rw_data['url_alias']
            if 'origin' in rw_data:
                # can  be submit => empty field / although it would be an  error as there is a inoreader item
                item['rw_origin_url'] = rw_data['origin']
            if 'disaster_type' in rw_data:
                item['rw_disaster_type'] = [sub['code'] for sub in rw_data['disaster_type']]
            if 'disaster' in rw_data:
                item['rw_disaster'] = [sub['name'] for sub in rw_data['disaster']]
            if debug:
                item['rw_all_data'] = rw_data
        finally:
            return item
    else:
        return item


def process_ir_categories(categories, item):
    item['ir_starred'] = False
    item['ir_read'] = False
    for category in item['ir_categories_array']:
        item['ir_starred'] = item['ir_starred'] | category.endswith("starred")
        item['ir_read'] = item['ir_read'] | category.endswith("read")

    for category in item['ir_categories_array']:
        if "label" in category:
            category_name = category.rpartition('/')[-1]
            if category_name not in categories:
                categories[category_name] = {}
                categories[category_name]['n_items'] = 0
                categories[category_name]['n_read'] = 0
                categories[category_name]['n_starred'] = 0
                categories[category_name]['n_posted_rw'] = 0
            categories[category_name]['n_items'] += 1
            if item['ir_starred']:
                categories[category_name]['n_starred'] += 1
            if item['ir_read']:
                categories[category_name]['n_read'] += 1
            if "rw_url" in item:
                categories[category_name]['n_posted_rw'] += 1
    item['ir_categories_array'] = []
    return categories


@app.route('/post', methods=['POST'])
def post_something():
    time_start = datetime.datetime.now()

    authorization_response = request.form.get('code')
    date = request.form.get('date')
    non_read = request.form.get('read-content')
    print(non_read)
    non_read = (non_read == "True")

    match_rw = request.form.get('match-rw')
    print(match_rw)
    match_rw = (match_rw == "True")
    print(match_rw)

    max_items = int(request.form.get('max-items'))
    date_unix = date_to_unix(date)

    print('==== INPUT PARAMETERS ==== ' + str(datetime.datetime.now()))

    print('- Start date: ' + date)
    print('- Process only non-read items: ' + str(non_read))
    print('- Match with RW content: ' + str(match_rw))
    print('- Max items to process: ' + str(max_items))

    print('==== START PROCESSING ==== ' + str(datetime.datetime.now()))

    token = oauth.fetch_token(

        'https://www.inoreader.com/oauth2/token',
        code=authorization_response,
        # Google specific extra parameter used for client authentication
        client_secret=client_secret)

    continuation = ""

    ir_n_items = 0
    rw_n_items = 0
    items = []
    categories = {}
    while True:
        url = 'https://www.inoreader.com/reader/api/0/stream/contents?' \
              'n=' + str(n_items) + \
              '&ot=' + str(date_unix)
        # the parameter only gets non-read content, number of items and date_from
        if continuation != "":
            url = url + '&c=' + continuation
        if non_read:
            url = url + '&xt=user/-/state/com.google/read'

        contents = make_oauth_call_to_json(url, debug)
        ir_n_items = ir_n_items + len(contents['items'])
        print(
            '- Additional %i contents to process from inoreader. Total so far: %i ' % (
            len(contents['items']), ir_n_items))
        for content in contents['items']:
            item = get_inoreader_data(content)
            if match_rw:
                item = get_reliefweb_data(item, item['ir_origin_url'])
            categories = process_ir_categories(categories, item)
            if 'rw_url' in item:
                rw_n_items = rw_n_items + 1
            items.append(item)
        if ('continuation' not in contents) | debug | ((ir_n_items > max_items) & (max_items != 0)):
            break
        else:
            continuation = contents['continuation']

    print('==== DONE PROCESSING ==== ' + str(datetime.datetime.now()))

    time_end = datetime.datetime.now()
    time_delta = time_end - time_start
    total_seconds = time_delta.total_seconds()
    total_minutes = total_seconds / 60

    print('- Content from inoreader: %i ' % ir_n_items)
    print('- Matching RW: %i ' % rw_n_items)
    print('- Minutes to process: %i ' % total_minutes)

    # saving the result as json file
    print('==== SAVING OUTPUT ==== ' + str(datetime.datetime.now()))

    with open('data.json', 'w') as outfile:
        json.dump(items, outfile)
        df = pd.DataFrame(items)
    try:
        filename = 'inoreader_items_' + str(time_end) + '.csv'
        df.to_csv(filename, index=None)
        print('- Datafile with result for each item available at: ' + filename)
    except:
        print("- I cannot write in the output file (%s) , omitting" % filename)

    print(categories)
    return render_template('results.html', date=date, non_read=non_read, n_inoreader=ir_n_items,
                           n_reliefweb=rw_n_items, time=total_minutes, categories=categories)

    print('==== DONE ==== ' + str(datetime.datetime.now()))


@app.route('/code')
def get_code():
    authorization_code = request.args.get('code')
    today = datetime.date.today()
    date = today - datetime.timedelta(days=days_back)

    return render_template('code.html', code=authorization_code, days_back=days_back, date=date)


# A welcome message to test our server
@app.route('/')
def index():
    return render_template('home.html', url=authorization_url, days_back=days_back)


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')


if __name__ == '__main__':
    # Threaded option to enable multiple instances for multiple user access support
    app.run(threaded=True, port=port)
