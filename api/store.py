import json
import os
from typing import Dict, List, Union

import faiss
import pandas as pd
from llama_index.core.indices import load_index_from_storage
from llama_index.core.indices.vector_store.base import VectorStoreIndex
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.schema import Document, NodeWithScore
from llama_index.core.service_context import ServiceContext
from llama_index.core.storage.storage_context import StorageContext
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.vector_stores.faiss import FaissVectorStore
from pydantic import BaseModel

from api.retriever import HybridRetriever
from lib.cache import async_threadsafe_ttl_cache as cache

allsides_file = "./data/allsides.com.json"
mbfc_file = "./data/mediabiasfactcheck.com.json"
csv_file = "./data/all.csv"
persist_dir = "./db"


class Media(BaseModel):
    """Media model"""

    Name: str
    Website: str
    Youtube: str
    About: str
    TrustFactors: str
    Topics: str
    Wikipedia: str
    X: str
    Bias: Union[str, None]
    Profile: Union[str, None]
    Factual: Union[str, None]
    Credibility: Union[str, None]


def _merge_facts(df: pd.DataFrame, facts: Dict[str, Dict[str, str]]) -> pd.DataFrame:
    def merge_fact(row: pd.Series) -> pd.Series:
        name = row["Name"].lower()
        if name in facts:
            fact = facts[name]
            row["Bias"] = fact["bias"]
            row["Profile"] = fact["profile"]
            row["Factual"] = fact["factual"]
            row["Credibility"] = fact["credibility"]
        else:
            print(f"Facts not found for {name}")
        return row

    return df.apply(merge_fact, axis=1)


def get_data() -> List[Dict[str, str]]:
    combined = "data/combined.json"
    if os.path.exists(combined):
        with open(combined, encoding="utf-8") as f:
            return json.load(f)
    else:
        # combine the data
        raw = pd.read_csv(csv_file, na_filter=False)
        with open(mbfc_file, encoding="utf-8") as f:
            fact_list = json.load(f)
        facts = {item["name"].lower(): item for item in fact_list}
        df = _merge_facts(raw, facts)
        data = df.where(pd.notnull(df), None).to_dict(orient="records")
        # write json to file:
        with open(combined, "w", encoding="utf-8") as f:
            json.dump(data, f)
        return data


def _get_documents() -> List[Document]:
    """
    Let's create custom documents from json to avoid cruft, to get more reliable scoring during retrieval.
    We keep our own index to later map back to the original json dicts corresponding to the matching documents.
    We are only interested in the following fields, so we just concat them into a single string:
    - Name
    - About
    - Topics
    """
    data = get_data()
    documents = []
    # iterate over the list of data and keep track of the index
    for i, item in enumerate(data):
        # create a document with the index as id
        document = Document(
            metadata={"json_doc_id": i},
            text=item["Name"] + "\n" + item["About"] + "\n" + item["Topics"],
        )
        # add the document to the list
        documents.append(document)
    return documents


def _get_index() -> VectorStoreIndex:
    exists = os.path.exists(persist_dir)
    print("DB exists: " + str(exists))

    d = 3072
    embed_model = OpenAIEmbedding(model_name="text-embedding-3-large", dimensions=d)
    service_context = ServiceContext.from_defaults(embed_model=embed_model)
    index: VectorStoreIndex
    if exists:
        vector_store = FaissVectorStore.from_persist_dir(persist_dir)
        storage_context = StorageContext.from_defaults(
            vector_store=vector_store,
            persist_dir=persist_dir,
        )
        index = load_index_from_storage(
            storage_context=storage_context, service_context=service_context
        )
    else:
        faiss_index = faiss.IndexFlatL2(d)
        vector_store = FaissVectorStore(faiss_index=faiss_index)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        documents = _get_documents()
        index = VectorStoreIndex.from_documents(
            documents, storage_context=storage_context, service_context=service_context
        )
        index.storage_context.persist(persist_dir=persist_dir)
    return index


def _get_retriever(top_k: int) -> HybridRetriever:
    use_top_k = top_k * 2
    index = _get_index()
    bm25_retriever = BM25Retriever.from_defaults(
        index=index, similarity_top_k=use_top_k
    )
    vector_retriever = VectorIndexRetriever(
        index=index,
        similarity_top_k=use_top_k,
    )
    hybrid_retriever = HybridRetriever(vector_retriever, bm25_retriever)
    return hybrid_retriever


# def _get_reranked_nodes(
#     nodes: list[NodeWithScore], query: str, top_k: int
# ) -> list[NodeWithScore]:
#     reranker = SentenceTransformerRerank(top_n=top_k, model="BAAI/bge-reranker-base")
#     reranked_nodes = reranker.postprocess_nodes(
#         nodes,
#         query_bundle=QueryBundle(query),
#     )
#     return reranked_nodes


def _extract_node_data(nodes: list[NodeWithScore]) -> list[Media]:
    """
    We need to map the nodes back to the original json data.
    """
    data = get_data()
    selection = []
    for node in nodes:
        item = data[node.metadata["json_doc_id"]]
        selection.append(item)
    return selection


@cache(ttl=60 * 60 * 24)
async def query_media(query: str, top_k: int = 5) -> list[Media]:
    retriever = _get_retriever(top_k)
    raw_nodes = await retriever.aretrieve(query)
    # reranked_nodes = _get_reranked_nodes(raw_nodes, query, top_k)
    reranked_nodes = raw_nodes[:top_k]
    # sort response by score
    nodes_sorted = sorted(reranked_nodes, key=lambda x: x.score, reverse=True)
    data = _extract_node_data(nodes_sorted)
    # print("Found results:")
    # for item in data:
    #     print("---------")
    #     print("Name: " + item["Name"])
    #     print("About: " + item["About"])
    #     print("Topics: " + item["Topics"])
    #     print("Youtube: " + item["Youtube"])
    return data


def query_allsides(query: str, limit: int = 5, offset: int = 0) -> List[Dict[str, str]]:
    with open(allsides_file, encoding="utf-8") as f:
        fact_list = json.load(f)
    results = []
    for item in fact_list:
        if query.lower() in item["name"].lower():
            results.append(item)
    return results[offset : offset + limit]


def query_mediabiasfactcheck(
    query: str, limit: int = 5, offset: int = 0
) -> List[Dict[str, str]]:
    with open(mbfc_file, encoding="utf-8") as f:
        fact_list = json.load(f)
    results = []
    for item in fact_list:
        if query.lower() in item["name"].lower():
            if item["credibility"] in [
                "medium credibility",
                "high credibility",
            ] or item["factual"] in ["factual", "mostly", "mixed"]:
                results.append(item)
    return results[offset : offset + limit]
