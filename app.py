import os
from distutils import errors
from functools import wraps
from venv import logger

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
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
performance_collection = db['performance']
broadcast_collection = db['live_broadcast']
phone_voting_collection = db['phone_voting']
sms_voting_collection = db['SMS_voting']
results_collection = db['results']
jury_voting_collection = db['jury_voting']



def is_valid_objectid(id_str):
    """
    Перевіряє, чи є рядок валідним ObjectId.
    """
    try:
        ObjectId(id_str)
        return True
    except errors.InvalidId:
        return False


def cascade_delete(collection_name, document_id):
    try:
        if collection_name == 'contestant':
            # Видалення виступів
            deleted_performances = performance_collection.delete_many({'contestant_id': document_id})
            # Видалення голосів
            deleted_phone_votes = phone_voting_collection.delete_many({'contestant_id': document_id})
            deleted_sms_votes = sms_voting_collection.delete_many({'contestant_id': document_id})
            logger.info(f'Deleted {deleted_performances.deleted_count} performances, '
                        f'{deleted_phone_votes.deleted_count} phone votes, '
                        f'{deleted_sms_votes.deleted_count} SMS votes for contestant {document_id}.')

        elif collection_name == 'song':
            # Видалення виступів з цією піснею
            deleted_performances = performance_collection.delete_many({'song_id': document_id})
            logger.info(f'Deleted {deleted_performances.deleted_count} performances for song {document_id}.')

        elif collection_name == 'broadcast':
            # Видалення виступів
            deleted_performances = performance_collection.delete_many({'broadcast_id': document_id})
            # Видалення голосів
            deleted_phone_votes = phone_voting_collection.delete_many({'broadcast_id': document_id})
            deleted_sms_votes = sms_voting_collection.delete_many({'broadcast_id': document_id})
            logger.info(f'Deleted {deleted_performances.deleted_count} performances, '
                        f'{deleted_phone_votes.deleted_count} phone votes, '
                        f'{deleted_sms_votes.deleted_count} SMS votes for broadcast {document_id}.')

        elif collection_name == 'performance':
            # Видалення голосів, пов’язаних з цим виступом
            deleted_phone_votes = phone_voting_collection.delete_many({'performance_id': document_id})
            deleted_sms_votes = sms_voting_collection.delete_many({'performance_id': document_id})
            logger.info(f'Deleted {deleted_phone_votes.deleted_count} phone votes, '
                        f'{deleted_sms_votes.deleted_count} SMS votes for performance {document_id}.')

        # Додайте інші випадки залежно від вашої моделі даних
    except Exception as e:
        logger.error(f'Error during cascade delete: {str(e)}')
        raise e

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


def roles_required(*roles):
    def wrapper(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'role' not in session:
                flash('You need to be logged in to access this page.', 'danger')
                return redirect(url_for('login'))
            user_role = session['role']
            if user_role in roles:
                return f(*args, **kwargs)
            else:
                return redirect(url_for('no_permissions'))

        return decorated_function

    return wrapper


@app.route('/no_permissions')
def no_permissions():
    return render_template('no_permissions.html')


@app.route('/fail')
def fail():
    return render_template('fail.html')


@app.route('/')
@login_required
def home():
    return render_template('dashboard.html')


# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = keys_collection.find_one({'username': username})

        if user and user['password'] == password:
            session['logged_in'] = True
            session['username'] = user['username']
            session['role'] = user.get('role', 'user')
            return redirect(url_for('dashboard'))
        else:
            return redirect(url_for('fail'))

    return render_template('login.html')

# Маршрут для "Forgot Password"
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        email = request.form.get('email').strip()

        if not username or not email:
            flash('Будь ласка, заповніть всі поля.', 'danger')
            return redirect(url_for('forgot_password'))

        user = keys_collection.find_one({'username': username, 'email': email})

        if user:
            password = user.get('password')
            flash(f'Ваш пароль: {password}', 'success')
            return redirect(url_for('forgot_password'))
        else:
            flash('Користувач з таким логіном та електронною поштою не знайдений.', 'danger')
            return redirect(url_for('forgot_password'))

    return render_template('forgot_password.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            username = request.form['username']
            email = request.form['email']
            password = request.form['password']

            existing_user = keys_collection.find_one({'email': email})

            if existing_user is None:
                keys_collection.insert_one({
                    'username': username,
                    'email': email,
                    'password': password,
                    'role': 'user'
                })
                flash('Registration successful!', 'success')
                return redirect(url_for('home'))
            else:
                flash('User already exists!', 'danger')
        except Exception as e:
            flash(f"An error occurred: {str(e)}", 'danger')

    if request.method == 'GET':
        return render_template('register.html')
    return render_template('login.html')

@app.route('/user/add', methods=['GET', 'POST'])
def user_add():
    if request.method == 'POST':
        try:
            username = request.form['username']
            email = request.form['email']
            password = request.form['password']
            role = request.form['role']

            existing_user = keys_collection.find_one({'email': email})

            if existing_user is None:
                keys_collection.insert_one({
                    'username': username,
                    'email': email,
                    'password': password,
                    'role': role
                })
                flash('Registration successful!', 'success')
                return redirect(url_for('manage_users'))
            else:
                flash('User already exists!', 'danger')
        except Exception as e:
            flash(f"An error occurred: {str(e)}", 'danger')

    if request.method == 'GET':
        return render_template('users/users_add.html')
    return url_for('manage_users')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))


