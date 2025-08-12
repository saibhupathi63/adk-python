# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Tool Runner Agent Pattern with RAG

This example demonstrates the "tool-runner agent" architectural pattern for 
working around the Gemini API constraint that prevents mixing VertexAiRagRetrieval 
tools with other custom Python function tools in a single agent.

The key insight is to isolate the RAG tool in a dedicated sub-agent and use 
AgentTool to access it from the main orchestrator.
"""

import os
from dotenv import load_dotenv

from google.adk.agents import Agent
from google.adk.tools import AgentTool
from google.adk.tools.retrieval.vertex_ai_rag_retrieval import VertexAiRagRetrieval
from google.adk.runners import InMemoryRunner
from google.genai import types
from vertexai.preview import rag

load_dotenv()

# --- Configuration ---
APP_NAME = "tool_runner_rag_example"
USER_ID = "demo_user"
SESSION_ID = "demo_session"

# --- Custom Function Tools ---
def get_weather(city: str) -> dict:
    """Get weather information for a city."""
    # Mock weather data - in real usage, this would call a weather API
    weather_data = {
        "New York": {"temperature": "72°F", "condition": "Sunny", "humidity": "45%"},
        "London": {"temperature": "18°C", "condition": "Cloudy", "humidity": "70%"},
        "Tokyo": {"temperature": "25°C", "condition": "Rainy", "humidity": "80%"},
    }
    
    if city in weather_data:
        return {
            "status": "success",
            "city": city,
            "weather": weather_data[city]
        }
    else:
        return {
            "status": "error", 
            "message": f"Weather data not available for {city}"
        }

def calculate_wind_chill(temperature_f: float, wind_speed_mph: float) -> dict:
    """Calculate wind chill temperature using the NWS formula."""
    if temperature_f > 50 or wind_speed_mph < 3:
        return {
            "wind_chill": temperature_f,
            "note": "Wind chill not applicable (temperature > 50°F or wind < 3 mph)"
        }
    
    # NWS Wind Chill Formula
    wind_chill = (35.74 + 
                  0.6215 * temperature_f - 
                  35.75 * (wind_speed_mph ** 0.16) + 
                  0.4275 * temperature_f * (wind_speed_mph ** 0.16))
    
    return {
        "temperature_f": temperature_f,
        "wind_speed_mph": wind_speed_mph, 
        "wind_chill_f": round(wind_chill, 1)
    }

# --- RAG Tool Setup ---
def create_rag_tool():
    """Create a VertexAI RAG retrieval tool if properly configured."""
    rag_corpus = os.environ.get("RAG_CORPUS")
    
    if not rag_corpus:
        print("⚠️  RAG_CORPUS not configured - using mock RAG function")
        return mock_rag_search  # Return the function directly
    
    try:
        return VertexAiRagRetrieval(
            name="search_knowledge_base",
            description="Search the knowledge base for relevant information",
            rag_resources=[
                rag.RagResource(rag_corpus=rag_corpus)
            ],
            similarity_top_k=3,
            vector_distance_threshold=0.5,
        )
    except Exception as e:
        print(f"⚠️  Error creating VertexAI RAG tool: {e}")
        print("    Using mock RAG function instead")
        return mock_rag_search  # Return the function directly

def mock_rag_search(query: str) -> str:
    """Mock RAG search function for demonstration when VertexAI RAG is not configured."""
    # Mock knowledge base responses
    mock_responses = {
        "python": "Python is a high-level programming language known for its simplicity and readability. It supports multiple programming paradigms and has a vast ecosystem of libraries.",
        "weather": "Weather refers to atmospheric conditions including temperature, humidity, wind, and precipitation. Climate change is affecting global weather patterns.",
        "climate": "Climate represents long-term weather patterns. Global climate change is causing shifts in temperature and precipitation worldwide.",
        "machine learning": "Machine learning is a subset of AI that enables systems to learn from data without explicit programming.",
    }
    
    # Find best match
    query_lower = query.lower()
    for topic, response in mock_responses.items():
        if topic in query_lower:
            return f"Knowledge base result for '{query}': {response}"
    
    return f"No specific information found in knowledge base for: {query}"

# --- Agent Definitions ---

# 1. Dedicated RAG Agent (Tool Runner Pattern)
def create_knowledge_retrieval_agent():
    """Creates a specialized agent that ONLY handles RAG retrieval."""
    rag_tool = create_rag_tool()
    
    return Agent(
        name="knowledge_retrieval_agent", 
        model="gemini-2.0-flash",
        description="Specialized agent for searching the knowledge base using RAG",
        instruction="""You are a knowledge retrieval specialist. Your only job is to search 
        the knowledge base using the search_knowledge_base tool when asked. 
        
        Always use the tool to search for information - never try to answer from your own knowledge.
        Return the search results clearly and concisely.""",
        tools=[rag_tool]  # ONLY the RAG tool - this is the key to avoiding API conflicts
    )

# 2. Main Orchestrator Agent 
def create_main_orchestrator():
    """Creates the main orchestrator that can use both custom tools and RAG via AgentTool."""
    knowledge_agent = create_knowledge_retrieval_agent()
    
    return Agent(
        name="weather_and_knowledge_orchestrator",
        model="gemini-2.0-flash", 
        description="Main orchestrator that handles weather queries and knowledge searches",
        instruction="""You are a helpful assistant that can:

