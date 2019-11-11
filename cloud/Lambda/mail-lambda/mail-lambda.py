
###############################################################################

# This function sends a freshly generated report hyperlink to customer.

###############################################################################
#######   This is CLOUD version, intended for production deployment.   ########
###############################################################################

# MongoDB driver:
from pymongo import MongoClient
# Our send mail class:
from mailsender import MailSender
# Some stuff to deserialize objects:
from json import loads
# And finally, our credentials:
from credentials import mail_creds, sqs, incoming_queue, mongo

# This function returns a hyperlink, retrieved from MongoDB,
# to the xlsx report file, which stores in AWS S3 object storage,
# for the provided occupation.
def get_href_from_mongo(occupation):
    # Instantiate MongoDB connection context
    with MongoClient(mongo) as mongodb:    
        # Connection to 'xlsx' collection of 'hh_reports' database
        collection = mongodb.hh_reports['xlsx']
        # Attempt to find an existing report
        report = collection.find_one({'occupation': occupation})
        return report.get('report')

# This function gets an occupation name and email address from MongoDB.
def get_email_from_mongo():
    # Instantiate MongoDB connection context
    with MongoClient(mongo) as mongodb:    
        # Connection to 'orders' collection of 'hh_reports' database
        collection = mongodb.hh_reports['orders']
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
def send_email_to_customer():
    # Message subject
    success = 'Ваш отчёт готов!'
    # Retrieve occupation name and email address
    order_customer, occupation = get_email_from_mongo()
    # Retrieve a hyperlink to the xlsx report file
    message = get_href_from_mongo(occupation)
    mail = MailSender( [mail_creds['admin'], order_customer],
                        success, 
                        message )
    mail.send_email()


# Main lamba function
def lambda_handler(event, context):

    send_email_to_customer()
    delete_message_from_queue()
    
    return {
        'statusCode': 200,
    }
