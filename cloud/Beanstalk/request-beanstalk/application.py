
###############################################################################

# This application handle web forms, that offers list of analysis reports,
# vacancies analysis report request and resume analysis report request.
# Under the hood, it requests AWS S3 Object Storage for xslx report files,
# and returns all hyperlinks to it, which was find.
# If an order is received from the user, puts order to MonngoDB
# and puts message to appropriate SQS queue, then wake up harvest-lambda.

###############################################################################
#######   This is CLOUD version, intended for production deployment.   ########
###############################################################################

# Import required modules
# Flask python web framework itself:
from flask import Flask, render_template, flash, request, Markup
# Html form handlers:
from wtforms import Form, TextField, TextAreaField, validators, StringField, SubmitField
# Some stuff to serialize objects:
from json import dumps
# MongoDB driver:
from pymongo import MongoClient
# Our beloved requests :) :
import requests
# It's just for debugging purposes:
import os
# Our send mail class:
from mailsender import MailSender
# And finally, our credentials:
from credentials import mongo, sqs, outgoing_vqueue, outgoing_rqueue, SECRET_KEY,  mail_creds

# Initialize Flask web application instance itself
application = Flask(__name__)
# Load application configuration from here (this file)
application.config.from_object(__name__)
# Just little thing which provided for security reasons
# It's Flask strict requirement
application.config['SECRET_KEY'] = SECRET_KEY
# Only enable Flask debugging if an env var is set to true
application.debug = os.environ.get('FLASK_DEBUG') in ['true', 'True']
# Get application version from env
app_version = os.environ.get('APP_VERSION')
# Get cool new feature flag from env (AWS specific feature)
enable_cool_new_feature = os.environ.get('ENABLE_COOL_NEW_FEATURE') in ['true', 'True']

# Define vacancy order html form
class VacancyOrderForm(Form):
    # Occupation field with any text availability check
    occupation = TextField('Occupation:', validators=[validators.required()])
    # E-mail field with any text availability check
    email = TextField('Your e-mail:', validators=[validators.required()])

# Define resume order html form
class ResumeOrderForm(Form):
    # Search Criteria field with any text availability check
    scriteria = TextField('Criteria:', validators=[validators.required()])
    # E-mail field with any text availability check
    email = TextField('Your e-mail:', validators=[validators.required()])

# Success messages on order
message = ( 'Ваш запрос был успешно добавлен в очередь на обработку! '
            'Когда сбор данных и генерация отчёта будут завершены, '
            'вы получите уведомление на указанный вами адрес.' )
thanks = 'Спасибо за пользование сервисом!'
# Form validation error message on order
error = 'Пожалуйста, заполните все имеющиеся поля формы.'

# This function forms and sends e-mail message
def send_email_to_customer(order):
    # Message subject
    subject = 'Laboranalysis application gets the new order'
    # To admin, with above subject and 'order' body
    mail = MailSender( [mail_creds['admin']], 
                        subject, 
                        str(order) )
    mail.send_email()

# This function tries to get a hyperlinks to the xlsx report files from MongoDB
def get_hrefs_from_mongo(report_type):
    # Instantiate MongoDB connection context
    with MongoClient(mongo) as mongodb:
        # Connection to 'xlsx' collection of 'hh_reports' database
        collection = mongodb.hh_reports['xlsx']
        # Attempt to find all reports
        raw_reports = collection.find({})
        reports = [report for report in raw_reports]
        # Separate reports by its types
        response = {item[report_type]:item['report']
            for item in reports
                if report_type in item.keys()}
        if response:
            # Return hyperlinks
            return response

# This function adds a request or parse order to MongoDB.
def add_order_to_mongo(email, occupation=None, criteria=None):
    # Instantiate MongoDB connection context
    with MongoClient(mongo) as mongodb:
        # Connection to 'orders' collection of 'hh_reports' database
        collection = mongodb.hh_reports['orders']
        # Put request order
        if occupation:
            # If vacancy request
            order = {'customer': email, 'occupation': occupation}
            # Add order to MongoDB
            collection.insert(order)
            # Send mail notification
            send_email_to_customer(order)
        else:
            # If resume request
            order = {'customer': email, 'criteria': criteria}
            # Add order to MongoDB
            collection.insert(order)
            # Send mail notification
            send_email_to_customer(order)

# This function queues a message to wake up the next lambda.
def add_message_to_queue(queue):
    # Create message (dict object)
    raw_message = {"Wake": 'Up'}
    # Serialize message object, because queue requires string messages
    message = dumps(raw_message)
    # Put it to queue
    sqs.send_message(
            QueueUrl=queue,
            MessageBody=message)

# URL binding
@application.route("/", methods=['GET', 'POST'])
# Default handler function which will start when our root web app Url will be visited
def _index():
    # Trying to get report Urls
    vacancy_reports = get_hrefs_from_mongo('occupation')
    resume_reports = get_hrefs_from_mongo('scriteria')
    # Form lists of URLs
    vreports = [Markup(f'<a href="{value}" class="links">{key}</a> <br>')
        for key, value in vacancy_reports.items()]
    rreports = [Markup(f'<a href="{value}" class="links">{key}</a> <br>')
        for key, value in resume_reports.items()]
    # Render index html page template with our report URLs data
    return render_template('index.html',
                            vreports=vreports,
                            rreports=rreports)

# URL binding
@application.route("/vacancy", methods=['GET', 'POST'])
# Function which handles vacancy order page
def _vacancy_request():
    # Define form handler
    form = VacancyOrderForm(request.form)
    # Request form data filled by user
    if request.method == 'POST':
        occupation = request.form['occupation']
        email = request.form['email']
        # Validation check 
        if form.validate():
            # Reassure user
            flash(message)
            flash(thanks)
            # Put request order to mongo
            add_order_to_mongo(email, occupation=occupation)
            add_message_to_queue(outgoing_vqueue)
        else:
            # Asking to fill in all fields
            flash(error)
    # Render vacancy order html page template with our order form
    return render_template('vrequest.html', form=form)

# URL binding
@application.route("/resume", methods=['GET', 'POST'])
# Function which handles resume order page
def _resume_request():
    # Define form handler
    form = ResumeOrderForm(request.form)
    # Request html form data filled by user
    if request.method == 'POST':
        criteria = request.form['scriteria']
        email = request.form['email']
        # Validation check 
        if form.validate():
            # Reassure user
            flash(message)
            flash(thanks)
            # Put parse order to mongo
            add_order_to_mongo(email, criteria=criteria)
            add_message_to_queue(outgoing_rqueue)
        else:
            # Asking to fill in all fields
            flash(error)
    # Render resume order html page template with our order form
    return render_template('rrequest.html', form=form)


# Checks importing issue
if __name__ == '__main__':
    # Run application in debug mode
    application.debug = True
    # Set application worldwide availability
    application.run(host='0.0.0.0')