@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    return render_template('dashboard.html')


# Маршрути для Журі
@app.route('/jury', methods=['GET', 'POST'])
@login_required
@roles_required('owner', 'administrator', 'operator', 'user')
def jury():
    return render_template('jury/jury.html', jury=list(jury_collection.find()))


@app.route('/jury/<jury_id>', methods=['GET', 'POST'])
@login_required
@roles_required('owner', 'administrator', 'operator', 'user')
def view_jury(jury_id):
    if not is_valid_objectid(jury_id):
        flash('Невалідний ID журі.', 'danger')
        return redirect(url_for('jury'))

    jury_member = jury_collection.find_one({"_id": ObjectId(jury_id)})
    if not jury_member:
        flash("Член журі не знайдено.", "danger")
        return redirect(url_for('jury'))
    return render_template('jury/jury_profile.html', jury=jury_member)


@app.route('/jury/<jury_id>/delete')
@login_required
@roles_required('owner', 'administrator')
def delete_jury(jury_id):
    if not is_valid_objectid(jury_id):
        flash('Невалідний ID журі.', 'danger')
        return redirect(url_for('jury'))

    try:
        jury_member = jury_collection.find_one({"_id": ObjectId(jury_id)})
        if not jury_member:
            flash("Член журі не знайдено.", "danger")
            return redirect(url_for('jury'))

        # Якщо є дочірні записи, додайте виклик cascade_delete
        # Наприклад:
        # cascade_delete('jury', ObjectId(jury_id))

        jury_collection.delete_one({"_id": ObjectId(jury_id)})
        flash('Член журі успішно видалений!', 'success')
    except Exception as e:
        flash(f'Виникла помилка при видаленні члена журі: {str(e)}', 'danger')

    return redirect(url_for('jury'))


@app.route('/jury/<jury_id>/edit', methods=['GET', 'POST'])
@login_required
@roles_required('owner', 'administrator', 'operator')
def edit_jury(jury_id):
    if not is_valid_objectid(jury_id):
        flash('Невалідний ID журі.', 'danger')
        return redirect(url_for('jury'))

    jury_member = jury_collection.find_one({"_id": ObjectId(jury_id)})

    if not jury_member:
        flash("Член журі не знайдено.", "danger")
        return redirect(url_for('jury'))

    if request.method == 'POST':
        try:
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
            flash('Член журі успішно оновлений!', 'success')
            return redirect(url_for('view_jury', jury_id=jury_id))
        except Exception as e:
            flash(f'Виникла помилка при оновленні журналу: {str(e)}', 'danger')

    return render_template('jury/jury_edit.html', jury=jury_member)


@app.route('/jury/add', methods=['GET', 'POST'])
@login_required
@roles_required('owner')
def add_jury():
    if request.method == 'POST':
        try:
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
            flash('Член журі успішно доданий!', 'success')
            return redirect(url_for('jury'))
        except Exception as e:
            flash(f'Виникла помилка при додаванні члена журі: {str(e)}', 'danger')

    return render_template('jury/jury_add.html')


# Маршрути для Конкурсантів
@app.route('/contestants', methods=['GET', 'POST'])
@login_required
@roles_required('owner', 'administrator', 'operator', 'user')
def contestants():
    return render_template('contestants/contestants.html', contestants=list(contestant_collection.find()))


@app.route('/contestant/<contestant_id>', methods=['GET', 'POST'])
@login_required
@roles_required('owner', 'administrator', 'operator', 'user')
def view_contestant(contestant_id):
    if not is_valid_objectid(contestant_id):
        flash('Невалідний ID конкурсанта.', 'danger')
        return redirect(url_for('contestants'))

    contestant = contestant_collection.find_one({"_id": ObjectId(contestant_id)})
    if not contestant:
        flash("Конкурсант не знайдено.", "danger")
        return redirect(url_for('contestants'))
    return render_template('contestants/contestant_profile.html', contestant=contestant)


@app.route('/contestants/<contestant_id>/delete')
@login_required
@roles_required('owner', 'administrator')
def delete_contestant(contestant_id):
    if not is_valid_objectid(contestant_id):
        flash('Невалідний ID конкурсанта.', 'danger')
        return redirect(url_for('contestants'))

    try:
        contestant = contestant_collection.find_one({"_id": ObjectId(contestant_id)})
        if not contestant:
            flash("Конкурсант не знайдено.", "danger")
            return redirect(url_for('contestants'))

        # Виконання каскадного видалення
        cascade_delete('contestant', ObjectId(contestant_id))

        # Видалення самого конкурсанта
        contestant_collection.delete_one({"_id": ObjectId(contestant_id)})

        flash('Конкурсант та всі пов’язані записи успішно видалені!', 'success')
    except Exception as e:
        flash(f'Виникла помилка при видаленні конкурсанта: {str(e)}', 'danger')

    return redirect(url_for('contestants'))


@app.route('/contestants/<contestant_id>/edit', methods=['GET', 'POST'])
@login_required
@roles_required('owner', 'administrator', 'operator')
def edit_contestant(contestant_id):
    if not is_valid_objectid(contestant_id):
        flash('Невалідний ID конкурсанта.', 'danger')
        return redirect(url_for('contestants'))

    contestant = contestant_collection.find_one({"_id": ObjectId(contestant_id)})

    if not contestant:
        flash("Конкурсант не знайдено.", "danger")
        return redirect(url_for('contestants'))

    if request.method == 'POST':
        try:
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
            flash('Конкурсант успішно оновлений!', 'success')
            return redirect(url_for('view_contestant', contestant_id=contestant_id))
        except Exception as e:
            flash(f'Виникла помилка при оновленні конкурсанта: {str(e)}', 'danger')

    return render_template('contestants/contestant_edit.html', contestant=contestant)


