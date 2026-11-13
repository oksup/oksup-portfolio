# Agent Control Plane: Scoped workflow automation

**Role:** Project owner. I designed the workflow, defined the tool permissions and evaluation cases, and validated the local prototype.

**Status:** Personal prototype, tested locally.

## The problem

Task updates, notes and coding requests had separate interfaces. I wanted to handle them from a single chat interface while keeping the actions available in each workflow predictable.

## Design decisions

- **Give each workflow a small set of tools.** A Python orchestrator presents only the tools assigned to the active Discord channel and checks that assignment again before executing a request.
- **Keep sensitive changes in review.** The coding workflow routes changes involving protected areas such as authentication and payments to a human review step.
- **Test the workflow before adding infrastructure.** SQLite and Markdown gave me working task and notes backends without requiring separate hosted services. A repeatable evaluation suite exercised routing and tool selection while I refined the workflow.

## What worked

The local prototype connected Discord to task and notes workflows and ran a coding job end to end. It also recorded model usage and estimated costs. The project demonstrates how I translate an operating process into explicit permissions, measurable behavior and review steps.
