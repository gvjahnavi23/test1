from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import bson
import gunicorn
import json
from bson import ObjectId
from flask import Response
from werkzeug.utils import secure_filename
import mimetypes
import imghdr

app = Flask(__name__)
with open("test\config.json", "r") as file:
    config = json.load(file)
    
app.secret_key = config["secret_key" ""]
uri = config["uri"]

# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))
# MongoDB setup
db = client["mydatabase"]
collection2 = db["mails"]
collection3 = db["posts"]
comments_db = db["comments_db"]
likes_db = db["likes"]

#entry page

@app.route('/')
def index():
    return render_template('index.html')


#new user registration

@app.route('/register', methods=['POST'])
def register():
    name = request.form['name']
    email = request.form['email']
    password = request.form['password']
    if not email or not password:
        return jsonify({"message": "Email and password are required!", "success": False}), 400
    # Check if email already exists
    if collection2.find_one({'email': email}) is not None:
        return jsonify({"message": "Email already exists", "success": False}), 400
    if collection2.find_one({'name': name}) is not None:
        return jsonify({"message": "Name is already taken, \n Go for unique name", "success": False}), 400

    # Insert new user
    user_data = {"name": name, "email": email, "password": password}
    collection2.insert_one(user_data)
    return jsonify({"message": "Registration successful", "success": True})

#old user login

@app.route('/login', methods=['GET', 'POST'])
def login():
    email = request.form['email']
    password = request.form['password']
    if not email or not password:
        return jsonify({"message": "Email and password are required!", "success": False}), 400
    user = collection2.find_one({'email': email})

    if user is None:
        return jsonify({"message": "Email does not exist", "success": False}), 400

    if user['password'] == password:
        session['user_name'] = user['name']
        session['email'] = user['email']
        return jsonify({"message":"Login Successful", "success": True})
    else:
        return jsonify({"message": "Incorrect password", "success": False}), 400

#old user forgot password

@app.route('/forgot_password', methods=['POST'])
def forgot_password():
    email = request.form['email']
    new_password = request.form['newPassword']
    confirm_password = request.form['confirmPassword']

    if new_password != confirm_password:
        return jsonify({"message": "Passwords do not match", "success": False}), 400

    user = collection2.find_one({'email': email})

    if user is None:
        return jsonify({"message": "Email does not exist", "success": False}), 400

    collection2.update_one({'email': email}, {'$set': {'password': new_password}})
    return jsonify({"message": "Password updated successfully", "success": True})

#home page to display posts

@app.route('/home')
def home():
    # Fetch posts from the database (assuming posts are in 'posts' collection)
    postts = db['posts'].find()  # Adjust collection name if needed
    user_name = session.get('user_name')
    # commentts = db['comments_db'].find()
    comments = {}
    for commentt in db['comments_db'].find():
        title = commentt.get('title')
        author = commentt.get('author')
        tit = title+author
        if title and author:
            if tit not in comments:
                comments[tit] = []
            comments[tit].append(commentt.get('comment'))
    return render_template('home.html',posts = postts, user_name = user_name, comments = comments)


#display the vedio included in the post

@app.route('/media/<post_id>')
def get_media(post_id):
    # Retrieve the post by its ID from MongoDB
    post = collection3.find_one({'_id': ObjectId(post_id)})
    
    # Check if the post exists and contains media data (either image or video)
    if post:
        # If there's an image
        if post.get('image'):
            image_data = post['image']
            # Use imghdr to detect image type
            image_type = imghdr.what(None, h=image_data)
            mimetype = f"image/{image_type}" if image_type else 'image/jpeg'
            return Response(image_data, mimetype=mimetype)

        # If there's a video
        elif post.get('video'):
            video_data = post['video']
            filename = post.get('filename', 'video.mp4')  # Use the filename to determine the MIME type
            video_type, _ = mimetypes.guess_type(filename)
            mimetype = video_type if video_type else 'video/mp4'
            return Response(video_data, mimetype=mimetype)
        
        
    # If no media found
    return 'Media not found', 404



#display the write post form

@app.route('/write_post', methods=['GET'])
def write_post():
    return render_template('write_post.html')

#submit the post