@app.route('/contestant/add', methods=['GET', 'POST'])
@login_required
@roles_required('owner')
def add_contestant():
    if request.method == 'POST':
        try:
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
            flash('Конкурсант успішно доданий!', 'success')
            return redirect(url_for('contestants'))
        except Exception as e:
            flash(f'Виникла помилка при додаванні конкурсанта: {str(e)}', 'danger')

    return render_template('contestants/contestant_add.html')


# Маршрути для Пісень
@app.route('/songs', methods=['GET'])
@login_required
@roles_required('owner', 'administrator', 'operator', 'user')
def songs():
    return render_template('songs/songs.html', songs=list(song_collection.find()))


@app.route('/songs/add', methods=['GET', 'POST'])
@login_required
@roles_required('owner')
def add_song():
    if request.method == 'POST':
        try:
            name = request.form['name']
            author = request.form['author']
            genre = request.form['genre']

            song_collection.insert_one({
                "name": name,
                "author": author,
                "genre": genre
            })
            flash('Пісня успішно додана!', 'success')
            return redirect(url_for('songs'))
        except Exception as e:
            flash(f'Виникла помилка при додаванні пісні: {str(e)}', 'danger')

    return render_template('songs/song_add.html')


@app.route('/song/<song_id>', methods=['GET'])
@login_required
@roles_required('owner', 'administrator', 'operator', 'user')
def view_song(song_id):
    if not is_valid_objectid(song_id):
        flash('Невалідний ID пісні.', 'danger')
        return redirect(url_for('songs'))

    song = song_collection.find_one({"_id": ObjectId(song_id)})
    if not song:
        flash("Пісню не знайдено.", "danger")
        return redirect(url_for('songs'))
    return render_template('songs/song_profile.html', song=song)


@app.route('/songs/<song_id>/delete')
@login_required
@roles_required('owner')
def delete_song(song_id):
    if not is_valid_objectid(song_id):
        flash('Невалідний ID пісні.', 'danger')
        return redirect(url_for('songs'))

    try:
        song = song_collection.find_one({"_id": ObjectId(song_id)})
        if not song:
            flash("Пісню не знайдено.", "danger")
            return redirect(url_for('songs'))

        # Виконання каскадного видалення
        cascade_delete('song', ObjectId(song_id))

        # Видалення самої пісні
        song_collection.delete_one({"_id": ObjectId(song_id)})

        flash('Пісня та всі пов’язані записи успішно видалені!', 'success')
    except Exception as e:
        flash(f'Виникла помилка при видаленні пісні: {str(e)}', 'danger')

    return redirect(url_for('songs'))


@app.route('/songs/<song_id>/edit', methods=['GET', 'POST'])
@login_required
@roles_required('owner', 'administrator', 'operator')
def edit_song(song_id):
    if not is_valid_objectid(song_id):
        flash('Невалідний ID пісні.', 'danger')
        return redirect(url_for('songs'))

    song = song_collection.find_one({"_id": ObjectId(song_id)})

    if not song:
        flash("Пісню не знайдено.", "danger")
        return redirect(url_for('songs'))

    if request.method == 'POST':
        try:
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
            flash('Пісня успішно оновлена!', 'success')
            return redirect(url_for('songs'))
        except Exception as e:
            flash(f'Виникла помилка при оновленні пісні: {str(e)}', 'danger')

    return render_template('songs/song_edit.html', song=song)


@app.route('/performances', methods=['GET', 'POST'])
@login_required
@roles_required('owner', 'administrator', 'operator', 'user')
def performances():
    # Отримуємо всі унікальні ефіри для вибору
    broadcasts = list(broadcast_collection.find())
    selected_broadcast_id = None
    performances = []

    # Якщо обрано ефір
    if request.method == 'POST':
        selected_broadcast_id = request.form.get('broadcast_id')
        if selected_broadcast_id:
            # Отримуємо виступи, пов'язані лише з обраним ефіром
            performances = list(performance_collection.find({"broadcast_id": ObjectId(selected_broadcast_id)}).sort("order", 1))
    else:
        # Якщо ефір не обрано, показуємо всі виступи
        performances = list(performance_collection.find())

    # Збираємо унікальні contestant_id та song_id для фільтрованих виступів
    contestant_ids = {performance['contestant_id'] for performance in performances}
    song_ids = {performance['song_id'] for performance in performances}

    # Фільтруємо конкурсантів і пісні
    contestants = list(contestant_collection.find({"_id": {"$in": list(contestant_ids)}}))
    songs = list(song_collection.find({"_id": {"$in": list(song_ids)}}))

    return render_template(
        'performances/performances.html',
        performances=performances,
        contestants=contestants,
        songs=songs,
        broadcasts=broadcasts,
        selected_broadcast_id=selected_broadcast_id
    )



