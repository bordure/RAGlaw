from typing import List
from langchain_community.document_loaders import PyPDFLoader
from pymilvus import connections, Collection, CollectionSchema, FieldSchema, DataType, utility
from openai import AzureOpenAI
import os
from dotenv import load_dotenv




def load_pdf(files: List[str]) -> List[dict]:
    """ Load given set of pdfs and returns List of dictionaries with pdf content """
    pages = []
    for file in files:
        loader = PyPDFLoader(file)
        for page in loader.lazy_load():
            pages.append(page)
    return pages


def chunk_data(data: List[dict]) -> List[dict]:
    """ This function chunks page content to text, article_number and paragraph_number """
    import re
    chunks = []
    pattern = r'(Art\.\s+\d+.*?)\s*(?=Art\.\s+\d+|$)'
    pattern_for_paragraphs = r'(?=§\s*\d+\.)'
    for page in data:
        try:
            text = page.page_content.replace('\xa0', '').replace('\n', '')
            splitted_per_article = re.findall(pattern, text, re.DOTALL)
            for article in splitted_per_article:
                article_number = article.split('[')[0]
                if '§' in article:
                    splitted_per_paragraph = re.split(pattern_for_paragraphs, article)
                    paragraphs = splitted_per_paragraph[1:] # Remove first element of list with article name
                    for paragraph in paragraphs:
                        paragraph_number = paragraph.split('§')[1].split('.')[0].strip()
                        index_of_paragraph_number = paragraph.index(paragraph_number)
                        text = paragraph[index_of_paragraph_number+1:]
                        chunks.append({'article_number': article_number, 'paragraph_number': paragraph_number, 'text': text})
                else:
                    chunks.append({'article_number': article_number, 'paragraph_number': 0, 'text': article.split(']')[1]})
        except Exception as e:
            print(e)
            pass
            
    return chunks 

def create_milvus_collection(host: str = 'localhost', port: str = '19530', collection_name: str = 'kodekskarny_embedd') -> Collection:
    """ This function connect to Milvus DB and create collection, if collection already exists it connects to it """
    connections.connect(alias="default", uri=f"http://{host}:{port}")
    
    if collection_name in utility.list_collections():
        collection = Collection(name=collection_name)
        utility.drop_collection(collection_name)

    pk_field = FieldSchema(name="pk", dtype=DataType.INT64, is_primary=True, auto_id=True)
    vector_field = FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=3072) 
    text_field = FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=4096)
    article_field = FieldSchema(name="article", dtype=DataType.VARCHAR, max_length=512)
    paragraph_field = FieldSchema(name="paragraph", dtype=DataType.VARCHAR, max_length=512)
    
    schema = CollectionSchema(fields=[pk_field, vector_field, text_field, article_field, paragraph_field], description="Collection for document embeddings")
    
    collection = Collection(name=collection_name, schema=schema)
    

    index_params = {"metric_type": "L2", "index_type": "IVF_FLAT", "params": {"nlist": 128}}
    collection.create_index(field_name="vector", index_params=index_params)

    collection.load()
    
    print(f"Collection '{collection_name}' is ready for insertion!")
    return collection

def generate_embeddings(text, model="text-embedding-3-large"): 
    load_dotenv()
    client = AzureOpenAI(
        api_key = os.getenv("AZURE_OPENAI_API_KEY"),  
        api_version = "2024-02-01",
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    )
    return client.embeddings.create(input = [text], model=model).data[0].embedding

def insert_chunks_to_milvus(chunks: List[dict], collection: Collection) -> None:
    """Embeds and inserts chunked data into Milvus."""
    results = collection.query(expr="", output_fields=["count(*)"])
    number_of_rows = int(results[0]['count(*)'])
    if number_of_rows > 0:
        print("Chunks already ingested")
        return
        
    texts = [chunk["text"] for chunk in chunks]
    articles = [str(chunk["article_number"]) for chunk in chunks]
    paragraphs = [str(chunk["paragraph_number"]) for chunk in chunks]
    
    embeddings_list = []
    for chunk in chunks:
        if chunk['text'].strip():
            embeddings_list.append(generate_embeddings(chunk['text'].strip()))
    
    entities = [
        {"vector": embedding, "text": text, "article": article, "paragraph": paragraph}
        for embedding, text, article, paragraph in zip(embeddings_list, texts, articles, paragraphs)
    ]

    if entities:
        collection.insert(entities)
        print(f"Inserted {len(entities)} records to db'.")
    else:
        print("No records to insert.")



def main():
    files = ['workflows/data/kodekskarny2.pdf']
    ingested_data = load_pdf(files)
    chunks = chunk_data(ingested_data)
    collection = create_milvus_collection(port='19530', host='milvus.milvus.svc.cluster.local')
    insert_chunks_to_milvus(chunks, collection)

if __name__ == "__main__":
    main()