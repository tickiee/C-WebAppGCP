from flask import Flask, flash, redirect, url_for, render_template, request, send_file
from google.cloud import datastore, storage

import datetime
import pytz
import json

import os
from werkzeug.utils import secure_filename
import tempfile

timezone = pytz.timezone("Australia/Victoria")

app = Flask(__name__)
app.config['SECRET_KEY'] = "abc123!@#zxc"
UPLOAD_FOLDER = '/tmp'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
datastore_client = datastore.Client("myassignment1-task1")

# Starting .html page, the login page
@app.route('/')
def root():
    return redirect(url_for('loginpage'))

# register.html page
@app.route('/registerpage', methods = ['POST'])
def registerpage():
    return render_template("registerpage.html")

# return to login.html page
@app.route('/loginpage')
def loginpage():
    return render_template("index.html")

# forumpage.html
@app.route('/forumpage/<string:entityUsername>')
def forumpage(entityUsername):
    # Gets image bucket
    bucket = "a1-task1-images"

    # Gets user details
    query = datastore_client.query(kind = "user")
    query.add_filter("user_name", "=", entityUsername)
    results = list(query.fetch())
    id = results[0]["id"]
    imagename = id + "_image.png"

    return render_template("forumpage.html", bucket = bucket, imagename = imagename, entityUsername = entityUsername)

# log in function
@app.route('/login', methods = ['POST'])
def login():
    id = request.form.get('id')
    password = request.form.get('password')

    loginValidationQuery = datastore_client.query(kind = "user")
    loginValidationQuery.add_filter("id", "=", id)
    loginValidationQuery.add_filter("password", "=", password)
    results = list(loginValidationQuery.fetch())

    # id and password authentication 
    if(len(results) == 1):
        return redirect(url_for('forumpage', entityUsername = results[0]["user_name"]))
    else:
        flash("ID or password is invalid! Please retry.")
        return render_template("index.html")