@app.route('/performance/create', methods=['GET', 'POST'])
@login_required
@roles_required('owner')
def add_performance():
    if request.method == 'POST':
        try:
            contestant_id = request.form['contestant_id']
            song_id = request.form['song_id']
            broadcast_id = request.form['broadcast_id']
            order = int(request.form['order'])

            # Перевірка валідності ObjectId
            if not all(map(is_valid_objectid, [contestant_id, song_id, broadcast_id])):
                flash('Невалідний ID одного з полів.', 'danger')
                return redirect(url_for('add_performance'))

            # Перевірка: чи вже цей конкурсант має виступ на цьому ефірі
            existing_performance = performance_collection.find_one({
                "contestant_id": ObjectId(contestant_id),
                "broadcast_id": ObjectId(broadcast_id)
            })
            if existing_performance:
                error_message = 'Цей конкурсант вже має виступ у цій трансляції.'
                return render_template('performances/performance_add.html',
                                       contestants=list(contestant_collection.find()),
                                       songs=list(song_collection.find()),
                                       broadcasts=list(broadcast_collection.find()),
                                       error_message=error_message)

            # Перевірка: чи вже існує виступ з таким самим порядком у цій трансляції
            same_order_performance = performance_collection.find_one({
                "broadcast_id": ObjectId(broadcast_id),
                "order": order
            })
            if same_order_performance:
                error_message = 'Інший конкурсант вже має цей порядок у цій трансляції.'
                return render_template('performances/performance_add.html',
                                       contestants=list(contestant_collection.find()),
                                       songs=list(song_collection.find()),
                                       broadcasts=list(broadcast_collection.find()),
                                       error_message=error_message)

            # Додавання нового виступу
            performance_collection.insert_one({
                "contestant_id": ObjectId(contestant_id),
                "song_id": ObjectId(song_id),
                "broadcast_id": ObjectId(broadcast_id),
                "order": order,
            })
            flash('Виступ успішно доданий!', 'success')
            return redirect(url_for('performances'))
        except Exception as e:
            flash(f'Виникла помилка при додаванні виступу: {str(e)}', 'danger')

    return render_template('performances/performance_add.html',
                           contestants=list(contestant_collection.find()),
                           songs=list(song_collection.find()),
                           broadcasts=list(broadcast_collection.find()))


