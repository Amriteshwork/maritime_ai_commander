from typing import Annotated, TypedDict
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from src.agents.mcp_tools import get_vessel_telemetry, predict_vessel_trajectory, assess_vessel_risk
from src.agents.rag_pipeline import maritime_regulatory_retriever
import os

# Define State
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]

# Initialize Tools and LLM
tools = [
    get_vessel_telemetry, 
    predict_vessel_trajectory, 
    assess_vessel_risk, 
    maritime_regulatory_retriever
]

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0) # Or gpt-4-turbo
llm_with_tools = llm.bind_tools(tools)

# System Prompt detailing the Agentic Workflow
system_prompt = """You are the Maritime AI Commander, an autonomous agentic intelligence system.
You have specialized tools for:
1. Vessel Tracking (telemetry)
2. Risk Assessment (anomaly detection)
3. Route Optimization (trajectory prediction)
4. Maritime RAG (access to regulations and historical data)

Always verify vessel status using telemetry before predicting or assessing risk. 
If an anomaly is detected, cross-reference it with the maritime_regulatory_retriever to explain WHY it is a risk based on maritime law or historical precedent.
Provide concise, actionable intelligence."""

def agent_node(state: AgentState):
    messages = state["messages"]
    if not any(msg.type == "system" for msg in messages):
         messages = [{"role": "system", "content": system_prompt}] + messages
    
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

# Build the LangGraph
workflow = StateGraph(AgentState)

workflow.add_node("agent", agent_node)
workflow.add_node("tools", ToolNode(tools))

workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", tools_condition)
workflow.add_edge("tools", "agent")

# Compile graph
agent_app = workflow.compile()