
# This function sends a freshly generated report hyperlink to customer.
# This is LOCAL version, intended fot testing purposes only!

# MongoDB driver:
from pymongo import MongoClient
# Mail sender:
from smtplib import SMTP_SSL
# Some stuff to deserialize objects:v
from json import loads
# And finally, our credentials:
from credentials import email, password, smtp_server, sqs, queue, mongo

# This function returns a hyperlink to the xlsx report file
# from MongoDB for the provided occupation.
def get_href_from_mongo(occupation):
    # Connection to 'hh_reports' database object
    client = MongoClient(mongo).hh_reports
    # Connection to 'xlsx' collection object
    collection = client['xlsx']
    # Find report
    report = collection.find_one({'occupation': occupation})
    return report.get('report')

# This function gets a message from the queue, which was sent by the beanstalk web app.
# The Message contains occupation name and email address.
def get_email_from_queue():
    # Receive a message from queue
    raw_message = sqs.receive_message(QueueUrl=queue)
    # Deserialize it
    payload = loads(raw_message.get('Messages')[0].get('Body'))
    # Return email and occupation name
    return (payload.get('customer'), payload.get('occupation'))

# This function deletes a message from the queue,
# which was sent by the beanstalk web app and which was
# successfully processed by all previous lambda functions.
def delete_message():
    # Receive message and provide 'VisibilityTimeout' to queue
    raw_message = sqs.receive_message(QueueUrl=queue, VisibilityTimeout=60)
    # Receive 'ReceiptHandle' from message
    receipt_handle = raw_message['Messages'][0]['ReceiptHandle']
    # And finally deletes the message
    sqs.delete_message(QueueUrl=queue, ReceiptHandle=receipt_handle)

# Define function which will form and send e-mail mesage
def send_email():
    subject = 'The vacancies analysis report you ordered'
    # Retrieve occupation name and email address
    dest_email, occupation = get_email_from_queue()
    # Retrieve a hyperlink to the xlsx report file
    email_text = get_href_from_mongo(occupation)
    # Form a message
    raw_message = f'From: {email}\nTo: {dest_email}\nSubject: {subject}\n\n{email_text}'
    message = raw_message.encode('utf-8')
    # Create mail sender object
    server = SMTP_SSL(smtp_server)
    # Enable debug output
    server.set_debuglevel(1)
    # Some authentication and authorizations
    server.ehlo(email)
    server.login(email, password) #stopped!!!
    server.auth_plain()
    # Send email
    server.sendmail(email, dest_email, message)
    # Destroy mail sender object
    server.quit()


def main():
    send_email()
    delete_message()
