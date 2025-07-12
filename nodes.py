import os
import requests
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from helper import *
from StateGraph import State
from datetime import date
import time
from langgraph.graph import END
import logging

load_dotenv()

llm = ChatGroq(model = "llama-3.3-70b-versatile", api_key=os.getenv("groq_api"))

logging.basicConfig(
    filename='main.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 1. Fetch news articles
def extract(state: State) -> State:
    try:
        retry_count = 0
        apikey = os.getenv("mediastack_api")
        categories = state["news_categories"]
        categories_str = ",".join(categories)
        interests = ["football", "cricket", "Artificial Intelligence", "LLM", "Singapore", "basketball", "India"]
        country = "in"
        language = "en"
        day = date.today()
        limit_articles = state["num_articles"] if state["offset"] == 0 else state["offset"]
        offset = state["total_fetched"]
        url = f"http://api.mediastack.com/v1/news?access_key={apikey}&categories={categories_str}&languages={language}&date={day}&sort=popularity&limit={limit_articles}&offset={offset}"
        while retry_count < 5:
            response = requests.get(url)
            data = response.json()
            if response.status_code == 200:
                for article in data["data"]:
                    state["titles"].extend([article["title"]])
                    state["raw_articles"].extend([article["description"]])
                    state["links"].extend([article["url"]])
                state["total_fetched"] += len(data["data"])
                retry_count = 999
            elif data["error"]["code"] == "rate_limit_reached":
                time.sleep(1)
                retry_count += 1
            else:
                raise Exception(data["error"])
    except Exception as e:
        print("Error: ", e)
        logging.ERROR("Error: ", e)
        state["exception"] = True
    
    return state

# 2. Check and remove any duplicate articles
def deduplicate(state: State) -> State:
    try:
        if not state["titles"]:
            state["offset"] = state["num_articles"]
            return state
        
        vectors = embed(state["titles"])
        duplicate_index = set()
        
        for i in range(len(vectors)):
            for j in range(i + 1, len(vectors)):
                sim = cosine_similarity(vectors[i], vectors[j])
                if sim > 0.85:
                    duplicate_index.add(j)
                    logging.INFO(f"Duplicate found: '{state['titles'][i]}' and '{state['titles'][j]}' (similarity: {sim:.3f})")
        
        for i in range(len(state["titles"])):
            if i in duplicate_index:
                continue
                
            similar_docs = vectorstore.similarity_search_with_score(
                state["titles"][i], 
                k=1
            )
            
            if similar_docs:
                doc, score = similar_docs[0]
                # Convert distance to similarity (assuming cosine distance)
                similarity = 1 - score
                if similarity > 0.85:  # Same threshold as above
                    duplicate_index.add(i)
                    logging.INFO(f"Store duplicate found: '{state['titles'][i]}' (similarity: {similarity:.3f})")

        for index in sorted(duplicate_index, reverse=True):
            state["raw_articles"].pop(index)
            state["titles"].pop(index)
            state["links"].pop(index)
        
        logging.INFO(f"{len(duplicate_index)} duplicates popped")

        # Calculate how many more articles are needed
        needed = state["num_articles"] - len(state["titles"])
        state["offset"] = needed
    except Exception as e:
        print("Error: ", e)
        logging.ERROR("Error: ", e)
        state["exception"] = True
    return state

# Condition to check if we have enough articles
def condition(state: State):
    try:
        if state["exception"] == True:
            return END
        if state["offset"] > 0 and state["total_fetched"] <= state["max_fetch"]:
            return "extract"
        else:
            return "store"
    except Exception as e:
        print("Error: ", e)
        logging.ERROR("Error: ", e)
        state["exception"] = True

# 3. Store fetched articles
def store(state: State) -> State:
    try:
        if len(state["titles"]) > 0:
            vectorstore.add_texts(state["titles"])
        else:
            pass
    except Exception as e:
        print("Error: ", e)
        logging.ERROR("Error: ", e)
        state["exception"] = True

    return state

# 4. Summarise the articles
def summarize(state: State) -> State:
    try:
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
    except Exception as e:
        print("Error: ", e)
        logging.ERROR("Error: ", e)
        state["exception"] = True

    return state

# 5. Publish the newsletter to given mail ids
def publish(state: State) -> State:
    try:
        print(state["titles"])
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
    except Exception as e:
        print("Error: ", e)
        logging.ERROR("Error: ", e)
        state["exception"] = True
    return state