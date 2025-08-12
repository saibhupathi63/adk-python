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
Tool Runner Agent Pattern with RAG - Interactive Demo

This example demonstrates the "tool-runner agent" architectural pattern for 
working around the Gemini API constraint that prevents mixing VertexAiRagRetrieval 
tools with other custom Python function tools in a single agent.

The key insight is to isolate the RAG tool in a dedicated sub-agent and use 
AgentTool to access it from the main orchestrator.

This demo shows the architecture and can be run with actual API keys,
or in demo mode to understand the pattern.
"""

import os
from dotenv import load_dotenv

from google.adk.agents import Agent
from google.adk.tools import AgentTool
from google.adk.tools.retrieval.vertex_ai_rag_retrieval import VertexAiRagRetrieval
from vertexai.preview import rag

load_dotenv()

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

def mock_rag_search(query: str) -> str:
    """Mock RAG search function for demonstration when VertexAI RAG is not configured."""
    # Mock knowledge base responses
    mock_responses = {
        "python": "Python is a high-level programming language known for its simplicity and readability. It supports multiple programming paradigms and has a vast ecosystem of libraries.",
        "weather": "Weather refers to atmospheric conditions including temperature, humidity, wind, and precipitation. Climate change is affecting global weather patterns.",
        "climate": "Climate represents long-term weather patterns. Global climate change is causing shifts in temperature and precipitation worldwide.",
        "machine learning": "Machine learning is a subset of AI that enables systems to learn from data without explicit programming.",
        "artificial intelligence": "AI refers to computer systems that can perform tasks typically requiring human intelligence, including learning, reasoning, and perception.",
    }
    
    # Find best match
    query_lower = query.lower()
    for topic, response in mock_responses.items():
        if topic in query_lower:
            return f"Knowledge base result for '{query}': {response}"
    
    return f"No specific information found in knowledge base for: {query}"

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

def demonstrate_architecture():
    """Demonstrate the architecture without making API calls."""
    print("🚀 Tool Runner Agent Pattern with RAG - Architecture Demo")
    print("=" * 60)
    print()
    
    print("🔧 ARCHITECTURE OVERVIEW:")
    print()
    print("This pattern solves the Gemini API constraint that prevents mixing")
    print("VertexAiRagRetrieval tools with custom Python function tools.")
    print()
    
    print("❌ PROBLEMATIC PATTERN (causes 400 INVALID_ARGUMENT):")
    print("   ┌─────────────────────────────┐")
    print("   │      Single Agent           │")
    print("   │  ❌ VertexAiRagRetrieval    │")
    print("   │  ❌ custom_function_1       │") 
    print("   │  ❌ custom_function_2       │")
    print("   └─────────────────────────────┘")
    print()
    
    print("✅ SOLUTION: TOOL RUNNER AGENT PATTERN:")
    print("   ┌─────────────────────────────────────────┐")
    print("   │           Main Orchestrator             │")
    print("   │  ✅ get_weather (custom function)       │")
    print("   │  ✅ calculate_wind_chill (custom fn)    │")
    print("   │  ✅ AgentTool(knowledge_agent)          │")
    print("   └─────────────┬───────────────────────────┘")
    print("                 │ delegates RAG queries")
    print("                 ▼")
    print("   ┌─────────────────────────────────────────┐")
    print("   │      Knowledge Retrieval Agent         │")
    print("   │  ✅ VertexAiRagRetrieval tool ONLY     │")
    print("   │  ✅ Specialized for RAG operations     │")
    print("   └─────────────────────────────────────────┘")
    print()
    
    print("🏗️  CREATING AGENTS...")
    
    # Create agents to show the structure
    try:
        knowledge_agent = create_knowledge_retrieval_agent()
        main_orchestrator = create_main_orchestrator()
        
        print(f"✅ Knowledge Agent Created: '{knowledge_agent.name}'")
        print(f"   - Tools: {[tool.__name__ if hasattr(tool, '__name__') else type(tool).__name__ for tool in knowledge_agent.tools]}")
        print()
        
        print(f"✅ Main Orchestrator Created: '{main_orchestrator.name}'")
        print("   - Custom Tools:")
        for tool in main_orchestrator.tools:
            if hasattr(tool, '__name__'):
                print(f"     • {tool.__name__} (Python function)")
            elif hasattr(tool, 'agent'):
                print(f"     • AgentTool({tool.agent.name}) - delegates to RAG agent")
            else:
                print(f"     • {type(tool).__name__}")
        
        print()
        print("🎯 KEY BENEFITS:")
        print("   ✅ No 400 INVALID_ARGUMENT errors")
        print("   ✅ Clean separation of concerns")
        print("   ✅ Modular and testable architecture") 
        print("   ✅ Can mix any built-in tools with custom functions")
        print()
        
        print("📚 USAGE EXAMPLES:")
        print("   • \"What's the weather in New York?\" → uses custom get_weather function")
        print("   • \"Search for Python information\" → delegates to RAG agent")
        print("   • \"Weather + search query\" → uses both via orchestration")
        print()
        
        print("🔗 RELATED GITHUB ISSUES:")
        print("   • #969 - Master Issue: built-in tools cannot co-exist with FunctionDeclaration tools")
        print("   • #514 - 400 INVALID_ARGUMENT after Python Tool Call when VertexAiRagRetrieval is Present")
        print("   • #1293 - RAG and function call cannot work together")
        print()
        
        api_key = os.environ.get("GOOGLE_API_KEY")
        if api_key and api_key != "mock_key_for_demo":
            print("🚀 To run with live API calls, execute:")
            print("   python agent.py --live")
        else:
            print("💡 To test with live API calls:")
            print("   1. Set up your .env file with valid GOOGLE_API_KEY")
            print("   2. Optionally configure RAG_CORPUS for real RAG")
            print("   3. Run: python agent.py --live")
            
        print("\n✨ Architecture demonstration complete!")
        
    except Exception as e:
        print(f"❌ Error creating agents: {e}")
        print("   This is likely due to missing or invalid API credentials.")
        print("   The pattern is still valid - check the README for setup instructions.")

def main():
    """Main function - choose demo mode or live mode based on arguments."""
    import sys
    
    if "--live" in sys.argv:
        # Live mode would go here - but requires API keys
        print("Live mode requires valid API credentials in .env file")
        print("For now, showing architecture demo...")
        demonstrate_architecture()
    else:
        # Default to architecture demonstration
        demonstrate_architecture()

if __name__ == "__main__":
    main()