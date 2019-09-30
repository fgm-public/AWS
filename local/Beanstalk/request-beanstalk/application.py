
# This application handle web form, that offers vacancies analysis report request.
# Under the hood, it requests AWS S3 Object Storage for xslx report file,
# and returns hyperlink to it, if finds. Else, adds apropriate task to queue.
# This is LOCAL version, intended fot testing purposes only!

# Import required modules
# Flask python web framework itself:
from flask import Flask, render_template, flash, request, Markup
# Html forms handlers:
from wtforms import Form, TextField, TextAreaField, validators, StringField, SubmitField
# Our beloved requests :) :
import requests
# MongoDB driver:
import pymongo
# And finally, our credentials:
from credentials import mongo

# Initialize Flask web application itself
app = Flask(__name__)
app.config.from_object(__name__)

# Define html form handler fields
class ReusableForm(Form):
    occupation = TextField('Occupation:', validators=[validators.required()])
    email = TextField('Your e-mail:') , validators=[validators.required()])

def get_href_from_mongo(occupation, email):
        client = pymongo.MongoClient(mongo).hh_reports
        collection = client['xlsx'] 
        report = collection.find_one({'occupation': occupation})
        if report:
            return report.get('report')
        else:
            collection = client['orders']
            client.insert({'customer': email, 'occupation': occupation})
            return None

def add_message_to_queue(queue, occupation, email):
    pass

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
            report_url = get_href_from_mongo(occupation, email)
            if report_url:
                response = (f'Your report is ready! '
                            f'<a href="{report_url}" class="alert-link">Click here</a> '
                            f'to download it!'
                            )
                flash(Markup(response))
            else:
                flash('Your request has been added to the processing queue. '
                      'You will be notified by e-mail, when the report is ready.'
                    )
                add_message_to_queue(queue, occupation, email)
        else:
            flash('Error: Please, enter occupation name and email into text fields')
    return render_template('request.html', form=form)

if __name__ == "__main__":
    app.run()
