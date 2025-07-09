from typing_extensions import TypedDict, Annotated

class State(TypedDict):
    titles: Annotated[list[str], "merge"]
    raw_articles: Annotated[list[str], "merge"]
    links: Annotated[list[str], "merge"]
    summaries: Annotated[list[str], "merge"]
    email_ids: Annotated[list[str], "merge"]
    publish_state: bool
    offset: int
    num_articles: int
    total_fetched: int
    max_fetch: int