@app.route('/performance/<performance_id>/edit', methods=['GET', 'POST'])
@login_required
@roles_required('owner', 'administrator', 'operator')
def edit_performance(performance_id):
    if not is_valid_objectid(performance_id):
        flash('Невалідний ID виступу.', 'danger')
        return redirect(url_for('performances'))

    performance = performance_collection.find_one({"_id": ObjectId(performance_id)})

    if not performance:
        flash("Виступ не знайдено.", "danger")
        return redirect(url_for('performances'))

    if request.method == 'POST':
        try:
            contestant_id = request.form['contestant_id']
            song_id = request.form['song_id']
            broadcast_id = request.form['broadcast_id']
            order = int(request.form['order'])

            # Перевірка валідності ObjectId
            if not all(map(is_valid_objectid, [contestant_id, song_id, broadcast_id])):
                flash('Невалідний ID одного з полів.', 'danger')
                return redirect(url_for('edit_performance', performance_id=performance_id))

            # Перевірка: чи вже цей конкурсант має виступ на цьому ефірі (виключаючи поточний)
            existing_performance = performance_collection.find_one({
                "contestant_id": ObjectId(contestant_id),
                "broadcast_id": ObjectId(broadcast_id),
                "_id": {"$ne": ObjectId(performance_id)}
            })
            if existing_performance:
                error_message = 'Цей конкурсант вже має виступ у цій трансляції.'
                return render_template('performances/performance_edit.html', performance=performance,
                                       contestants=list(contestant_collection.find()),
                                       songs=list(song_collection.find()),
                                       broadcasts=list(broadcast_collection.find()),
                                       error_message=error_message)

            # Перевірка: чи вже існує виступ з таким самим порядком у цій трансляції (виключаючи поточний)
            same_order_performance = performance_collection.find_one({
                "broadcast_id": ObjectId(broadcast_id),
                "order": order,
                "_id": {"$ne": ObjectId(performance_id)}
            })
            if same_order_performance:
                error_message = 'Інший конкурсант вже має цей порядок у цій трансляції.'
                return render_template('performances/performance_edit.html', performance=performance,
                                       contestants=list(contestant_collection.find()),
                                       songs=list(song_collection.find()),
                                       broadcasts=list(broadcast_collection.find()),
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
            flash('Виступ успішно оновлено!', 'success')
            return redirect(url_for('performances'))
        except Exception as e:
            flash(f'Виникла помилка при оновленні виступу: {str(e)}', 'danger')

    return render_template('performances/performance_edit.html',
                           performance=performance,
                           contestants=list(contestant_collection.find()),
                           songs=list(song_collection.find()),
                           broadcasts=list(broadcast_collection.find()))


@app.route('/performance/<performance_id>/delete')
@login_required
@roles_required('owner')
def delete_performance(performance_id):
    if not is_valid_objectid(performance_id):
        flash('Невалідний ID виступу.', 'danger')
        return redirect(url_for('performances'))

    try:
        performance = performance_collection.find_one({"_id": ObjectId(performance_id)})
        if not performance:
            flash('Виступ не знайдено.', 'danger')
            return redirect(url_for('performances'))

        # Виконання каскадного видалення
        cascade_delete('performance', ObjectId(performance_id))

        # Видалення самого виступу
        performance_collection.delete_one({"_id": ObjectId(performance_id)})

        flash('Виступ та всі пов’язані записи успішно видалені!', 'success')
    except Exception as e:
        flash(f'Виникла помилка при видаленні виступу: {str(e)}', 'danger')

    return redirect(url_for('performances'))


# Маршрути для Трансляцій
@app.route('/broadcasts', methods=['GET', 'POST'])
@login_required
@roles_required('owner', 'administrator', 'operator', 'user')
def broadcasts():
    return render_template('broadcasts/broadcasts.html', broadcasts=list(broadcast_collection.find()))


@app.route('/broadcast/create', methods=['GET', 'POST'])
@login_required
@roles_required('owner', 'administrator')
def add_broadcast():
    if request.method == 'POST':
        try:
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
            flash('Трансляцію успішно додано!', 'success')
            return redirect(url_for('broadcasts'))
        except Exception as e:
            flash(f'Виникла помилка при додаванні трансляції: {str(e)}', 'danger')

    return render_template('broadcasts/broadcast_add.html')


@app.route('/broadcast/<broadcast_id>/edit', methods=['GET', 'POST'])
@login_required
@roles_required('owner', 'administrator', 'operator')
def edit_broadcast(broadcast_id):
    if not is_valid_objectid(broadcast_id):
        flash('Невалідний ID трансляції.', 'danger')
        return redirect(url_for('broadcasts'))

    broadcast = broadcast_collection.find_one({"_id": ObjectId(broadcast_id)})

    if not broadcast:
        flash("Трансляцію не знайдено.", "danger")
        return redirect(url_for('broadcasts'))

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
            flash('Трансляцію успішно оновлено!', 'success')
            return redirect(url_for('broadcasts'))
        except Exception as e:
            flash(f'Виникла помилка при оновленні трансляції: {str(e)}', 'danger')

    return render_template('broadcasts/broadcast_edit.html', broadcast=broadcast)


@app.route('/broadcast/<broadcast_id>/delete')
@login_required
@roles_required('owner', 'administrator')
def delete_broadcast(broadcast_id):
    if not is_valid_objectid(broadcast_id):
        flash('Невалідний ID трансляції.', 'danger')
        return redirect(url_for('broadcasts'))

    try:
        broadcast = broadcast_collection.find_one({"_id": ObjectId(broadcast_id)})
        if not broadcast:
            flash("Трансляцію не знайдено.", "danger")
            return redirect(url_for('broadcasts'))

        # Виконання каскадного видалення
        cascade_delete('broadcast', ObjectId(broadcast_id))

        # Видалення самої трансляції
        broadcast_collection.delete_one({"_id": ObjectId(broadcast_id)})

        flash('Трансляцію та всі пов’язані записи успішно видалені!', 'success')
    except Exception as e:
        flash(f'Виникла помилка при видаленні трансляції: {str(e)}', 'danger')

    return redirect(url_for('broadcasts'))



@app.route('/voting', methods=['GET', 'POST'])
@login_required
@roles_required('owner', 'administrator', 'operator', 'user')  # <-- New
def voting():
    broadcasts = []
    try:
        if request.method == 'POST':
            broadcast_id = request.form['broadcast_id']
        else:
            broadcast_id = request.args.get('broadcast_id')

        selected_broadcast = None
        performances = []
        contestants = []
        songs = []
        broadcasts = list(broadcast_collection.find())

        if broadcast_id:
            selected_broadcast = broadcast_collection.find_one({'_id': ObjectId(broadcast_id)})
            performances = list(performance_collection.find({'broadcast_id': ObjectId(broadcast_id)}))

            contestant_ids = {performance['contestant_id'] for performance in performances}
            song_ids = {performance['song_id'] for performance in performances}

            contestants = list(contestant_collection.find({"_id": {"$in": list(contestant_ids)}}))
            songs = list(song_collection.find({"_id": {"$in": list(song_ids)}}))

        return render_template(
            'voting/voting.html',
            broadcasts=broadcasts,
            performances=performances,
            contestants=contestants,
            songs=songs,
            selected_broadcast=selected_broadcast
        )
    except Exception as e:
        logger.error(f"Error in voting route: {str(e)}")
        flash('An error occurred while loading voting data.', 'danger')

    return render_template('voting/voting.html', broadcasts=broadcasts, performances=None, selected_broadcast=None)


@app.route('/select_broadcast_for_voting', methods=['POST'])
@login_required
@roles_required('owner', 'administrator', 'operator', 'user')
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
@roles_required('owner', 'administrator', 'operator')
def submit_votes():
    broadcast_id = request.form.get('broadcast_id')
    votes_data = request.form.get('votes')

    if not broadcast_id or not votes_data:
        flash('Invalid submission. Please try again.', 'danger')
        return redirect(url_for('broadcasts'))

    for performance_id, votes in votes_data.items():
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

        performance_collection.update_one(
            {"_id": ObjectId(performance_id)},
            {"$set": {"phone_votes": phone_votes, "sms_votes": sms_votes}}
        )

    flash('Votes successfully submitted!', 'success')
    return redirect(url_for('broadcasts'))


@app.route('/results', methods=['GET'])
@login_required
@roles_required('owner', 'administrator', 'operator', 'user')
def results():
    results = []
    for contestant in contestant_collection.find():
        # Підрахунок голосів від телефонів
        phone_votes_count = phone_voting_collection.count_documents({"contestant_id": contestant["_id"]})

        # Підрахунок голосів від SMS
        sms_votes_count = sms_voting_collection.count_documents({"contestant_id": contestant["_id"]})

        # Підрахунок балів від журі
        jury_scores = jury_voting_collection.find({"contestant_id": contestant["_id"]})
        total_jury_score = sum([score["score"] for score in jury_scores])  # Сума балів від журі

        # Загальна кількість голосів
        total_votes = phone_votes_count + sms_votes_count + total_jury_score

        results.append({
            "contestant": contestant,
            "phone_votes": phone_votes_count,
            "sms_votes": sms_votes_count,
            "jury_score": total_jury_score,
            "total_votes": total_votes
        })

    if not results:
        flash("Немає доступних результатів.", "warning")
    return render_template('results/results.html', results=results)


@app.route('/performance/<performance_id>/vote', methods=['GET', 'POST'])
@login_required
def vote_performance(performance_id):
    # Знаходимо дані перформансу, журі та пов'язаного бродкасту
    performance = performance_collection.find_one({"_id": ObjectId(performance_id)})
    broadcast_id = performance["broadcast_id"] if performance else None
    contestant_id = performance["contestant_id"] if performance else None
    juries = list(jury_collection.find())

    if request.method == 'POST':
        phone_number = request.form.get('phone_number')
        vote_type = request.form.get('vote_type')

        # Якщо голос від глядача (sms або phone)
        if vote_type in ['sms', 'phone'] and phone_number:
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

            flash('Viewer vote recorded successfully!', 'success')

        # Якщо голос від журі
        elif vote_type == 'jury':
            jury_id = request.form.get('jury_id')
            score = int(request.form.get('score', 0))

            if jury_id and 1 <= score <= 10:
                jury_vote_data = {
                    "performance_id": ObjectId(performance_id),
                    "broadcast_id": broadcast_id,
                    "contestant_id": contestant_id,
                    "jury_id": ObjectId(jury_id),
                    "score": score
                }
                jury_voting_collection.insert_one(jury_vote_data)
                flash('Jury vote recorded successfully!', 'success')
            else:
                flash('Please select a valid jury and score between 1 and 10.', 'danger')

        return redirect(url_for('performances'))

    return render_template('voting/vote.html', performance=performance, juries=juries)


# User Management Routes
@app.route('/users', methods=['GET'])
@login_required
@roles_required('owner','administrator')
def manage_users():
    users = list(keys_collection.find())
    return render_template('users/users.html', users=users)


@app.route('/users/<user_id>/edit', methods=['GET', 'POST'])
@login_required
@roles_required('owner','administrator')
def edit_user(user_id):
    user = keys_collection.find_one({'_id': ObjectId(user_id)})
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('manage_users'))

    if request.method == 'POST':
        new_role = request.form['role']
        current_user_role = session.get('role')

        if current_user_role == 'administrator' and new_role == 'owner':
            flash('Administrators cannot assign the owner role.', 'danger')
            return redirect(url_for('manage_users'))

        allowed_roles = ['user', 'operator', 'administrator']
        if current_user_role == 'administrator' and new_role not in allowed_roles:
            flash('You do not have permission to assign this role.', 'danger')
            return redirect(url_for('manage_users'))

        # Owners can assign any role
        if current_user_role == 'owner':
            allowed_roles = ['user', 'operator', 'administrator', 'owner']
            if new_role not in allowed_roles:
                flash('Invalid role selected.', 'danger')
                return redirect(url_for('manage_users'))

        keys_collection.update_one({'_id': ObjectId(user_id)}, {'$set': {'role': new_role}})
        flash('User role updated successfully!', 'success')
        return redirect(url_for('manage_users'))

    roles = ['user', 'operator', 'administrator', 'owner']
    return render_template('users/users_edit.html', user=user, roles=roles)