@app.route('/submit_post', methods=['POST'])
def submit_post():
    # Get data from the form
    title = request.form['title']
    content = request.form['content']
    email = session.get('email')
    name = session.get('user_name')
    media = request.files.get('media')
    # print(media)
    # Insert the post into the MongoDB collection
    if email==collection2.find_one({'email':email})['email']: 
        post_data = {
            'title': title,
            'content': content,
            'mail' : email,
            'name' : name
        }
        if media:
            media_type = media.content_type  # Get MIME type of the uploaded file
            print(media_type)
        
            # Check if the uploaded file is an image or video
            if media_type.startswith('image/'):
                # Handle image
                media_binary = media.read()
                post_data['image'] = bson.Binary(media_binary)
            elif media_type.startswith('video/'):
                # Handle video
                media_binary = media.read()
                post_data['video'] = bson.Binary(media_binary)
                post_data['filename'] = secure_filename(media.filename)  # Save the original filename for later reference
            
    # Insert post data into MongoDB
        collection3.insert_one(post_data)
        return redirect(url_for('home'))

    else:
        return redirect(url_for('index'))
    

@app.route('/display')
def display():
    mail = session.get('email')
    name = session.get('user_name')

    p = collection2.find_one({'name': name, 'email': mail})  # Find user document

    if p:
        liked_posts = p.get('liked_posts', [])  # Get liked posts, default to empty list
        likess = len(liked_posts)
    else:
        likes = 0
        liked_posts = []
    
    author = collection3.find({'mail':mail, 'name':name})
    post_titles = []
    if author:
        
        for postt in collection3.find({'mail':mail, 'name':name}):
            title = postt['title']
            likes = postt['likes']
            post_titles.append([title, likes])

    return render_template('profile.html', names=name, mail=mail, like=likess, liked_posts=liked_posts, post_titles= post_titles)

@app.route('/display_author/<author_name>')
def display_author(author_name):
    data = collection2.find_one({'name' : author_name})
    if data is not None:
        mail = data['email']
        name = data['name']
        post_titles = []
        for postt in collection3.find({'mail':mail, 'name':name}):
            title = postt['title']
            likes = postt['likes']
            post_titles.append([title, likes])
    p = collection2.find_one({'name': name, 'email': mail})  # Find user document

    if p:
        likes = p.get('likes', 0)  # Get like count, default to 0
        liked_posts = p.get('liked_posts', [])  # Get liked posts, default to empty list
    else:
        likes = 0
        liked_posts = []
        print(post_titles)
    return render_template('author.html', mail = mail, name = name, post_titles = post_titles, liked_posts = liked_posts)
    
@app.route('/add_like', methods = ['POST'])
def add_like():
    title = request.form.get('title')  # Get the title of the post
    author = request.form.get('author')
    name = session.get('user_name')
    profile = collection2.find_one({'name': name})

    # Check if the user has already liked the post
    existing_like = likes_db.find_one({'title': title, 'author': author, 'liked_by': name})
    if existing_like:
        return jsonify({'status': 'error', 'message': 'You have already liked this post.'})  # Send response

    if not existing_like:  # Proceed only if the user hasn't liked the post yet
        fin = collection3.find_one({'title': title, 'name': author})
        
        if fin:
            # Increment the 'likes' field in MongoDB
            collection3.update_one(
                {'_id': ObjectId(fin['_id'])},  # Find the post by its ID
                {'$inc': {'likes': 1}}  # Increment 'likes' by 1
            )

        if profile and '_id' in profile:
            # Increment the like count in the user's profile
            collection2.update_one(
                {'_id': profile['_id']},
                {
                    '$inc': {'likes': 1}, 
                    '$addToSet': {'liked_posts': title + " by " + author}  
                },
                upsert=True
            )

            # Update or Insert Like Data in likes_db
            likes_db.update_one(
                {'title': title, 'author': author},  # Find document by title & author
                {
                    '$inc': {'likes': 1},  # Increment like count
                    '$addToSet': {'liked_by': name}  # Add user to liked_by array (no duplicates)
                },
                upsert=True  # If not found, create a new document
            )

            ss = likes_db.find_one({'title': title, 'author': author})
            

        return jsonify({'status': 'success', 'likes': ss['likes']})
        # return redirect('/home')

    
    
@app.route('/add_comment', methods=['POST'])
def add_comment():
    title = request.form.get('title')  # Get the title of the post
    comment = request.form.get('comment')  # Get the comment text
    author = request.form.get('author')
    name = session.get('user_name')
    comment = name+":    "+comment
    print(comment)
    comment_data = {
        'title' : title,
        'author' : author,
        'comment' : comment
    }
    if title and comment:
        ss = comments_db.find_one({'title':title,'autor':author})
        if  ss is None:
            comments_db.insert_one(comment_data) 
        else:
            ss['comment'].append(comment)
        return redirect('/home')  # Redirect back to the home page
    else:
        return "Invalid input", 400

# Redirect to home page or a success page after submission
@app.route('/logout')
def logout():
    session.clear()  # Remove user_name from session
    return index()  # Redirect to login page after logout



if __name__ == '__main__':
    app.run(debug=True)
