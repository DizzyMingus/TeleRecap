"""
Claude RAG Module

A module providing a single-node LangGraph implementation for RAG (Retrieval Augmented Generation)
using Anthropic's Claude to generate responses based on retrieved documents.
"""

import os
from typing import Dict, Any, List, TypedDict, Optional

from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate

# Load environment variables
load_dotenv()

# Define the state structure for the graph
class GraphState(TypedDict):
    query: str
    retrieved_documents: List[str]
    response: Optional[str]


def generate_response(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    A single node that generates a response using Claude based on retrieved documents and user query.
    
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
        model="claude-3-7-sonnet-latest", 
        api_key=os.environ["ANTHROPIC_API_KEY"],
        temperature=0.3
    )
    
    prompt = ChatPromptTemplate.from_template("""
    You are a helpful assistant answering questions based on the provided information.
    
    Context information:
    {context}
    
    User question: {query}
    
    Please provide a helpful, accurate, and concise answer based only on the context provided.
    If the context doesn't contain relevant information to answer the question, say so rather than making up information.
    
    Make your response more engaging by using appropriate emojis. For example:
    - Use 💡 when sharing insights or key information
    - Use ✅ when confirming something is correct or available
    - Use ❌ when information is not found or unavailable
    - Use 📊 when presenting data or statistics
    - Use 🔍 when referencing search results
    - Use 📝 when providing summaries
    
    Start your response with a relevant emoji that sets the tone for your answer.
    Use section headings with emojis where appropriate to organize longer responses.
    
    Also incorporate emojis naturally within your text, especially when:
    - Expressing emotions (happy 😊, sad 😢, surprised 😲, etc.)
    - Describing actions (reading 📚, writing ✍️, searching 🔎)
    - Emphasizing important points ⚠️
    - Mentioning specific topics (money 💰, time ⏰, technology 💻)
    - Expressing agreement 👍 or disagreement 👎
    - Creating visual cues that enhance readability and engagement
    
    Balance emoji usage to enhance clarity, not distract from your message.
    """)
    
    if isinstance(context, list):
        context_text = "\n\n".join(context)
    else:
        context_text = str(context)

    chain = prompt | model 
    response = chain.invoke({
        "context": context_text,
        "query": query
    })
    response_text = response.content
    return {"response": response_text}


def create_rag_graph():
    """
    Creates and returns a compiled LangGraph for RAG.
    
    Returns:
        A compiled StateGraph instance ready to be invoked.
    """
    graph = StateGraph(GraphState)
    
    graph.add_node("generate", generate_response)
    graph.add_edge(START, "generate");
    graph.add_edge("generate", END);
    
    return graph.compile()


