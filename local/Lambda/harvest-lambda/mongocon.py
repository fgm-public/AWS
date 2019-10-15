
from pymongo import MongoClient
from credentials import mongo

class MongoConnection(object):
    """MongoDB Connection"""
    
    def __init__(self):
        self.connection = None
    
    def __enter__(self):
        self.connection = MongoClient(mongo)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.connection.close()
