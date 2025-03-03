from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel 
from pymilvus import connections, Collection
from openai import AzureOpenAI
import os 

description = """
Api provides access to OpenAI chat completions and RAG interaction with Milvus similarity search
"""

tags_metadata = [
    {"name": "OpenAI", "description": "OpenAI compatible function"},
    {"name": "Milvus", "description": "Function uses Milvus context extraction"},
]

client = AzureOpenAI(
    api_key = os.getenv("AZURE_OPENAI_API_KEY"),  
    api_version = "2024-02-01",
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    )

app = FastAPI(
    title="RAG-Api",
    description=description,
    version="0.1",
    openapi_tags=tags_metadata
)

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Output(BaseModel):
    response: str 

async def generate_embeddings(text, model="text-embedding-3-large"):
    """ Returns embedding from OpenAI for given model """ 
    return client.embeddings.create(input = [text], model=model).data[0].embedding


async def query_vdb(query: str, collection: Collection) -> None:
    """ Query milvus vector database for similarity search for query """
    
    query_embedding = await generate_embeddings(query)
    
    search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
    results = collection.search(
        data=[query_embedding],
        anns_field="vector",
        param=search_params,
        limit=3,
        output_fields=["text", "article", "paragraph"]  
    )

    context = []
    
    for result in results[0]:
        context.append(f"Score: {result.score} Text: {result.entity.get('text')} Article: {result.entity.get('article')} Paragraph: {result.entity.get('paragraph')}\n")
        
    return context

async def get_context(query: str) -> str:
    """ Performs similarity search on MilvusDB and joins top 5 results into one string """
    connections.connect(alias="default", uri="http://milvus.milvus.svc.cluster.local:19530")
    collection = Collection(name="kodekskarny_embedd")
    collection.load()
    context_array = await query_vdb(query, collection)
    context = ' '.join(context_array)
    return context 

@app.post('/v1/rag_chat_completion', tags=['Milvus', 'OpenAI'], response_model=Output, summary='Returns OpenAI chat completion with given context from Milvus DB')
async def rag_chat_completion(prompt: str) -> str:
    context = await get_context(prompt)
    template = f""" 
    Odpowiedz na podane pytanie korzystajac tylko i wylacznie z podanego kontekstu, wybierz z niego najbardziej pasujacy, do odpowiedzi podaj nr artykulu i paragrafu skad czerpales wiedze.
    Kontekst: {context}
    Pytanie: {prompt}
    """
    model = 'gpt-4o-mini'
    completion = client.chat.completions.create(
        model=model,
        messages = [ 
            {
            "role": "assistant",
            "content": "Jestem przyjaznym botem, ktory odpowiada na pytania prawnicze korzystajac z dostarczonego kontekstu",
            },
            {
            "role": "user",
            "content": template,
            },
            
        ],
        temperature=0.3
    )
    content = completion.choices[0].message.content
    return Output(response=content)

if __name__=="__main__":
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