@app.route('/performers_by_song_and_city', methods=['GET', 'POST'])
@login_required
def performers_by_song_and_city():
    songs = list(song_collection.find())
    cities = contestant_collection.distinct("city")
    performers = []

    if request.method == 'POST':
        song_id = request.form.get('song')
        city = request.form.get('city')

        # Фільтр для запиту
        query = {}
        if city:
            query["city"] = city
        if song_id:
            performances = performance_collection.find({"song_id": ObjectId(song_id)})
            performer_ids = {performance["contestant_id"] for performance in performances}
            query["_id"] = {"$in": list(performer_ids)}

        # Отримуємо виконавців на основі фільтра
        performers = list(contestant_collection.find(query))

        # Додаємо інформацію про пісню для кожного виконавця
        for performer in performers:
            performer_performance = performance_collection.find_one(
                {"contestant_id": performer["_id"], "song_id": ObjectId(song_id)}) if song_id else None
            if performer_performance:
                song = song_collection.find_one({"_id": ObjectId(song_id)})
                performer["song"] = song["name"] if song else "Unknown Song"
            else:
                performer["song"] = "Unknown Song"
    if not results:
        flash("Немає доступних результатів.", "warning")
    return render_template('queries/performers_by_song_and_city.html', songs=songs, cities=cities,
                           performers=performers)


