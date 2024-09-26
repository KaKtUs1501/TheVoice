from pymongo import MongoClient
from pymongo.collection import Collection
from typing import List, Dict, Any

class Song:
    def __init__(self, name: str, author: str, genre: str):
        self.name = name
        self.author = author
        self.genre = genre

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "author": self.author,
            "genre": self.genre
        }

class SongDatabase:
    def __init__(self, db_uri: str, db_name: str):
        self.client = MongoClient(db_uri)
        self.db = self.client[db_name]
        self.collection: Collection = self.db["song"]  # Перевірте, що немає self.collection()

    def add_song(self, song: Song) -> None:
        self.collection.insert_one(song.to_dict())  # Правильний виклик методу

    def get_song(self, name: str) -> Dict[str, Any]:
        return self.collection.find_one({"name": name})  # Виклик методу без помилки

    def get_all_songs(self) -> List[Dict[str, Any]]:
        return list(self.collection.find())  # Виклик методу без помилки

    def update_song(self, name: str, updates: Dict[str, Any]) -> None:
        self.collection.update_one({"name": name}, {"$set": updates})  # Виклик методу без помилки

    def delete_song(self, name: str) -> None:
        self.collection.delete_one({"name": name})  # Виклик методу без помилки
