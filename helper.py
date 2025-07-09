import numpy as np
from StateGraph import State
from jinja2 import Template
from langchain_huggingface.embeddings import HuggingFaceEmbeddings
from langchain_chroma import Chroma

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

vectorstore = Chroma(
    collection_name = "newsletter", 
    embedding_function = embeddings, 
    persist_directory="./chroma_db"
)

def make_newsletter_page(state: State):
    html_template = open("email_template.html").read()
    template = Template(html_template)

    rendered_html = template.render(
        subject = "Weekly Newsletter",
        title = "Weekly Newsletter",
        sections = make_sections(state)
    )

    return rendered_html

def make_sections(state: State):
    sections = []

    for i in range(len(state["titles"])):
        sections.append(
            {
                "title": state["titles"][i],
                "content": state["summaries"][i],
                "link": state["links"][i]
            }
        )
    
    return sections

def embed(titles):
    vectors = embeddings.embed_documents(titles)

    return vectors

def cosine_similarity(a, b):
    a = np.array(a)
    b = np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))