@app.route('/artists_and_songs_by_broadcast', methods=['GET', 'POST'])
@login_required
@roles_required('owner', 'administrator', 'operator', 'user')  # <-- New
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
@roles_required('owner', 'administrator', 'operator', 'user')  # <-- New
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
@roles_required('owner', 'administrator', 'operator', 'user')  # <-- New
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
@roles_required('owner', 'administrator', 'operator', 'user')  # <-- New
def votes_in_first_broadcast():
    broadcasts = list(broadcast_collection.find().sort("date_of_live", 1))  # Fixed sort key
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
@roles_required('owner', 'administrator', 'operator', 'user')  # <-- New
def broadcast_schedule():
    broadcasts = list(broadcast_collection.find().sort("date_of_live", 1))
    return render_template('queries/broadcast_schedule.html', broadcasts=broadcasts)


@app.route('/max_sms_votes', methods=['GET', 'POST'])
@login_required
@roles_required('owner', 'administrator', 'operator', 'user')  # <-- New
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
@roles_required('owner', 'administrator', 'operator', 'user')
def winner_of_contest():
    contestants_results = []

    # Підраховуємо голоси та бали для кожного конкурсанта
    for contestant in contestant_collection.find():
        # Підрахунок телефонних та SMS голосів
        phone_votes_count = phone_voting_collection.count_documents({"contestant_id": contestant["_id"]})
        sms_votes_count = sms_voting_collection.count_documents({"contestant_id": contestant["_id"]})

        # Підрахунок балів від журі
        jury_votes = jury_voting_collection.find({"contestant_id": contestant["_id"]})
        total_jury_score = sum([vote["score"] for vote in jury_votes])

        # Загальна кількість голосів та балів
        total_votes = phone_votes_count + sms_votes_count + total_jury_score

        contestants_results.append({
            "contestant": contestant,
            "phone_votes": phone_votes_count,
            "sms_votes": sms_votes_count,
            "jury_score": total_jury_score,
            "total_votes": total_votes
        })

    # Сортуємо конкурсантів за загальною кількістю голосів у порядку спадання
    contestants_results.sort(key=lambda x: x["total_votes"], reverse=True)

    # Визначаємо переможця та призерів
    winner = contestants_results[0] if contestants_results else None
    second_place = contestants_results[1] if len(contestants_results) > 1 else None
    third_place = contestants_results[2] if len(contestants_results) > 2 else None

    return render_template(
        'queries/winner_of_contest.html',
        winner=winner,
        second_place=second_place,
        third_place=third_place
    )


@app.route('/sms_messages_per_broadcast', methods=['GET', 'POST'])
@login_required
@roles_required('owner', 'administrator', 'operator', 'user')  # <-- New
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
@roles_required('owner', 'administrator', 'operator', 'user')  # <-- New
def calls_from_number():
    broadcasts = list(broadcast_collection.find())
    total_calls = 0
    phone_number = request.form.get('phoneNumber')
    broadcast_id = request.form.get('broadcast')
    if phone_number and broadcast_id:
        calls = list(
            phone_voting_collection.find({"phone_number": phone_number, "broadcast_id": ObjectId(broadcast_id)}))
        total_calls = len(calls)
    return render_template('queries/calls_from_number.html', broadcasts=broadcasts, total_calls=total_calls)


@app.route('/create_collection', methods=['GET', 'POST'])
@login_required
@roles_required('owner')
def create_collection():
    if request.method == 'POST':
        collection_name = request.form.get('collection_name').strip()

        # Валідація імені колекції
        if not collection_name:
            flash('Назва колекції не може бути порожньою.', 'danger')
            return redirect(url_for('create_collection'))

        # Перевірка наявності колекції
        if collection_name in db.list_collection_names():
            flash('Колекція з такою назвою вже існує.', 'danger')
            return redirect(url_for('create_collection'))

        try:
            # Створення нової колекції
            db.create_collection(collection_name)
            flash(f'Колекція "{collection_name}" успішно створена!', 'success')
            return redirect(url_for('create_collection'))
        except Exception as e:
            flash(f'Виникла помилка при створенні колекції: {str(e)}', 'danger')
            return redirect(url_for('create_collection'))

    return render_template('collections/create_collection.html')


@app.route('/delete_collection', methods=['GET', 'POST'])
@login_required
@roles_required('owner')  # Доступ лише для власника
def delete_collection():
    if request.method == 'POST':
        collection_name = request.form.get('collection_name').strip()

        # Валідація імені колекції
        if not collection_name:
            flash('Назва колекції не може бути порожньою.', 'danger')
            return redirect(url_for('delete_collection'))

        # Перевірка наявності колекції
        if collection_name not in db.list_collection_names():
            flash('Колекція з такою назвою не існує.', 'danger')
            return redirect(url_for('delete_collection'))

        # Захист системних колекцій
        system_collections = ['system.indexes', 'system.users', 'system.roles']
        if collection_name in system_collections:
            flash('Ви не можете видалити системну колекцію.', 'danger')
            return redirect(url_for('delete_collection'))

        try:
            # Видалення колекції
            db.drop_collection(collection_name)
            flash(f'Колекція "{collection_name}" успішно видалена!', 'success')
            return redirect(url_for('delete_collection'))
        except Exception as e:
            flash(f'Виникла помилка при видаленні колекції: {str(e)}', 'danger')
            return redirect(url_for('delete_collection'))

    # Отримання списку колекцій, які можна видалити (виключаючи системні)
    system_collections = ['system.indexes', 'system.users', 'system.roles']
    collections = [name for name in db.list_collection_names() if name not in system_collections]

    return render_template('collections/delete_collection.html', collections=collections)


