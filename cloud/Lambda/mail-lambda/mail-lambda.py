
# This function sends a freshly generated report hyperlink to customer.
# This is CLOUD version, intended fot testing purposes only!

# MongoDB driver:
from pymongo import MongoClient
# Mail sender:
from smtplib import SMTP_SSL
# Some stuff to deserialize objects:v
from json import loads
# And finally, our credentials:
from credentials import email, password, smtp_server, sqs, incoming_queue, mongo

# This function returns a hyperlink, retrieved from MongoDB,
# to the xlsx report file, which stores in AWS S3 object storage,
# for the provided occupation.
def get_href_from_mongo(occupation):
    # Connection to 'hh_reports' database object
    client = MongoClient(mongo).hh_reports
    # Connection to 'xlsx' collection object
    collection = client['xlsx']
    # Finds a suitable report
    report = collection.find_one({'occupation': occupation})
    return report.get('report')

# This function gets an occupation name and email address from MongoDB.
def get_email_from_mongo():
    # Connection to 'hh_reports' database object
    client = MongoClient(mongo).hh_reports
    # Connection to 'orders' collection object
    collection = client['orders']
    # Gets serial number of last added order
    number = collection.estimated_document_count()-1
    # Get e-mail
    raw_document = collection.find().skip(number)
    email = raw_document[0].get('customer')
    occupation = raw_document[0].get('occupation')
    return email, occupation

# This function deletes a message from the queue,
# which was sent by the previous lambda function.
def delete_message_from_queue():
    # Receive message and provide 'VisibilityTimeout' to queue
    raw_message = sqs.receive_message(QueueUrl=incoming_queue,
                                      VisibilityTimeout=60)

    # Receive 'ReceiptHandle' from message
    receipt_handle = raw_message['Messages'][0]['ReceiptHandle']
    # And finally deletes the message
    sqs.delete_message(QueueUrl=incoming_queue,
                       ReceiptHandle=receipt_handle)

# This function forms and sends e-mail message
def send_email():
    subject = 'The vacancies analysis report you ordered'
    # Retrieve occupation name and email address
    dest_email, occupation = get_email_from_mongo()
    # Retrieve a hyperlink to the xlsx report file
    email_text = get_href_from_mongo(occupation)
    # Form a message
    raw_message = (f'From: {email}\n'
                   f'To: {dest_email}\n'
                   f'Subject: {subject}\n\n'
                   f'{email_text}')

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


# Main lamba function
def lambda_handler(event, context):

    send_email()
    delete_message_from_queue()
    
    return {
        'statusCode': 200,
    }
