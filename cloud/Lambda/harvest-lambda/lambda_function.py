
###############################################################################
##########################   Ethical disclaimer   #############################
###############################################################################

# In this application, we work with the portal and API of the headhunter.ru company.
# We are very grateful to headhunter.ru company for the beautiful portal 
# and excellently-designed well-documented API, programming with which was a pure pleasure.
# We are aware of the complexity of the development and maintenance of such services 
# and such a business as a whole. We are also fully aware that specialized databases 
# are one of the main assets of the company.
#
# In connection with the foregoing, we should in no case forget that:
#
#      THIS APPLICATION WAS CREATED EXCLUSIVELY FOR EDUCATIONAL PURPOSES
#      AND COMPLETELY EXCLUDES THE POSSIBILITY OF ANY BUSINESS USE.
#
# Also remember that the company itself provides analytical reporting services 
# that you can always use and this will be the best choice.

###############################################################################

# This function collects vacancies from the provider (hh.ru),
# and stores them to the database (MongoDB).

###############################################################################
#######   This is CLOUD version, intended for production deployment.   ########
###############################################################################

# Some stuff to deserialize objects:
from json import loads, dumps
# Our beloved requests:
import requests
# MongoDB driver:
from pymongo import MongoClient
# And finally, our credentials:
from credentials import mongo, sqs, incoming_queue, outgoing_queue

# This function deletes a message from the queue,
# which was sent by the beanstalk app.
def delete_message_from_queue():
    # Receive message and provide 'VisibilityTimeout' to queue
    raw_message = sqs.receive_message(QueueUrl=incoming_queue,
                                      VisibilityTimeout=60)
    # Receive 'ReceiptHandle' from message
    receipt_handle = raw_message['Messages'][0]['ReceiptHandle']
    # And finally deletes the message
    sqs.delete_message(QueueUrl=incoming_queue,
                       ReceiptHandle=receipt_handle)

# This function queues a message to wake up the next lambda.
def add_message_to_queue():
    # Create message (dict object)
    raw_message = {"Wake": 'Up'}
    # Serialize message object, because queue requires string messages
    message = dumps(raw_message)
    # Put it to queue
    sqs.send_message(
            QueueUrl=outgoing_queue,
            MessageBody=message,)

# This function gets an occupation name from MongoDB to request it from HH API.
def get_occupation_from_mongo():
    # Instantiate MongoDB connection context
    with MongoClient(mongo) as mongodb:
        # Connection to 'orders' collection of 'hh_reports' database
        collection = mongodb.hh_reports['orders']
        # Get number of last added order
        number = collection.estimated_document_count()-1
        # Get occupation name
        raw_document = collection.find().skip(number)
        occupation = raw_document[0].get('occupation')
        return occupation

# This function stores retrieved vacancies to MongoDB
def store_vacancies_to_mongo(occupation, vacancies):
    # Instantiate MongoDB connection context
    with MongoClient(mongo) as mongodb:
        # Open proper collection in hh_vacancies database
        collection = mongodb.hh_vacancies[occupation]
        # Write data into collection
        insert_result = collection.insert_many(vacancies)
        # Return insertion result
        return insert_result

# A BRIEF version of the request to API function which retrieve small batch,
# because of requests limitations.
# This function collects full vacancies from HH API.
def vacancy_retriever_brief(occupation):
    # HH API entry point Url
    api_url = 'https://api.hh.ru/vacancies'
    # Request to API parameters
    search_parameters = {
                'text': occupation,
                'per_page': 10,
                'page': 0,
                'period': 1
            }
    brief_vacancies = []
    vacancies = []
    # Request to API
    raw_response = requests.get(api_url, params = search_parameters)
    # Deserialize resronse
    response = raw_response.json()
    brief_vacancies += response.get('items')
    # Collecting the urls from the brief vacancies,
    # which links to full vacancy descriptions
    urls = [vacancy.get('url')
        for vacancy in brief_vacancies]
    # Retrieve full vacancy from each url
    for url in urls:
        vacancies.append(requests.get(url).json())
    return vacancies


# Main lamba function
def lambda_handler(event, context):
    # Retrieve the occupation name
##occupation = get_occupation_from_queue()
    occupation = get_occupation_from_mongo()
    # Usually, we use a BRIEF version of the function,
    # for time-saving purposes
    vacancies = vacancy_retriever_brief(occupation)
    # Store retrieved vacancies to MongoDB
    insert_result = store_vacancies_to_mongo(occupation, vacancies)
    # Deletes a 'wake-up' message from the queue
    delete_message_from_queue()
    # Sends a 'wake-up' message to the queue for next lambda
    add_message_to_queue()

    return {
        'statusCode': 200,
        'body': dumps(insert_result)
    }