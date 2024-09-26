import os
from functools import wraps
from models import *
from flask import Flask , render_template, request, redirect, url_for, flash, session
from pymongo import MongoClient
from bson import ObjectId

app = Flask(__name__)
app.secret_key = os.urandom(24)

client = MongoClient('localhost', 27017)
db = client['voice']
keys_collection = db['keys']
contestant_collection = db['contestant']
jury_collection = db['jury']
song_collection = db['song']
sequence_collection = db['sequence']

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
            flash('Invalid email or password!', 'danger')
            return render_template('fail.html')

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


#jury routes

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


#song routes

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


#performances routes

@app.route('/performance/create', methods=['GET', 'POST'])
@login_required
def add_performance():
    return 0


#sequences routes

@app.route('/sequences', methods=['GET', 'POST'])
@login_required
def sequences():
    return render_template('performances/sequences.html')


@app.route('/sequence/create', methods=['GET', 'POST'])
@login_required
def add_sequence():
    if request.method == 'POST':
        songs_assignment = request.form.getlist('songs')
        order = request.form.getlist('order[]')  # Отримання порядку з перетягування

        # Додавання нових виступів з порядком
        for index, contestant_id in enumerate(order):
            song_id = request.form.get(f'songs[{contestant_id}]')
            if song_id:
                contestant_id = ObjectId(contestant_id)
                song_id = ObjectId(song_id)

                # Додавання виступу в базу даних з порядком
                sequence_collection.insert_one({
                    "sequence_name": request.form['sequence_name'],
                    "contestant_id": contestant_id,
                    "song_id": song_id,
                    "sequence": index + 1  # Зберегти порядок
                })

        flash('Sequence and songs assigned successfully!', 'success')
        return redirect(url_for('add_sequence'))

        # Завантаження даних для вибору
    contestants = list(contestant_collection.find())
    songs = list(song_collection.find())
    return render_template('performances/sequence_add.html', contestants=contestants, songs=songs)


#broadcast routes

@app.route('/broadcasts', methods=['GET', 'POST'])
@login_required
def broadcasts():
    return render_template('broadcasts/broadcasts.html')


if __name__ == '__main__':
    app.run(debug=True)
