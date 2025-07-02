import os
from dotenv import load_dotenv
from datetime import timedelta
from couchbase.auth import PasswordAuthenticator
from couchbase.cluster import Cluster
from couchbase.options import ClusterOptions

class DataManager:

    def __init__(self, endpoint=None, username=None, password=None, 
                 bucket_name=None, scope_name=None, collection_name=None):

        load_dotenv()
        
        self.endpoint = endpoint or os.getenv("ENDPOINT")
        self.username = username or os.getenv("USERNAME")
        self.password = password or os.getenv("PASSWORD")
        self.bucket_name = bucket_name or os.getenv("BUCKET_NAME")
        self.scope_name = scope_name or os.getenv("SCOPE_NAME")
        self.collection_name = collection_name or os.getenv("COLLECTION_NAME")

        auth = PasswordAuthenticator(self.username, self.password)
        options = ClusterOptions(auth)
        
        self.cluster = Cluster(self.endpoint, options)
        self.cluster.wait_until_ready(timedelta(seconds=5))
        
        self.bucket = self.cluster.bucket(self.bucket_name)
        self.collection = self.bucket.scope(self.scope_name).collection(self.collection_name)

    def insert(self, key, document):
        if not self.collection.exists(key).exists:
            return self.collection.insert(key, document)
    
    def read(self, key):
        return self.collection.get(key)
    
    def read_all(self):
        query = f"""
            SELECT RAW doc 
            FROM `{self.bucket_name}`.`{self.scope_name}`.`{self.collection_name}` AS doc """
        
        result = self.cluster.query(query)
        documents = []
        for row in result:
            documents.append(row)
        return documents
    
    def update(self, key, document):
        return self.collection.replace(key, document)
    
    def delete(self, key):
        return self.collection.remove(key)
    
    def delete_all(self):
        query = f"SELECT META().id FROM `{self.bucket_name}`.`{self.scope_name}`.`{self.collection_name}`"
        result = self.cluster.query(query)
        for row in result:
            self.collection.remove(row['id'])    
