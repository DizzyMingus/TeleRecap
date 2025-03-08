import os
from typing import Dict, Any, List, TypedDict, Optional

from dotenv import load_dotenv
from langgraph.graph import StateGraph
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()


def generate_response(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    A single node that generates a response using Claude 3.5 Haiku based on retrieved documents and user query.

    Args:
        state: The graph state containing:
            - retrieved_documents: List of document content strings
            - query: User's question

    Returns:
        Updated state with response field added
    """
    context = state.get("retrieved_documents", [])
    query = state.get("query", "")

    model = ChatAnthropic(
        model="claude-3-5-sonnet-20241022", api_key=os.environ["ANTHROPIC_API_KEY"]
    )

    prompt = ChatPromptTemplate.from_template(
        """
    You are a helpful assistant answering questions based on the provided information.
    
    Context information:
    {context}
    
    User question: {query}
    
    Please provide a helpful, accurate, and concise answer based only on the context provided.
    If the context doesn't contain relevant information to answer the question, say so rather than making up information.
    """
    )

    if isinstance(context, list):
        context_text = "\n\n".join(context)
    else:
        context_text = str(context)

    chain = prompt | model
    response = chain.invoke({"context": context_text, "query": query})

    response_text = response.content

    return {"response": response_text}


class GraphState(TypedDict):
    query: str
    retrieved_documents: List[str]
    response: Optional[str]


graph = StateGraph(GraphState)

graph.add_node("generate", generate_response)
graph.set_entry_point("generate")
graph.set_finish_point("generate")

compiled_graph = graph.compile()

result = compiled_graph.invoke(
    {
        "query": "What are the key features of RAG systems?",
        "retrieved_documents": [
            "RAG (Retrieval Augmented Generation) combines information retrieval with language model generation.",
            "Key features include: ability to access external knowledge, reduced hallucinations, and up-to-date information.",
        ],
    }
)

print(result["response"])
