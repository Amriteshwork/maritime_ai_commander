import os
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.tools import tool
from langchain_core.documents import Document
from config import FAISS_INDEX_PATH, logger

embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

def build_initial_index():
    """Builds a sample FAISS index with dummy regulatory data if it doesn't exist."""
    logger.info("Building initial FAISS index for RAG...")
    sample_docs = [
        Document(page_content="ITU-R M.1371 Regulation: Vessels experiencing sudden speed anomalies exceeding 40 knots should be flagged for potential GPS spoofing.", metadata={"source": "ITU-R"}),
        Document(page_content="USCG AIS Guide: Cargo vessels have a typical maximum speed of 25 knots. Speeds above this indicate data corruption or physical teleportation anomalies.", metadata={"source": "USCG"}),
        Document(page_content="Historical Incident Report 2024: The MSC Flaminia experienced AIS spoofing where course over ground deviated from heading by more than 45 degrees.", metadata={"source": "Incident History"})
    ]
    vectorstore = FAISS.from_documents(sample_docs, embeddings)
    vectorstore.save_local(FAISS_INDEX_PATH)
    logger.info("FAISS index built and saved.")

@tool
def maritime_regulatory_retriever(query: str) -> str:
    """Use this tool to search maritime regulations, AIS guidelines, and historical incident data to assess risk and validate anomalies."""
    if not os.path.exists(FAISS_INDEX_PATH):
        build_initial_index()
        
    vectorstore = FAISS.load_local(FAISS_INDEX_PATH, embeddings, allow_dangerous_deserialization=True)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 2})
    docs = retriever.invoke(query)
    return "\n\n".join([f"Source: {doc.metadata.get('source', 'Unknown')}\n{doc.page_content}" for doc in docs])