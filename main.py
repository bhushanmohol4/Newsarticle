from langgraph.graph import StateGraph, START, END
from nodes import *

load_dotenv()

if __name__ == "__main__":
    email_ids = ["bhushanmohol4@gmail.com"]
    graph_builder = StateGraph(State)
    
    graph_builder.add_node("extract", extract)
    graph_builder.add_node("deduplicate", deduplicate)
    graph_builder.add_node("summarize", summarize)
    graph_builder.add_node("publish", publish)
    graph_builder.add_node("store", store)

    # tools = [extract]
    # llm_tools = llm.bind_tools(tools)

    graph_builder.add_edge(START, "extract")
    graph_builder.add_edge("extract", "deduplicate")
    graph_builder.add_conditional_edges(
        "deduplicate",
        condition,
        {
            "extract": "extract",
            "store": "store"
        }
    )
    graph_builder.add_edge("store", "summarize")
    graph_builder.add_edge("summarize", "publish")
    graph_builder.add_edge("publish", END)

    graph = graph_builder.compile()
    graph.invoke({
        "titles": [],
        "raw_articles": [],
        "links": [],
        "summaries": [],
        "email_ids": email_ids,
        "offset": 0,
        "num_articles": 5,
        "total_fetched": 0,
        "publish_state": False,
        "total_fetched": 0,
        "max_fetch": 7
    })