
# This application handle web form, that offers vacancies analysis report request.
# Under the hood, it requests AWS S3 Object Storage for xslx report file,
# and returns hyperlink to it, if finds. Else, adds the appropriate task to the queue.
# This is LOCAL version, intended fot testing purposes only!

# Import required modules
# Flask python web framework itself:
from flask import Flask, render_template, flash, request, Markup
# Html form handlers:
from wtforms import Form, TextField, TextAreaField, validators, StringField, SubmitField
# Some stuff to serialize objects:
from json import dumps
# MongoDB driver:
from pymongo import MongoClient
# Our MongoDB connection class:
from mongocon import MongoConnection
# Our beloved requests :) :
import requests
# And finally, our credentials:
from credentials import mongo, sqs, outgoing_queue, SECRET_KEY

# Initialize Flask web application instance itself
app = Flask(__name__)
# Load application configuration from here (this file)
app.config.from_object(__name__)
# Just little thing which provided for security reasons
# It's Flask strict requirement
app.config['SECRET_KEY'] = SECRET_KEY

# Define html form handler fields
class ReusableForm(Form):
    # Occupation field with any text availability check
    occupation = TextField('Occupation:', validators=[validators.required()])
    # E-mail field with any text availability check
    email = TextField('Your e-mail:', validators=[validators.required()])

# This function tries to get a hyperlink to the xlsx report file from MongoDB
# for the provided occupation. If the report already exists,
# the function returns a hyperlink, otherwise it puts the request order in MongoDB.
def get_href_from_mongo(occupation, email):
    # MongoDB connection object    
    client = MongoConnection()
    # Use our connection object with context manager to handle connection
    with client:
        # Connection to 'xlsx' collection of 'hh_reports' database
        collection = client.connection.hh_reports['xlsx']
        # Attempt to find an existing report
        report = collection.find_one({'occupation': occupation})
        if report:
            # Return hyperlink
            return report.get('report')
        else:
            add_order_to_mongo(client, occupation, email)
            return None

# This function adds a request order to MongoDB.
def add_order_to_mongo(client, occupation, email):
    # MongoDB connection object    
    client = MongoConnection()
    # Use our connection object with context manager to handle connection
    with client:
        # Connection to 'orders' collection of 'hh_reports' database
        collection = client.connection.hh_reports['orders']
        # Put request order
        collection.insert({'customer': email, 'occupation': occupation})

# This function queues a message to wake up the next lambda.
def add_message_to_queue():
    # Create message (dict object)
    raw_message = {"Wake": 'Up'}
    # Serialize message object, because queue requires string messages
    message = dumps(raw_message)
    # Put it to queue
    sqs.send_message(
            QueueUrl=outgoing_queue,
            MessageBody=message)

# Default handler function which will start when our root web app Url will be visited
@app.route("/", methods=['GET', 'POST'])
def _request():
    # Html form handler
    form = ReusableForm(request.form)
    # Request html form data filled by user
    if request.method == 'POST':
        occupation = request.form['occupation']
        email = request.form['email']
        # Validation check 
        if form.validate():
            # Trying to get report Url
            report_url = get_href_from_mongo(occupation, email)
            if report_url:
                # Create response
                response = (f'Your report is ready! '
                            f'<a href="{report_url}" class="alert-link">Click here</a> '
                            f'to download it!')
                # Put it to user
                flash(Markup(response))
            else:
                # Reassure user
                flash('Your request has been added to the processing queue. '
                      'You will be notified by e-mail, when the report is ready.')
                # Put report order to queue
                add_message_to_queue()
        else:
            # Asking to fill in all fields
            flash('Error: Please, enter occupation name and email into text fields')
    return render_template('request.html', form=form)

# Checks importing issue
if __name__ == "__main__":
    # Run application in debug mode
    app.run(debug=True)
