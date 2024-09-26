from flask import Flask, render_template, request, redirect, url_for, flash, session
from pymongo import MongoClient
from bson import ObjectId

client = MongoClient('localhost', 27017)
db = client['voice']
keys_collection = db['keys']
contestant_collection = db['contestant']
jury_collection = db['jury']
song_collection = db['song']


class Contestant:
    def view(contestant_id):
        contestant = contestant_collection.find_one({"_id": ObjectId(contestant_id)})
        if not contestant:
            flash("Contestant not found.", "danger")
            return redirect(url_for('home'))
        return render_template('contestants/contestant_profile.html', contestant=contestant)

    def delete(contestant_id):
        contestant_collection.delete_one({"_id": ObjectId(contestant_id)})
        flash('Contestant deleted successfully!', 'success')
        return redirect(url_for('dashboard'))

    def edit(contestant_id):
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
            return redirect(url_for('contestant_view', contestant_id=contestant_id))

        return render_template('contestants/contestant_edit.html', contestant=contestant)
