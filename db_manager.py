import psycopg2
from psycopg2.extras import execute_values

class DatabaseManager:
    def __init__(self, db_config):
        self.config = db_config
        self.conn = None

    def _get_connection(self):
        if self.conn is None or self.conn.closed:
            self.conn = psycopg2.connect(**self.config)
        return self.conn

    def register_document(self, file_name, minio_path):

        query = """
            INSERT INTO documents (file_name, minio_path) 
            VALUES (%s, %s) 
            RETURNING id;
        """
        conn = self._get_connection()
        with conn.cursor() as cur:
            cur.execute(query, (file_name, minio_path))
            doc_id = cur.fetchone()[0]
            conn.commit()
            return doc_id

    def save_search_results(self, doc_id, results_dict):
        
        query = "INSERT INTO phrase_matches (document_id, phrase, is_found) VALUES %s;"
        data = [(doc_id, phrase, is_found) for phrase, is_found in results_dict.items()]
        
        conn = self._get_connection()
        with conn.cursor() as cur:
            execute_values(cur, query, data)
            conn.commit()

    def close(self):
        if self.conn:
            self.conn.close()