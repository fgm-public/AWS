
# This function collects vacancies from the provider (hh.ru),
# and saves them to the database (MongoDB).
# This is LOCAL version, intended fot testing purposes only!

import time
import pymongo
import requests
from tqdm import tqdm
from credentials import mongo

def get_message_from_queue(queue):
    pass

def vacancy_retriever(occupation):
    api_url = 'https://api.hh.ru/vacancies'
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
    delay = 5
    while current_page < pages_count:
        search_parameters['page'] = current_page
        raw_response = requests.get(api_url, params = search_parameters)
        response = raw_response.json()
        brief_vacancies += response.get('items')
        pages_count = response.get('pages')
        current_page += 1
    # Collecting urls which link to full vacancy descriptions
    urls = [vacancy.get('url')
        for vacancy in brief_vacancies]
    for url in tqdm(urls):
        vacancies.append(requests.get(url).json())
        time.sleep(int(delay))
    return vacancies

occupation = get_message_from_queue(queue)
# Open hh_vacancies database
client = pymongo.MongoClient(mongo).hh_vacancies
vacancies = vacancy_retriever(occupation)
# Open proper collection
collection = client[occupation]
# Write data into collection
collection.insert_many(vacancies)
