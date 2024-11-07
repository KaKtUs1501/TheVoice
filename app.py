import os
from functools import wraps
from models import *
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from pymongo import MongoClient
from bson import ObjectId

app = Flask(__name__)
app.secret_key = os.urandom(24)

client = MongoClient('localhost', 27017)
db = client['TheVoice']
keys_collection = db['keys']
contestant_collection = db['contestant']
jury_collection = db['jury']
song_collection = db['song']
sequence_collection = db['sequence']
performance_collection = db['performance']
broadcast_collection = db['live_broadcast']
phone_voting_collection = db['phone_voting']
sms_voting_collection = db['SMS_voting']
results_collection = db['results']

song_db = SongDatabase(db_uri="mongodb://localhost:27017/", db_name="voice")


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


@app.route('/fail')
def fail():
    return render_template('fail.html')


@app.route('/')
@login_required
def home():
    return render_template('dashboard.html')


# Декоратор для перевірки, чи увійшов користувач у систему
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = keys_collection.find_one({'username': username})

        if user and user['password'] == password:
            session['logged_in'] = True
            session['username'] = user['username']
            return redirect(url_for('dashboard'))
        else:
            return "Incorrect username or password", 400

    return render_template('login.html')


# Створення маршруту для реєстрації
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            username = request.form['username']
            email = request.form['email']
            password = request.form['password']

            # Перевірка наявності користувача
            existing_user = keys_collection.find_one({'email': email})

            if existing_user is None:
                # Додавання нового користувача в базу даних
                keys_collection.insert_one({'username': username, 'email': email, 'password': password})
                flash('Registration successful!', 'success')
                return redirect(url_for('home'))
            else:
                flash('User already exists!', 'danger')
        except Exception as e:
            flash(f"An error occurred: {str(e)}", 'danger')

    if request.method == 'GET':
        return render_template('register.html')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))


@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    return render_template('dashboard.html')


# jury routes
@app.route('/jury', methods=['GET', 'POST'])
@login_required
def jury():
    return render_template('jury/jury.html', jury=list(jury_collection.find()))


@app.route('/jury/<jury_id>', methods=['GET', 'POST'])
@login_required
def view_jury(jury_id):
    jury_member = jury_collection.find_one({"_id": ObjectId(jury_id)})
    if not jury_member:
        flash("Jury member not found.", "danger")
        return redirect(url_for('home'))
    return render_template('jury/jury_profile.html', jury=jury_member)


@app.route('/jury/<jury_id>/delete')
@login_required
def delete_jury(jury_id):
    jury_collection.delete_one({"_id": ObjectId(jury_id)})
    flash('Jury member deleted successfully!', 'success')
    return redirect(url_for('dashboard'))


