
# This function collects vacancies from the provider (hh.ru),
# and saves them to the database (MongoDB).
# This is LOCAL version, intended fot testing purposes only!

# Import required modules
# Sleep function for requests delay:
from time import sleep
# MongoDB driver:
from pymongo import MongoClient
# Our MongoDB connection class:
from mongocon import MongoConnection
# Our beloved requests:
import requests
# Some stuff to deserialize objects:
from json import loads, dumps
# Preetty progress bar:
from tqdm import tqdm
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
    # MongoDB connection object    
    client = MongoConnection()
    # Use our connection object with context manager to handle connection
    with client:
        # Connection to 'orders' collection of 'hh_reports' database
        collection = client.connection.hh_reports['orders']
        # Get number of last added order
        number = collection.estimated_document_count()-1
        # Get occupation name
        raw_document = collection.find().skip(number)
        occupation = raw_document[0].get('occupation')
        return occupation

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
    for url in tqdm(urls):
        vacancies.append(requests.get(url).json())
    return vacancies

# A FULL version of the request to API function which retirve all vacancies,
# because we need more :)))
# This function collects full vacancies from HH API.
def vacancy_retriever(occupation):
    # HH API entry point Url
    api_url = 'https://api.hh.ru/vacancies'
    # Request to API parameters
    search_parameters = {
                'text': occupation,
                'per_page': 100,
                'page': 0,
                'period': 1
                }
    brief_vacancies = []
    vacancies = []
    current_page = 0
    pages_count = current_page + 1
    pages_count = 1
    # Delay between requests in seconds
    delay = 5
    while current_page < pages_count:
        search_parameters['page'] = current_page
        # Request to API
        raw_response = requests.get(api_url, params = search_parameters)
        # Deserialize resronse
        response = raw_response.json()
        brief_vacancies += response.get('items')
        pages_count = response.get('pages')
        current_page += 1
    # Collecting the urls from the brief vacancies,
    # which links to full vacancy descriptions
    urls = [vacancy.get('url')
        for vacancy in brief_vacancies]
    # Retrieve full vacancy from each url with request delay and progress bar
    for url in tqdm(urls):
        vacancies.append(requests.get(url).json())
        sleep(int(delay))
    return vacancies

if __name__ == "__main__":
    
    # Deletes a 'wake-up' message from the queue
    delete_message_from_queue()
    # Retrieve the occupation name
    ##occupation = get_occupation_from_queue()
    occupation = get_occupation_from_mongo()
    # Open hh_vacancies database
    client = MongoClient(mongo).hh_vacancies
    # Usually, we use a BRIEF version of the function,
    # for time-saving purposes
    vacancies = vacancy_retriever_brief(occupation)
    # Open proper collection
    collection = client[occupation]
    # Write data into collection
    collection.insert_many(vacancies)
    # Sends a 'wake-up' message to the queue for next lambda
    add_message_to_queue()
