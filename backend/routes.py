from . import app
import os
import json
import pymongo
from flask import jsonify, request, make_response, abort, url_for  # noqa; F401
from pymongo import MongoClient
from bson import json_util
from pymongo.errors import OperationFailure
from pymongo.results import InsertOneResult
from bson.objectid import ObjectId
import sys

SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
json_url = os.path.join(SITE_ROOT, "data", "songs.json")
songs_list: list = json.load(open(json_url))

# client = MongoClient(
#     f"mongodb://{app.config['MONGO_USERNAME']}:{app.config['MONGO_PASSWORD']}@localhost")
mongodb_service = os.environ.get('MONGODB_SERVICE')
mongodb_username = os.environ.get('MONGODB_USERNAME')
mongodb_password = os.environ.get('MONGODB_PASSWORD')
mongodb_port = os.environ.get('MONGODB_PORT')

print(f'The value of MONGODB_SERVICE is: {mongodb_service}')

if mongodb_service == None:
    app.logger.error('Missing MongoDB server in the MONGODB_SERVICE variable')
    # abort(500, 'Missing MongoDB server in the MONGODB_SERVICE variable')
    sys.exit(1)
if mongodb_username and mongodb_password:
    url = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_service}"
else:
    url = f"mongodb://{mongodb_service}"


print(f"connecting to url: {url}")

try:
    client = MongoClient(url)
except OperationFailure as e:
    app.logger.error(f"Authentication error: {str(e)}")

db = client.songs
db.songs.drop()
db.songs.insert_many(songs_list)

def parse_json(data):
    return json.loads(json_util.dumps(data))

######################################################################
# INSERT CODE HERE
######################################################################
@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "OK"}), 200


@app.route('/count', methods=['GET'])
def count():
    try:
        count = db.songs.count_documents({})
        return jsonify({"count": count}), 200
    except Exception as e:
        app.logger.error(f"Error counting documents: {e}")
        return jsonify({"error": "Database error"}), 500

@app.route('/song', methods=['GET'])
def songs():
    try:
        songs_cursor = db.songs.find({})
        songs_list = list(songs_cursor)  # Cursor to list
        return jsonify({"songs": parse_json(songs_list)}), 200
    except Exception as e:
        app.logger.error(f"Failed to retrieve songs: {e}")
        return jsonify({"error": "Failed to retrieve songs"}), 500

@app.route('/song/<int:id>', methods=['GET'])
def get_song_by_id(id):
    try:
        song = db.songs.find_one({"id": id})
        if song:
            return jsonify(parse_json(song)), 200
        else:
            return jsonify({"message": f"song with id {id} not found"}), 404
    except Exception as e:
        app.logger.error(f"Error fetching song with id {id}: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/song', methods=['POST'])
def create_song():
    try:
        song = request.get_json()
        song_id = song.get('id')

        if not song_id or not song.get('title') or not song.get('lyrics'):
            return jsonify({"error": "Missing required fields"}), 400

        existing_song = db.songs.find_one({"id": song_id})
        if existing_song:
            return jsonify({"Message": f"song with id {song_id} already present"}), 302

        result = db.songs.insert_one(song)
        return jsonify({"inserted id": parse_json(result.inserted_id)}), 201

    except Exception as e:
        app.logger.error(f"Error creating song: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route('/song/<int:id>', methods=['PUT'])
def update_song(id):
    try:
        updated_data = request.get_json()

        # Check if song exists
        song = db.songs.find_one({"id": id})
        if not song:
            return jsonify({"message": "song not found"}), 404

        # Update the song
        result = db.songs.update_one({"id": id}, {"$set": updated_data})

        if result.modified_count == 0:
            return jsonify({"message": "song found, but nothing updated"}), 200

        # Return the updated song
        updated_song = db.songs.find_one({"id": id})
        return jsonify(parse_json(updated_song)), 201

    except Exception as e:
        app.logger.error(f"Error updating song with id {id}: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route('/song/<int:id>', methods=["DELETE"])
def delete_song(id):
    try:
        result = db.songs.delete_one({"id": id})
        
        if result.deleted_count == 0:
            return jsonify({"message": "song not found"}), 404
        
        return '', 204  # No content

    except Exception as e:
        app.logger.error(f"Error deleting song with id {id}: {e}")
        return jsonify({"error": "Internal server error"}), 500