@app.route('/jury/<jury_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_jury(jury_id):
    jury_member = jury_collection.find_one({"_id": ObjectId(jury_id)})

    if request.method == 'POST':
        name = request.form['name']
        surname = request.form['surname']
        age = request.form['age']
        city = request.form['city']
        birth = request.form['birth']
        phone_number = request.form['phone_number']
        position = request.form['position']

        jury_collection.update_one(
            {"_id": ObjectId(jury_id)},
            {"$set": {
                "name": name,
                "surname": surname,
                "age": int(age),
                "city": city,
                "birth": birth,
                "phone_number": phone_number,
                "position": position
            }}
        )
        flash('Jury member updated successfully!', 'success')
        return redirect(url_for('view_jury', jury_id=jury_id))

    return render_template('jury/jury_edit.html', jury=jury_member)


@app.route('/jury/add', methods=['GET', 'POST'])
@login_required
def add_jury():
    if request.method == 'POST':
        name = request.form['name']
        surname = request.form['surname']
        age = request.form['age']
        city = request.form['city']
        birth = request.form['birth']
        phone_number = request.form['phone_number']
        position = request.form['position']

        jury_collection.insert_one({
            "name": name,
            "surname": surname,
            "age": int(age),
            "city": city,
            "birth": birth,
            "phone_number": phone_number,
            "position": position
        })
        flash('Jury member added successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('jury/jury_add.html')


# contestant routes
@app.route('/contestants', methods=['GET', 'POST'])
@login_required
def contestants():
    return render_template('contestants/contestants.html', contestants=list(contestant_collection.find()))


@app.route('/contestant/<contestant_id>', methods=['GET', 'POST'])
@login_required
def view_contestant(contestant_id):
    contestant = contestant_collection.find_one({"_id": ObjectId(contestant_id)})
    if not contestant:
        flash("Contestant not found.", "danger")
        return redirect(url_for('home'))
    return render_template('contestants/contestant_profile.html', contestant=contestant)


@app.route('/contestants/<contestant_id>/delete')
@login_required
def delete_contestant(contestant_id):
    contestant_collection.delete_one({"_id": ObjectId(contestant_id)})
    flash('Contestant deleted successfully!', 'success')
    return redirect(url_for('dashboard'))


@app.route('/contestants/<contestant_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_contestant(contestant_id):
    contestant = contestant_collection.find_one({"_id": ObjectId(contestant_id)})

    if request.method == 'POST':
        name = request.form['name']
        surname = request.form['surname']
        age = request.form['age']
        city = request.form['city']
        birth = request.form['birth']
        phone_number = request.form['phone_number']

        contestant_collection.update_one(
            {"_id": ObjectId(contestant_id)},
            {"$set": {
                "name": name,
                "surname": surname,
                "age": int(age),
                "city": city,
                "birth": birth,
                "phone_number": phone_number
            }}
        )
        flash('Contestant updated successfully!', 'success')
        return redirect(url_for('view_contestant', contestant_id=contestant_id))

    return render_template('contestants/contestant_edit.html', contestant=contestant)


@app.route('/contestant/add', methods=['GET', 'POST'])
@login_required
def add_contestant():
    if request.method == 'POST':
        name = request.form['name']
        surname = request.form['surname']
        age = request.form['age']
        city = request.form['city']
        birth = request.form['birth']
        phone_number = request.form['phone_number']

        contestant_collection.insert_one({
            "name": name,
            "surname": surname,
            "age": int(age),
            "city": city,
            "birth": birth,
            "phone_number": phone_number
        })
        flash('Contestant added successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('contestants/contestant_add.html')


# song routes
@app.route('/songs', methods=['GET'])
@login_required
def songs():
    return render_template('songs/songs.html', songs=list(song_collection.find()))


@app.route('/songs/add', methods=['GET', 'POST'])
@login_required
def add_song():
    if request.method == 'POST':
        name = request.form['name']
        author = request.form['author']
        genre = request.form['genre']

        song_collection.insert_one({
            "name": name,
            "author": author,
            "genre": genre
        })
        flash('Song added successfully!', 'success')
        return redirect(url_for('songs'))

    return render_template('songs/song_add.html')


@app.route('/song/<song_id>', methods=['GET'])
@login_required
def view_song(song_id):
    song = song_collection.find_one({"_id": ObjectId(song_id)})
    if not song:
        flash("Song not found.", "danger")
        return redirect(url_for('songs'))
    return render_template('songs/song_profile.html', song=song)


@app.route('/songs/<song_id>/delete')
@login_required
def delete_song(song_id):
    song_collection.delete_one({"_id": ObjectId(song_id)})
    flash('Song deleted successfully!', 'success')
    return redirect(url_for('songs'))


@app.route('/songs/<song_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_song(song_id):
    song = song_collection.find_one({"_id": ObjectId(song_id)})

    if request.method == 'POST':
        name = request.form['name']
        author = request.form['author']
        genre = request.form['genre']

        song_collection.update_one(
            {"_id": ObjectId(song_id)},
            {"$set": {
                "name": name,
                "author": author,
                "genre": genre
            }}
        )
        flash('Song updated successfully!', 'success')
        return redirect(url_for('songs'))

    return render_template('songs/song_edit.html', song=song)


# performance routes
@app.route('/performances', methods=['GET', 'POST'])
@login_required
def performances():
    performances = list(performance_collection.find())

    # Збираємо всі унікальні contestant_id, song_id і broadcast_id
    contestant_ids = {performance['contestant_id'] for performance in performances}
    song_ids = {performance['song_id'] for performance in performances}
    broadcast_ids = {performance['broadcast_id'] for performance in performances}

    # Фільтруємо контестантів, пісні та трансляції
    contestants = list(contestant_collection.find({"_id": {"$in": list(contestant_ids)}}))
    songs = list(song_collection.find({"_id": {"$in": list(song_ids)}}))
    broadcasts = list(broadcast_collection.find({"_id": {"$in": list(broadcast_ids)}}))

    return render_template(
        'performances/performances.html',
        performances=performances,
        contestants=contestants,
        songs=songs,
        broadcasts=broadcasts
    )


@app.route('/performance/create', methods=['GET', 'POST'])
@login_required
def add_performance():
    if request.method == 'POST':
        contestant_id = request.form['contestant_id']
        song_id = request.form['song_id']
        broadcast_id = request.form['broadcast_id']
        order = int(request.form['order'])

        # Перевірка: чи вже цей контестант має виступ на цьому ефірі
        existing_performance = performance_collection.find_one({
            "contestant_id": ObjectId(contestant_id),
            "broadcast_id": ObjectId(broadcast_id)
        })
        if existing_performance:
            error_message = 'This contestant already has a performance in this broadcast.'
            return render_template('performances/performance_add.html', contestants=list(contestant_collection.find()),
                                   songs=list(song_collection.find()), broadcasts=list(broadcast_collection.find()),
                                   error_message=error_message)

        # Перевірка: чи вже існує виступ на цьому ефірі з таким самим порядком
        same_order_performance = performance_collection.find_one({
            "broadcast_id": ObjectId(broadcast_id),
            "order": order
        })
        if same_order_performance:
            error_message = 'Another contestant already has this order in the same broadcast.'
            return render_template('performances/performance_add.html', contestants=list(contestant_collection.find()),
                                   songs=list(song_collection.find()), broadcasts=list(broadcast_collection.find()),
                                   error_message=error_message)

        # Додавання нового виступу
        performance_collection.insert_one({
            "contestant_id": ObjectId(contestant_id),
            "song_id": ObjectId(song_id),
            "broadcast_id": ObjectId(broadcast_id),
            "order": order,
            "phone_votes": 0,
            "sms_votes": 0,
        })
        flash('Performance added successfully!', 'success')
        return redirect(url_for('performances'))

    return render_template('performances/performance_add.html', contestants=list(contestant_collection.find()),
                           songs=list(song_collection.find()), broadcasts=list(broadcast_collection.find()))


@app.route('/performance/<performance_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_performance(performance_id):
    performance = performance_collection.find_one({"_id": ObjectId(performance_id)})

    if request.method == 'POST':
        try:
            contestant_id = request.form['contestant_id']
            song_id = request.form['song_id']
            broadcast_id = request.form['broadcast_id']
            order = int(request.form['order'])

            # Перевірка: чи вже цей контестант має виступ на цьому ефірі
            existing_performance = performance_collection.find_one({
                "contestant_id": ObjectId(contestant_id),
                "broadcast_id": ObjectId(broadcast_id),
                "_id": {"$ne": ObjectId(performance_id)}
            })
            if existing_performance:
                error_message = 'This contestant already has a performance in this broadcast.'
                return render_template('performances/performance_edit.html', performance=performance,
                                       contestants=list(contestant_collection.find()),
                                       songs=list(song_collection.find()), broadcasts=list(broadcast_collection.find()),
                                       error_message=error_message)

            # Перевірка: чи вже існує виступ на цьому ефірі з таким самим порядком
            same_order_performance = performance_collection.find_one({
                "broadcast_id": ObjectId(broadcast_id),
                "order": order,
                "_id": {"$ne": ObjectId(performance_id)}
            })
            if same_order_performance:
                error_message = 'Another contestant already has this order in the same broadcast.'
                return render_template('performances/performance_edit.html', performance=performance,
                                       contestants=list(contestant_collection.find()),
                                       songs=list(song_collection.find()), broadcasts=list(broadcast_collection.find()),
                                       error_message=error_message)

            # Оновлення виступу
            performance_collection.update_one(
                {"_id": ObjectId(performance_id)},
                {"$set": {
                    "contestant_id": ObjectId(contestant_id),
                    "song_id": ObjectId(song_id),
                    "broadcast_id": ObjectId(broadcast_id),
                    "order": order
                }}
            )
            flash('Performance updated successfully!', 'success')
            return redirect(url_for('performances'))
        except Exception as e:
            flash(f"An error occurred: {str(e)}", 'danger')

    return render_template('performances/performance_edit.html', performance=performance,
                           contestants=list(contestant_collection.find()), songs=list(song_collection.find()),
                           broadcasts=list(broadcast_collection.find()))


@app.route('/performance/<performance_id>/delete')
@login_required
def delete_performance(performance_id):
    performance_collection.delete_one({"_id": ObjectId(performance_id)})
    flash('Performance deleted successfully!', 'success')
    return redirect(url_for('performances'))


# broadcast routes
@app.route('/broadcasts', methods=['GET', 'POST'])
@login_required
def broadcasts():
    return render_template('broadcasts/broadcasts.html', broadcasts=list(broadcast_collection.find()))


@app.route('/broadcast/create', methods=['GET', 'POST'])
@login_required
def add_broadcast():
    if request.method == 'POST':
        name = request.form['name']
        date_of_live = request.form['date_of_live']
        duration = request.form['duration']
        description = request.form['description']

        broadcast_collection.insert_one({
            "name": name,
            "date_of_live": date_of_live,
            "duration": duration,
            "description": description
        })
        flash('Broadcast added successfully!', 'success')
        return redirect(url_for('broadcasts'))

    return render_template('broadcasts/broadcast_add.html')


@app.route('/broadcast/<broadcast_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_broadcast(broadcast_id):
    broadcast = broadcast_collection.find_one({"_id": ObjectId(broadcast_id)})

    if request.method == 'POST':
        try:
            date_of_live = request.form['date_of_live']
            duration = request.form['duration']
            name = request.form['name']
            description = request.form['description']
            broadcast_collection.update_one(
                {"_id": ObjectId(broadcast_id)},
                {"$set": {
                    "date_of_live": date_of_live,
                    "duration": duration,
                    "name": name,
                    "description": description
                }}
            )
            flash('Broadcast updated successfully!', 'success')
            return redirect(url_for('broadcasts'))
        except Exception as e:
            flash(f"An error occurred: {str(e)}", 'danger')

    return render_template('broadcasts/broadcast_edit.html', broadcast=broadcast,
                           error_message=request.args.get('error_message'))


@app.route('/broadcast/<broadcast_id>/delete')
@login_required
def delete_broadcast(broadcast_id):
    broadcast_collection.delete_one({"_id": ObjectId(broadcast_id)})
    flash('Broadcast deleted successfully!', 'success')
    return redirect(url_for('broadcasts'))


import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.route('/voting', methods=['GET', 'POST'])
@login_required
def voting():
    try:
        if request.method == 'POST':
            broadcast_id = request.form['broadcast_id']
        else:
            broadcast_id = request.args.get('broadcast_id')

        if broadcast_id:
            selected_broadcast = broadcast_collection.find_one({'_id': ObjectId(broadcast_id)})
            performances = list(performance_collection.find({'broadcast_id': ObjectId(broadcast_id)}))

            # Add contestant and song names to performances
            for performance in performances:
                contestant = contestant_collection.find_one({'_id': performance['contestant_id']})
                song = song_collection.find_one({'_id': performance['song_id']})
                performance[
                    'contestant_name'] = f"{contestant['name']} {contestant['surname']}" if contestant else 'Unknown Contestant'
                performance['song_name'] = song['name'] if song else 'Unknown Song'

            return render_template('voting/voting.html', broadcasts=list(broadcast_collection.find()),
                                   performances=performances, selected_broadcast=selected_broadcast)
    except Exception as e:
        logger.error(f"Error in voting route: {str(e)}")
        flash('An error occurred while loading voting data.', 'danger')

    return render_template('voting/voting.html', broadcasts=list(broadcast_collection.find()), performances=None,
                           selected_broadcast=None)


@app.route('/select_broadcast_for_voting', methods=['POST'])
@login_required
def select_broadcast_for_voting():
    try:
        broadcast_id = request.form['broadcast_id']
        return redirect(url_for('voting', broadcast_id=broadcast_id))
    except Exception as e:
        logger.error(f"Error in select_broadcast_for_voting route: {str(e)}")
        flash('An error occurred while selecting the broadcast.', 'danger')
        return redirect(url_for('voting'))


@app.route('/submit_votes', methods=['POST'])
@login_required
def submit_votes():
    broadcast_id = request.form.get('broadcast_id')
    votes_data = request.form.getlist('votes')

    if not broadcast_id or not votes_data:
        flash('Invalid submission. Please try again.', 'danger')
        return redirect(url_for('broadcasts'))

    for performance_id, votes in request.form.get('votes').items():
        phone_votes = votes.get('phone_votes')
        sms_votes = votes.get('sms_votes')

        if phone_votes is None or sms_votes is None:
            continue

        try:
            phone_votes = int(phone_votes)
            sms_votes = int(sms_votes)
        except ValueError:
            flash('Please enter valid numbers for votes.', 'danger')
            return redirect(url_for('broadcasts'))

        db.performances.update_one(
            {"_id": ObjectId(performance_id)},
            {"$set": {"phone_votes": phone_votes, "sms_votes": sms_votes}}
        )

    flash('Votes successfully submitted!', 'success')
    return redirect(url_for('broadcasts'))


@app.route('/results', methods=['GET'])
@login_required
def results():
    results = []
    for contestant in contestant_collection.find():
        # Підраховуємо кількість телефонних голосів для кожного конкурсанта
        phone_votes_count = phone_voting_collection.count_documents({"contestant_id": contestant["_id"]})

        # Підраховуємо кількість SMS голосів для кожного конкурсанта
        sms_votes_count = sms_voting_collection.count_documents({"contestant_id": contestant["_id"]})

        # Загальна кількість голосів
        total_votes = phone_votes_count + sms_votes_count

        results.append({
            "contestant": contestant,
            "total_votes": total_votes
        })

    return render_template('results/results.html', results=results)
@app.route('/performance/<performance_id>/vote', methods=['GET', 'POST'])
@login_required
def vote_performance(performance_id):
    # Знаходимо перформанс та його дані
    performance = performance_collection.find_one({"_id": ObjectId(performance_id)})
    broadcast_id = performance["broadcast_id"] if performance else None
    contestant_id = performance["contestant_id"] if performance else None

    if request.method == 'POST' and broadcast_id and contestant_id:
        phone_number = request.form['phone_number']
        vote_type = request.form['vote_type']

        # Формуємо дані для голосу, включаючи broadcast_id і contestant_id
        vote_data = {
            "performance_id": ObjectId(performance_id),
            "broadcast_id": broadcast_id,
            "contestant_id": contestant_id,
            "phone_number": phone_number
        }

        if vote_type == 'sms':
            sms_voting_collection.insert_one(vote_data)
        else:
            phone_voting_collection.insert_one(vote_data)

        flash('Vote recorded successfully!', 'success')
        return redirect(url_for('performances'))

    return render_template('voting/vote.html', performance=performance)


# requests

# Routes for executing queries

@app.route('/performers_by_song_and_city', methods=['GET', 'POST'])
@login_required
def performers_by_song_and_city():
    songs = list(song_collection.find())
    cities = contestant_collection.distinct('city')
    performers = []
    if request.method == 'POST':
        song = request.form.get('song')
        city = request.form.get('city')
        performers = list(contestant_collection.find({"city": city, "song": song}))
    return render_template('queries/performers_by_song_and_city.html', songs=songs, cities=cities,
                           performers=performers)


@app.route('/artists_and_songs_by_broadcast', methods=['GET', 'POST'])
@login_required
def artists_and_songs_by_broadcast():
    broadcasts = list(broadcast_collection.find())
    results = []
    if request.method == 'POST':
        broadcast_id = request.form.get('broadcast')
        performances = list(db['performance'].find({"broadcast_id": ObjectId(broadcast_id)}))
        for performance in performances:
            contestant = contestant_collection.find_one({"_id": performance["contestant_id"]})
            song = song_collection.find_one({"_id": performance["song_id"]})
            if contestant and song:
                results.append({
                    "contestant": f"{contestant['name']} {contestant['surname']}",
                    "song": song['name']
                })
    return render_template('queries/artists_and_songs_by_broadcast.html', broadcasts=broadcasts, results=results)


@app.route('/contestant_performed_songs', methods=['GET', 'POST'])
@login_required
def contestant_performed_songs():
    contestants = list(contestant_collection.find())
    song_data = {}
    if request.method == 'POST':
        contestant_id = request.form.get('contestant_id')
        performances = list(db['performance'].find({"contestant_id": ObjectId(contestant_id)}))
        for performance in performances:
            song_id = performance.get("song_id")
            song = song_collection.find_one({"_id": ObjectId(song_id)})
            if song:
                song_data[song["name"]] = song_data.get(song["name"], 0) + 1
    return render_template('queries/contestant_performed_songs.html', contestants=contestants, song_data=song_data)


@app.route('/contestant_under_200_votes', methods=['GET', 'POST'])
@login_required
def contestant_under_200_votes():
    contestants = list(contestant_collection.find())
    results = []
    if request.method == 'POST':
        for contestant in contestants:
            total_votes = phone_voting_collection.count_documents({"contestant_id": contestant["_id"]}) + \
                          sms_voting_collection.count_documents({"contestant_id": contestant["_id"]})
            if total_votes < 200:
                results.append(contestant)
    return render_template('queries/contestant_under_200_votes.html', contestants=results)


@app.route('/votes_in_first_broadcast', methods=['GET', 'POST'])
@login_required
def votes_in_first_broadcast():
    broadcasts = list(broadcast_collection.find().sort("date", 1))
    results = []
    if request.method == 'POST':
        first_broadcast = broadcasts[0] if broadcasts else None
        if first_broadcast:
            broadcast_id = first_broadcast["_id"]
            contestants = list(contestant_collection.find())
            for contestant in contestants:
                total_votes = phone_voting_collection.count_documents(
                    {"contestant_id": contestant["_id"], "broadcast_id": broadcast_id}) + \
                              sms_voting_collection.count_documents(
                                  {"contestant_id": contestant["_id"], "broadcast_id": broadcast_id})
                results.append(
                    {"contestant": f"{contestant['name']} {contestant['surname']}", "total_votes": total_votes})
    return render_template('queries/votes_in_first_broadcast.html', broadcasts=broadcasts, results=results)


@app.route('/broadcast_schedule', methods=['GET', 'POST'])
@login_required
def broadcast_schedule():
    broadcasts = list(broadcast_collection.find().sort("date_of_live", 1))
    return render_template('queries/broadcast_schedule.html', broadcasts=broadcasts)


@app.route('/max_sms_votes', methods=['GET', 'POST'])
@login_required
def max_sms_votes():
    max_votes = 0
    winner = None
    contestants = list(contestant_collection.find())
    if request.method == 'POST':
        for contestant in contestants:
            total_votes = sms_voting_collection.count_documents({"contestant_id": contestant["_id"]})
            if total_votes > max_votes:
                max_votes = total_votes
                winner = contestant
    return render_template('queries/max_sms_votes.html', winner=winner, total_votes=max_votes)


@app.route('/winner_of_contest', methods=['GET', 'POST'])
@login_required
def winner_of_contest():
    max_votes = 0
    winner = None
    contestants = list(contestant_collection.find())
    if request.method == 'POST':
        for contestant in contestants:
            total_votes = phone_voting_collection.count_documents({"contestant_id": contestant["_id"]}) + \
                          sms_voting_collection.count_documents({"contestant_id": contestant["_id"]})
            if total_votes > max_votes:
                max_votes = total_votes
                winner = contestant
    return render_template('queries/winner_of_contest.html', winner=winner, total_votes=max_votes)


@app.route('/sms_messages_per_broadcast', methods=['GET', 'POST'])
@login_required
def sms_messages_per_broadcast():
    broadcasts = list(broadcast_collection.find())
    sms_counts = []
    if request.method == 'POST':
        for broadcast in broadcasts:
            count = sms_voting_collection.count_documents({"broadcast_id": broadcast["_id"]})
            sms_counts.append({"broadcast": broadcast["name"], "count": count})
    return render_template('queries/sms_messages_per_broadcast.html', broadcasts=broadcasts, sms_counts=sms_counts)


@app.route('/calls_from_number', methods=['GET', 'POST'])
@login_required
def calls_from_number():
    broadcasts = list(broadcast_collection.find())
    total_calls = 0
    phone_number = request.form.get('phoneNumber')
    broadcast_id = request.form.get('broadcast')
    calls = list(phone_voting_collection.find({"phone_number": phone_number, "broadcast_id": ObjectId(broadcast_id)}))
    total_calls = len(calls)
    return render_template('queries/calls_from_number.html', broadcasts=broadcasts, total_calls=total_calls)


if __name__ == '__main__':
    app.run(debug=True)
