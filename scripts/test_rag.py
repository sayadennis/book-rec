import numpy as np
import pandas as pd
import torch
from sentence_transformers import SentenceTransformer, util
from transformers import AutoModelForSeq2SeqLM  # type: ignore[import]
from transformers import AutoTokenizer  # type: ignore[import]

DEVICE = "cuda:0" if torch.cuda.is_available() else "cpu"

## Load models ##

RETRIEVER_ID = "sentence-transformers/all-MiniLM-L6-v2"
GENERATOR_ID = "lmqg/flan-t5-base-squad-qag"

# might be better to use popular question answering models?
# "distilbert/distilbert-base-cased-distilled-squad"
# "distilbert/distilbert-base-cased"
# "deepset/tinybert-6l-768d-squad2"
# "deepset/roberta-base-squad2"

retriever = SentenceTransformer(
    RETRIEVER_ID, device=DEVICE, cache_folder="/projects/b1042/lyglab/saya"
)
generator_tokenizer = AutoTokenizer.from_pretrained(
    GENERATOR_ID, cache_dir="/projects/b1042/lyglab/saya"
)
generator_model = AutoModelForSeq2SeqLM.from_pretrained(
    GENERATOR_ID, cache_dir="/projects/b1042/lyglab/saya"
).to(DEVICE)

## Load data ##

# Sample data: NYT bestsellers dataset (title, description)
sandbox_corpus = [
    (
        "The Martian is a sci-fi novel by Andy Weir, published in 2011, "
        "about an astronaut stranded on Mars, using science to survive."
    ),
    (
        "Les Misérables is a historical fiction set during the French Revolution. "
        "It has been turned into a play and a movie."
    ),
    (
        "Demon Copperhead by Barbara Kingslover is a modern coming-of-age story "
        "in the Appalachian Mountains. It is highly popular and "
        "has been on the NYT best sellers list for over 30 weeks."
    ),
]

# Subset of real dataset
bestsellers = pd.read_csv(
    "/projects/p30791/book-rec/data/raw/bestsellers-2014-01-01-to-2014-01-31.csv",
    index_col=0,
)
bestsellers_corpus = [
    (
        f'{x.category} book "{x.title}" (ISBN {x.primary_isbn13}) is written by '
        f"{x.author} published by {x.publisher} on {x.publication_date}. The highest "
        f"rank it achieved on the bestseller list is {x.best_rank} and it stayed on "
        f"the bestseller list for {x.max_weeks_on_list} weeks. NYT Description: "
        f"{x.description} // Google Books Description: {x.google_description}"
    )
    for _, x in bestsellers.iterrows()
]

## RAG pipeline ##

# Precompute embeddings for the dataset
corpus_embeddings = retriever.encode(bestsellers_corpus, convert_to_tensor=True)


def rag_pipeline(query):
    """
    Simple RAG pipeline that retrieves relevant context and generates an answer.
    """
    # Step 1: Encode the query and find the most similar description
    query_embedding = retriever.encode(query, convert_to_tensor=True)
    scores = util.pytorch_cos_sim(query_embedding, corpus_embeddings)
    best_match_idx = np.argmax(
        scores
    )  # Index of the most relevant row - eventually, return top few
    context = bestsellers_corpus[best_match_idx]
    title = bestsellers.loc[best_match_idx.item(), "title"]
    # Step 2: Generate an answer using Flan-T5
    input_text = f"Context: {context} // Question: {query}"
    inputs = generator_tokenizer(
        input_text, return_tensors="pt", max_length=512, truncation=True
    )
    outputs = generator_model.generate(**inputs, max_length=100)
    answer = generator_tokenizer.decode(outputs[0], skip_special_tokens=True)
    return {"title": title, "answer": answer}


# Example queries
queries = [
    "Can you recommend a popular historical fiction book?",
    "Any books that are popular fantasy?",
    "For how many weeks was The Martian a bestseller?",
    "Can you recommend a historical fiction about the French Revolution?",
    "What are some popular modern coming-of-age stories?",
    "Any books that are long-time new york times bestsellers?",
    "What are some popular modern coming-of-age stories?",
    "Are there any books written by andy weir?",
]

# Process queries
for query in queries:
    result = rag_pipeline(query)
    print(f"Query: {query}")
    print(f"Book Title: {result['title']}")
    print(f"Answer: {result['answer']}")
    print("-" * 50)
