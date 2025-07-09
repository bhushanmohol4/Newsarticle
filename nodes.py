import os
import requests
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from helper import *
from StateGraph import State
from datetime import date

load_dotenv()

llm = ChatGroq(model = "llama-3.3-70b-versatile", api_key=os.getenv("groq_api"))

# 1. Fetch news articles
def extract(state: State) -> State:
    try:
        apikey = os.getenv("mediastack_api")
        categories = ["sports"]
        categories_str = ",".join(categories)
        interests = ["football", "cricket", "Artificial Intelligence", "LLM", "Singapore", "basketball", "India"]
        country = "in"
        language = "en"
        day = date.today()
        limit_articles = state["num_articles"] if state["offset"] == 0 else state["offset"]
        offset = state["total_fetched"]
        url = f"http://api.mediastack.com/v1/news?access_key={apikey}&categories={categories_str}&languages={language}&date={day}&sort=popularity&limit={limit_articles}&offset={offset}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            for article in data["data"]:
                state["titles"].extend([article["title"]])
                state["raw_articles"].extend([article["description"]])
                state["links"].extend([article["url"]])
            # Update total_fetched
            state["total_fetched"] += len(data["data"])
        else:
            print("request response error: ", response.json()["error"])
    except Exception as e:
        print("Error", e)
    
    return state

# 2. Check and remove any duplicate articles
def deduplicate(state: State) -> State:
    vectors = embed(state["titles"])
    duplicate_index = set()
    
    for i in range(len(vectors)):
        for j in range(i + 1, len(vectors)):
            sim = cosine_similarity(vectors[i], vectors[j])
            if(sim > 0.8):
                duplicate_index.add(i)
    
    for i in range(len(state["titles"])):
        similar_docs = vectorstore.search(state["titles"][i], search_type = "similarity")
        if(len(similar_docs)>0):
            duplicate_index.add(i)

    for index in sorted(duplicate_index, reverse=True):
        state["raw_articles"].pop(index)
        state["titles"].pop(index)
        state["links"].pop(index)

    # Calculate how many more articles are needed
    needed = state["num_articles"] - len(state["titles"])
    state["offset"] = needed
    return state

# Condition to checj if we have enough articles
def condition(state: State):
    if state["offset"] > 0 and state["total_fetched"] <= state["max_fetch"]:
        return "extract"
    else:
        return "store"

# 3. Store fetched articles
def store(state: State):
    vectorstore.add_texts(state["titles"])

    return state

# 4. Summarise the articles
def summarize(state: State) -> State:
    system_prompt = """
    You are an assistant working on a news website.
    You are given a list of articles from the previous week.
    You need to summarise the articles in a way that is descriptive and still easy to understand.
    Always start directly with the summary without any text before it
"""
    for i in range(len(state["titles"])):
        prompt = [
        ("system", system_prompt),
        ("user", f"Here is the news title: {state['titles'][i]} and the news article content: {state['raw_articles'][i]}")
        ]
        res = llm.invoke(prompt)
        state["summaries"].append(res.content)

    return state

# 5. Publish the newsletter to given mail ids
def publish(state: State) -> State:
    template = make_newsletter_page(state)

    payload = {
        "email_list": state["email_ids"],
        "template": template
    }

    response = requests.post(
        "http://localhost:8000/send_mail",
        json=payload
    )

    if response.status_code == 200:
        print("Email Successfully Sent")
        state["publish_state"] = True
    else:
        print("Error", response)
        state["publish_state"] = False
    return state