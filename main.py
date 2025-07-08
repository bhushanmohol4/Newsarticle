from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict
import os
import requests
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from jinja2 import Template

load_dotenv()

llm = ChatGroq(model = "llama-3.3-70b-versatile", api_key=os.getenv("groq_api"))

class State(TypedDict):
    titles: list[str]
    raw_articles: list[str]
    links: list[str]
    cleaned_articles: list[str]
    summaries: list[str]
    newsletter: str
    email_ids: list[str]
    publish_state: bool

def extract(state: State) -> State:
    apikey = os.getenv("gnews_api")
    keywords = ["Sports"]
    for keyword in keywords:
        url = f"https://gnews.io/api/v4/search?q={keyword}&lang=en&country=in&max=10&apikey={apikey}"
        response = requests.get(url)
        data = response.json()
        for article in data["articles"]:
            state["titles"].extend([article["title"]])
            state["raw_articles"].extend([article["content"]])
            state["links"].extend([article["url"]])

    return state

def clean(state: State) -> State:
    return state

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
        state["publish_state"] = True
    else:
        state["publish_state"] = False
    print(response)
    return state

def make_newsletter_page(state: State):
    html_template = open("email_template.html").read()
    template = Template(html_template)

    rendered_html = template.render(
        subject = "Weekly Newsletter",
        title = "Weekly Newsletter",
        intro = "Here's what happened this week:",
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

if __name__ == "__main__":
    graph_builder = StateGraph(State)
    
    graph_builder.add_node("extract", extract)
    graph_builder.add_node("clean", clean)
    graph_builder.add_node("summarize", summarize)
    graph_builder.add_node("publish", publish)

    # tools = [extract]
    # llm_tools = llm.bind_tools(tools)

    graph_builder.add_edge(START, "extract")
    graph_builder.add_edge("extract", "summarize")
    graph_builder.add_edge("summarize", "publish")
    graph_builder.add_edge("publish", END)

    graph = graph_builder.compile()
    graph.invoke({"titles": [], "raw_articles": [], "links": [], "summaries": [], "email_ids": ["bhushanmohol4@gmail.com"]})