1. Provide weather information using the get_weather tool
2. Calculate wind chill using the calculate_wind_chill tool  
3. Search a knowledge base using the knowledge_retrieval_agent

When users ask about weather, use the weather tools. When they ask for general information
or want to search for knowledge, delegate to the knowledge_retrieval_agent.

You can combine information from multiple sources to provide comprehensive answers.""",
        tools=[
            get_weather,
            calculate_wind_chill,
            AgentTool(
                agent=knowledge_agent,
                skip_summarization=True  # Get raw results from the knowledge agent
            )
        ]
    )

# --- Demonstration Functions ---

async def demo_query(runner, query: str):
    """Run a demo query and display the results."""
    print(f"\n🤔 Query: {query}")
    print("=" * 50)
    
    content = types.Content(role="user", parts=[types.Part(text=query)])
    
    response_parts = []
    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=SESSION_ID, 
        new_message=content
    ):
        if event.is_final_response():
            if event.content and event.content.parts:
                if event.content.parts[0].text:
                    response_parts.append(event.content.parts[0].text)
    
    print("🤖 Response:")
    for part in response_parts:
        print(part)
    print("\n" + "=" * 50)

async def main():
    """Main demonstration function."""
    print("🚀 Tool Runner Agent Pattern with RAG - Demo")
    print("This example shows how to combine RAG retrieval with custom function tools")
    print("by using the tool-runner agent architectural pattern.\n")
    
    # Create the main orchestrator
    root_agent = create_main_orchestrator()
    
    # Set up runner
    runner = InMemoryRunner(agent=root_agent, app_name=APP_NAME)
    await runner.session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID
    )
    
    print("✅ Agents created successfully!")
    print(f"   - Main orchestrator: {root_agent.name}")
    print(f"   - Knowledge agent: Available via AgentTool")
    print(f"   - Custom tools: get_weather, calculate_wind_chill")
    
    # Demo queries showing different capabilities
    queries = [
        "What's the weather in New York?",
        "Search the knowledge base for information about Python",
        "What's the weather in London and also search for information about climate?",
        "Calculate the wind chill if the temperature is 32°F and wind speed is 15 mph",
        "Can you search for machine learning information?",
    ]
    
    for query in queries:
        await demo_query(runner, query)
    
    print("\n✨ Demo complete! The tool-runner agent pattern successfully allows")
    print("   mixing custom Python functions with RAG retrieval tools.")
    print("\n📚 Key takeaways:")
    print("   - RAG tool is isolated in its own dedicated agent")  
    print("   - Main orchestrator uses AgentTool to access RAG functionality")
    print("   - No 400 INVALID_ARGUMENT errors when mixing tool types")
    print("   - Clean separation of concerns and modular architecture")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())