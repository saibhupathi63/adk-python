# Contributing Resources

This folder host resources for ADK contributors, for example, testing samples etc.

## Samples

Samples folder host samples to test different features. The samples are usually minimal and simplistic to test one or a few scenarios.

**Note**: This is different from the [google/adk-samples](https://github.com/google/adk-samples) repo, which hosts more complex e2e samples for customers to use or modify directly.

### Recommended Patterns

- **[Tool Runner Agent Pattern with RAG](samples/tool_runner_rag_pattern/)** - Demonstrates the architectural pattern for combining VertexAI RAG retrieval tools with custom Python functions, solving the common 400 INVALID_ARGUMENT error when mixing tool types.

## ADK project and architecture overview

The [adk_project_overview_and_architecture.md](adk_project_overview_and_architecture.md) describes the ADK project overview and its technical architecture from high-level.

This is helpful for contributors to understand the project and design philosophy.
 It can also be feed into LLMs for vibe-coding.