@app.route('/search_contestants', methods=['GET', 'POST'])
@login_required
@roles_required('owner', 'administrator', 'operator', 'user')
def search_contestants():
    query = {}
    results = []
    if request.method == 'POST':
        name = request.form.get('name').strip()
        surname = request.form.get('surname').strip()
        city = request.form.get('city').strip()
        age = request.form.get('age').strip()

        if name:
            query['name'] = {'$regex': name, '$options': 'i'}  # Case-insensitive search
        if surname:
            query['surname'] = {'$regex': surname, '$options': 'i'}
        if city:
            query['city'] = {'$regex': city, '$options': 'i'}
        if age:
            try:
                query['age'] = int(age)
            except ValueError:
                flash('Вік повинен бути числом.', 'danger')
                return redirect(url_for('search_contestants'))

        results = list(contestant_collection.find(query))

        if not results:
            flash('Нічого не знайдено за вашими критеріями.', 'info')

    return render_template('contestants/search_contestants.html', results=results)


@app.route('/search_songs', methods=['GET', 'POST'])
@login_required
@roles_required('owner', 'administrator', 'operator', 'user')
def search_songs():
    query = {}
    results = []
    if request.method == 'POST':
        name = request.form.get('name').strip()
        author = request.form.get('author').strip()
        genre = request.form.get('genre').strip()

        if name:
            query['name'] = {'$regex': name, '$options': 'i'}
        if author:
            query['author'] = {'$regex': author, '$options': 'i'}
        if genre:
            query['genre'] = {'$regex': genre, '$options': 'i'}

        results = list(song_collection.find(query))

        if not results:
            flash('Нічого не знайдено за вашими критеріями.', 'info')

    return render_template('songs/search_songs.html', results=results)


@app.route('/search_performances', methods=['GET', 'POST'])
@login_required
@roles_required('owner', 'administrator', 'operator', 'user')
def search_performances():
    query = {}
    results = []
    if request.method == 'POST':
        contestant_name = request.form.get('contestant_name').strip()
        song_name = request.form.get('song_name').strip()
        broadcast_name = request.form.get('broadcast_name').strip()
        order = request.form.get('order').strip()

        if contestant_name:
            # Шукаємо конкусанта та додаємо фільтр по contestant_id
            contestants = list(contestant_collection.find({'name': {'$regex': contestant_name, '$options': 'i'}}))
            contestant_ids = [contestant['_id'] for contestant in contestants]
            if contestant_ids:
                query['contestant_id'] = {'$in': contestant_ids}
            else:
                # Якщо не знайдено, результати пусті
                results = []
                flash('Нічого не знайдено за вашим ім\'ям конкурсанта.', 'info')
                return render_template('performances/search_performances.html', results=results)

        if song_name:
            songs = list(song_collection.find({'name': {'$regex': song_name, '$options': 'i'}}))
            song_ids = [song['_id'] for song in songs]
            if song_ids:
                query['song_id'] = {'$in': song_ids}
            else:
                results = []
                flash('Нічого не знайдено за назвою пісні.', 'info')
                return render_template('performances/search_performances.html', results=results)

        if broadcast_name:
            broadcasts = list(broadcast_collection.find({'name': {'$regex': broadcast_name, '$options': 'i'}}))
            broadcast_ids = [broadcast['_id'] for broadcast in broadcasts]
            if broadcast_ids:
                query['broadcast_id'] = {'$in': broadcast_ids}
            else:
                results = []
                flash('Нічого не знайдено за назвою трансляції.', 'info')
                return render_template('performances/search_performances.html', results=results)

        if order:
            try:
                query['order'] = int(order)
            except ValueError:
                flash('Порядок повинен бути числом.', 'danger')
                return redirect(url_for('search_performances'))

        results = list(performance_collection.find(query))

        if not results:
            flash('Нічого не знайдено за вашими критеріями.', 'info')

    return render_template('performances/search_performances.html', results=results)


@app.route('/search_broadcasts', methods=['GET', 'POST'])
@login_required
@roles_required('owner', 'administrator', 'operator', 'user')
def search_broadcasts():
    query = {}
    results = []
    if request.method == 'POST':
        name = request.form.get('name').strip()
        date_of_live = request.form.get('date_of_live').strip()
        description = request.form.get('description').strip()

        if name:
            query['name'] = {'$regex': name, '$options': 'i'}
        if date_of_live:
            query['date_of_live'] = {'$regex': date_of_live, '$options': 'i'}
        if description:
            query['description'] = {'$regex': description, '$options': 'i'}

        results = list(broadcast_collection.find(query))

        if not results:
            flash('Нічого не знайдено за вашими критеріями.', 'info')

    return render_template('broadcasts/search_broadcasts.html', results=results)


@app.route('/search_jury', methods=['GET', 'POST'])
@login_required
@roles_required('owner', 'administrator', 'operator', 'user')
def search_jury():
    query = {}
    results = []
    if request.method == 'POST':
        name = request.form.get('name').strip()
        surname = request.form.get('surname').strip()
        position = request.form.get('position').strip()

        if name:
            query['name'] = {'$regex': name, '$options': 'i'}
        if surname:
            query['surname'] = {'$regex': surname, '$options': 'i'}
        if position:
            query['position'] = {'$regex': position, '$options': 'i'}

        results = list(jury_collection.find(query))

        if not results:
            flash('Нічого не знайдено за вашими критеріями.', 'info')

    return render_template('jury/search_jury.html', results=results)


if __name__ == '__main__':
    app.run(debug=True)