# user registration function
@app.route('/register', methods = ['POST'])
def register():
    id = request.form.get('id')
    username = request.form.get('username')
    password = request.form.get('password')
    image = request.files['file']
    

    checkIdExistQuery = datastore_client.query(kind = "user")
    checkIdExistQuery.add_filter("id", "=", id)
    results = list(checkIdExistQuery.fetch())

    # checks if id has already existed in database
    if(len(results) > 0):
        flash("The id already exists! Please use another id.")
        return render_template("registerpage.html")
    else:

        checkUNExistQuery = datastore_client.query(kind = "user")
        checkUNExistQuery.add_filter("user_name", "=", username)
        results = list(checkUNExistQuery.fetch())

        # checks if username has already existed in database
        if(len(results) > 0):
            flash("The username already exists! Please use another username.")
            return render_template("registerpage.html")
        else:
            # add image to bucket
            filename = secure_filename(image.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(filepath)

            storage_client = storage.Client("myassignment1-task1")
            bucket = storage_client.bucket("a1-task1-images")
            blobname = str(id) + "_image.png"
            blob = bucket.blob(blobname)
            blob.upload_from_filename(filepath)
            blob.make_public()

            # add user info to datastore
            entity = datastore.Entity(key = datastore_client.key('user',  id))
            entity.update({
                'id' : id,
                'user_name' : username,
                'password' : password
            })

            datastore_client.put(entity)

            return redirect(url_for('loginpage'))

# userpage.html
@app.route('/viewUserPage/<string:entityUsername>')
def viewUserPage(entityUsername):
    return render_template("userpage.html", entityUsername = entityUsername)

# changing user password function
@app.route('/changepassword', methods = ['post'])
def changepassword():
    username = request.form.get('username')
    currentPassword = request.form.get('current_password')
    newPassword = request.form.get('new_password')

    query = datastore_client.query(kind = "user")
    query.add_filter("user_name", "=", username)
    
    query_entity = query.fetch()
    results = list(query.fetch())

    # current password authentication
    if(results[0]["password"] != currentPassword):
        flash("The current password does not match. Please try again.")
        return render_template("userpage.html", entityUsername = username)
    else:
        # updates new password
        id = results[0]["id"]

        with datastore_client.transaction():
            key = datastore_client.key("user", id)
            task = datastore_client.get(key)

            task["password"] = newPassword

            datastore_client.put(task)
        
        return render_template("index.html")

# messagepage.html
@app.route('/messagepage/<string:entityUsername>')
def messagepage(entityUsername):
    query = datastore_client.query(kind = "message")
    query.order = ['-datetime']

    results = list(query.fetch(10))

    messagebucket = "a1-task1-messageimages"
    userbucket = "a1-task1-images"

    return render_template("messagepage.html", entityUsername = entityUsername, 
    messagebucket = messagebucket, userbucket = userbucket,
    results = results)
    

# latestmessages.html
@app.route('/displaylatestmessages/<string:entityUsername>')
def displaylatestmessages(entityUsername):
    return render_template("latestmessages.html", entityUsername = entityUsername)

# post message function
@app.route('/postmessage', methods = ['post'])
def postmessage():
    subject = request.form.get('subject')
    message = request.form.get('message')
    username = request.form.get('username')
    image = request.files['file']

    # Store imageindex, for updating image during edit image
    imageIndex = 1

    # Gets userimage in string, to display user image in messagepage.html
    query = datastore_client.query(kind = "user")
    query.add_filter("user_name", "=", username)
    
    querylist = list(query.fetch())
    results = querylist[0]

    # adds details to datastore
    entity = datastore.Entity(key = datastore_client.key('message'))
    entity["subject"] = subject
    entity["messagetext"] = message
    entity["user_name"] = username
    entity["user_image"] = results["id"] + "_image.png"
    entity["imageindex"] = imageIndex
    entity["datetime"] = datetime.datetime.now()

    datastore_client.put(entity)

    entity_id = entity.key.id
    entity_id_instring = str(entity_id)

    # adds image to bucket
    filename = secure_filename(image.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    image.save(filepath)

    storage_client = storage.Client("myassignment1-task1")
    bucket = storage_client.bucket("a1-task1-messageimages")
    blobname = entity_id_instring + "_" + str(imageIndex) + "_image.png"
    blob = bucket.blob(blobname)
    blob.upload_from_filename(filepath)
    blob.make_public()

    # adds detail to imagename
    with datastore_client.transaction():
        key = datastore_client.key("message", entity_id)
        task = datastore_client.get(key)

        task["imagename"] = blobname

        datastore_client.put(task)

    flash("Message posted!")
    return redirect(url_for('messagepage', entityUsername = username))

# userpostedmessages.html
@app.route('/userpostedmessages/<string:entityUsername>')
def userpostedmessages(entityUsername):
    query = datastore_client.query(kind = "message")
    query.add_filter("user_name", "=", entityUsername)

    results = list(query.fetch())

    bucket = "a1-task1-messageimages"

    return render_template("userpostedmessages.html", entityUsername = entityUsername, bucket = bucket, results = results)

# editmessage.html on the chosen message
@app.route('/editmessage/<string:entityUsername>', methods = ['post'])
def editmessage(entityUsername):
    subject = request.form.get('subject')
    query = datastore_client.query(kind = "message")
    query.add_filter("subject", "=", subject)

    querylist = list(query.fetch())
    results = querylist[0]

    bucket = "a1-task1-messageimages"

    return render_template("editmessage.html", entityUsername = entityUsername, bucket = bucket, results = results)

# updates the chosen message to be edited
@app.route('/updatemessage/<string:entityUsername>', methods = ['post'])
def updatemessage(entityUsername):
    subject = request.form.get('subject')
    newsubject = request.form.get('newsubject')
    message = request.form.get('messagetext')
    image = request.files['file']

    # Get entity from datastore
    query = datastore_client.query(kind = "message")
    query.add_filter("subject", "=", subject)
    
    querylist = list(query.fetch())
    results = querylist[0]

    entity_id = results.key.id

    with datastore_client.transaction():
        key = datastore_client.key("message", entity_id)
        task = datastore_client.get(key)

        task["subject"] = newsubject
        task["messagetext"] = message
        task["datetime"] = datetime.datetime.now()

        datastore_client.put(task)

    # if there is an image uploaded, otherwise ignore
    if image:
        ## Adding new image
        blobname = results["imagename"]

        # Delete old picture
        storage_client = storage.Client("myassignment1-task1")
        bucket = storage_client.bucket("a1-task1-messageimages")
        blob = bucket.blob(blobname)
        blob.delete()

        # get image index
        imageIndex = results["imageindex"] 

        # change image index
        imageIndex = imageIndex + 1

        # change imagename based on image index
        new_blobname = str(entity_id) + "_" + str(imageIndex) + "_image.png"

        # add updated imageindex and imagename to datastore
        with datastore_client.transaction():
            key = datastore_client.key("message", entity_id)
            task = datastore_client.get(key)

            task["imageindex"] = imageIndex
            task["imagename"] = new_blobname

            datastore_client.put(task)


        # add new image based on image index as image name
        filename = secure_filename(image.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image.save(filepath)

        storage_client = storage.Client("myassignment1-task1")
        bucket = storage_client.bucket("a1-task1-messageimages")
        blob = bucket.blob(new_blobname)
        blob.upload_from_filename(filepath)
        blob.make_public()

    return redirect(url_for('messagepage', entityUsername = entityUsername))

if __name__ == "__main__":
    # For local testing
    app.run(host = "127.0.0.1", port = 8080, debug = True)