import json, urllib, urllib2, sqlite3, datetime
from flask import Flask, render_template, g

app = Flask(__name__)

# configuration details
num_songs = 7
lastfm_apikey = 'f5751cfc3aefbd7aa133f9d3bb4b19cd'
echonest_apikey = 'IL6UAJYLSF4XRPAX4'

@app.before_request
def db_connect():
    # SQLit3 Database initialization
    DATABASE = 'bpm.db'
    g.db = sqlite3.connect(DATABASE)

@app.teardown_request
def db_disconnect(exception=None):
    g.db.close()

@app.route('/', defaults={'username': 'joedanz'})
@app.route('/<username>')
def get_recent(username):
    # get recently played list from last.fm api
    recent_list = urllib2.urlopen('http://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks&api_key=' \
        + lastfm_apikey + '&format=json&limit=' + str(num_songs) +'&user=' + username)
    recent_data = recent_list.read()
    recent_list.close()
    parsed_recent = json.loads(recent_data)
    print "Retrieved list from last.fm..."

    # create tables
    g.db.execute("DROP TABLE IF EXISTS songs")
    g.db.execute("CREATE TABLE songs (ID INT PRIMARY KEY, ARTIST CHAR(250), TITLE CHAR(250), \
        BPM INTEGER, LISTENED CHAR(50), IMAGE CHAR(250))")

    # loop over songs from last.fm, don't include first in case currently playing
    for i in range(num_songs):
        print str(i+1) + ')',
        print parsed_recent['recenttracks']['track'][i]['artist']['#text'] + ' :',
        print parsed_recent['recenttracks']['track'][i]['name'],

        try:
            listenedAt = datetime.datetime.strptime(parsed_recent['recenttracks']['track'][i]['date']['#text'], '%d %b %Y, %H:%M')
        except:
            listenedAt = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

        # search for echo nest id
        echo_url1 = 'http://developer.echonest.com/api/v4/song/search?api_key='+echonest_apikey+'&artist=' \
            + urllib.quote(parsed_recent['recenttracks']['track'][i]['artist']['#text']) \
            + '&title=' + urllib.quote(parsed_recent['recenttracks']['track'][i]['name'].encode('utf8'))
        echo_track = urllib2.urlopen(echo_url1)
        echo_data = echo_track.read()
        echo_track.close()
        parsed_echo = json.loads(echo_data)

        # get tempo data from echo nest song detail
        echo_url2 = 'http://developer.echonest.com/api/v4/song/profile?api_key='+echonest_apikey+'&id=' \
            + parsed_echo['response']['songs'][0]['id'] + '&bucket=audio_summary'
        echo_bpm = urllib2.urlopen(echo_url2)
        bpm_data = echo_bpm.read()
        echo_bpm.close()
        parsed_bpm = json.loads(bpm_data)
        print '(' + str(parsed_bpm['response']['songs'][0]['audio_summary']['tempo']) + ') -',

        # use placeholder image if no album image and for now playing
        image_url = parsed_recent['recenttracks']['track'][i]['image'][2]['#text']
        if image_url == '':
            image_url = 'http://ticc.net/img/turntable.png'

        # insert into database
        g.db.execute("INSERT INTO songs (ARTIST, TITLE, BPM, LISTENED, IMAGE) VALUES ('" \
            + parsed_recent['recenttracks']['track'][i]['artist']['#text'] + "', '" \
            + parsed_recent['recenttracks']['track'][i]['name'] + "', '" \
            + str(int(parsed_bpm['response']['songs'][0]['audio_summary']['tempo'])) + "', '" \
            + str(listenedAt) + "', '" + image_url + "')")

        print listenedAt

    # get necessary data from db
    songs1 = g.db.execute("SELECT ID, ARTIST, TITLE, BPM, LISTENED, IMAGE FROM songs LIMIT 1000").fetchall()
    songs2 = g.db.execute("SELECT BPM, COUNT(*) AS NUMSONGS FROM songs GROUP BY BPM ORDER BY BPM LIMIT 1000").fetchall()
    return render_template('index.html', name=username, num_songs=num_songs, songs1=songs1, songs2=songs2)

if __name__ == '__main__':
    app.run(debug=True)
