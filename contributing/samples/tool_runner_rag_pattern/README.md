# Tool Runner Agent Pattern with RAG

This sample demonstrates the "tool-runner agent" architectural pattern for working around the Gemini API constraint that prevents mixing VertexAiRagRetrieval tools with other custom Python function tools in a single agent.

## The Problem

When you try to include the VertexAiRagRetrieval tool in an agent alongside other custom Python function tools, you consistently encounter a 400 INVALID_ARGUMENT error stating that "multiple tools are only supported if they are all search tools." This is a constraint at the Gemini API level.

**Example of the problematic pattern:**
```python
# This WILL NOT work - causes 400 INVALID_ARGUMENT error
broken_agent = Agent(
    name="broken_orchestrator",
    model="gemini-2.0-flash",
    instruction="Answer questions using both RAG and custom tools",
    tools=[
        VertexAiRagRetrieval(...),  # Built-in search tool
        my_custom_function,         # Custom Python function
    ]
)
```

## The Solution: Tool Runner Agent Pattern

The architectural solution is to isolate the RAG tool in a highly specialized, dedicated sub-agent whose only purpose is to host and expose the RAG tool. The main orchestrator then uses AgentTool to delegate to this specialized agent.

**Benefits of this pattern:**
- ✅ Resolves the API conflict cleanly
- ✅ Makes the orchestrator's logic cleaner and more modular  
- ✅ Allows mixing built-in and custom tools effectively
- ✅ Follows separation of concerns principles
- ✅ Easy to test and maintain each component independently

## Architecture Diagram

```
┌─────────────────────────────────────────┐
│           Main Orchestrator             │
│  - Custom Python function tools        │
│  - AgentTool(knowledge_retrieval_agent) │
└─────────────┬───────────────────────────┘
              │ delegates RAG queries
              ▼
┌─────────────────────────────────────────┐
│      Knowledge Retrieval Agent         │
│  - VertexAiRagRetrieval tool ONLY      │
│  - Specialized for RAG operations      │
└─────────────────────────────────────────┘
```

## Quick Start

1. **Setup Environment**
   ```bash
   cd contributing/samples/tool_runner_rag_pattern
   pip install -r requirements.txt
   ```

2. **Run the Architecture Demo** (no API keys required)
   ```bash
   python demo_agent.py
   ```
   This demonstrates the pattern and shows how the agents are structured.

3. **Run the Full Interactive Example** (requires API setup)
   ```bash
   cp .env.example .env
   # Edit .env with your Google API credentials and optionally RAG corpus
   python agent.py --live
   ```

## Files in this Sample

- **`demo_agent.py`** - Architecture demonstration (works without API keys)
- **`agent.py`** - Full interactive example (requires API credentials)
- **`README.md`** - This documentation
- **`.env.example`** - Environment variable template

## Key Implementation Details

### 1. Dedicated RAG Agent
```python
# Specialized agent with ONLY the RAG tool
knowledge_retrieval_agent = Agent(
    name="knowledge_retrieval_agent",
    model="gemini-2.0-flash",
    instruction="Use the RAG tool to search the knowledge base",
    tools=[ask_vertex_retrieval],  # ONLY RAG tool here
)
```

### 2. Main Orchestrator with AgentTool
```python
# Main orchestrator uses AgentTool to access the RAG agent
main_orchestrator = Agent(
    name="main_orchestrator",
    model="gemini-2.0-flash",
    instruction="Answer questions using weather data and knowledge search",
    tools=[
        get_weather,  # Custom Python function
        AgentTool(    # Delegate to RAG agent
            agent=knowledge_retrieval_agent,
            skip_summarization=True
        )
    ]
)
```

## Related Issues & References

This pattern addresses the issues documented in:
- [#969 - Master Issue: built-in tools cannot co-exist with FunctionDeclaration tools](https://github.com/google/adk-python/issues/969)
- [#514 - 400 INVALID_ARGUMENT after Python Tool Call when VertexAiRagRetrieval is Present](https://github.com/google/adk-python/issues/514)  
- [#1293 - RAG and function call cannot work together](https://github.com/google/adk-python/issues/1293)

## Advanced Patterns

### Multiple Specialized Agents
For complex applications, you can create multiple specialized tool-runner agents:

```python
# Specialized agents for different built-in tools
search_agent = Agent(tools=[google_search])
rag_agent = Agent(tools=[vertex_rag_retrieval])
code_agent = Agent(tools=[code_executor])

# Orchestrator coordinates between them
orchestrator = Agent(tools=[
    custom_function1,
    custom_function2, 
    AgentTool(search_agent),
    AgentTool(rag_agent),
    AgentTool(code_agent),
])
```

### Error Handling and Fallbacks
```python
knowledge_agent = Agent(
    name="knowledge_agent",
    instruction="""
    Search the knowledge base. If no relevant information is found,
    return 'No relevant information found in knowledge base.'
    """,
    tools=[rag_tool]
)
```

This pattern has proven effective in production applications and is recommended for any multi-agent system that needs to combine RAG retrieval with custom function tools.