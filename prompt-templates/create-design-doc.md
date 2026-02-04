The following files contain the idea, discussion, and specification:

- idea-file: @${IDEA_FILE}
- discussion-file: @${DISCUSSION_FILE}
- spec-file: @${SPEC_FILE}

The following skills are available. **You MUST read each skill and apply its guidelines in the design**:

${DESIGN_SKILLS}

**Important**: Do not just reference skill names. Read each skill's SKILL.md file and ensure the design follows its specific guidelines.

Create a high-level architecture/design document that describes how the idea will be implemented.
This document will later serve as input to the implementation plan, but in **this step you must NOT generate any implementation plan or tasks**.
Your output is the design document only.

First, read all the input files to understand:
- The original idea and its context
- The discussion and decisions made during brainstorming
- The specification with requirements and scenarios

**Reference projects**: If the input files mention any existing projects as references or examples to build upon, read those projects to understand their patterns and structure. The design should be consistent with established patterns from reference projects.

**Existing codebase**: If the specification describes changes to an existing application, read the relevant parts of the existing codebase to understand what exists. Compare with the specification to determine what needs to be added, modified, or deleted. NEVER read an existing design doc to determine changes - the inputs are the idea, discussion, spec, and existing code only.

Then, produce a Design Document organized around four architectural views.

**Diagram requirement:** Each view MUST include:
1. A Mermaid diagram in a fenced code block (` ```mermaid `). Use the diagram type specified for each view.
2. A bullet list describing each element shown in the diagram: what it is and why it's required.
3. **If modifying an existing application**: Only show elements being added, modified, or deleted. Clearly label each (e.g., "NEW:", "MODIFIED:", "DELETED:").

## 1. Overview
- Brief summary of what is being built
- Key goals and constraints from the specification
- **If modifying an existing application**: Describe only the changes - existing elements being modified, elements being added, and elements being deleted.

## 2. UI/UX View (if applicable)
**Include this section only if the change involves UI.** For new applications, describe the full UI design. For existing applications, focus on changes only - do not describe existing UI.

### Visible UI
- **Diagram** (Mermaid `flowchart` or wireframe description): New/modified user flows, screen layouts, or interaction patterns
- Screens being added, modified, or deleted (label each: NEW/MODIFIED/DELETED)
- New user interactions and navigation changes
- Accessibility requirements for new/modified elements
- Responsive design requirements for new/modified elements

### Implementation
- **Diagram** (Mermaid `flowchart` or `classDiagram`): Component hierarchy and data flow for new/modified UI
- Framework-level changes (React, NextJS, Vue, etc.)
- Components, hooks, state management changes
- Routing changes
- API/data fetching changes related to UI

## 3. Security Architecture (if applicable)
**Include this section only if security is a significant concern.** For new applications, describe the full security architecture. For existing applications, focus on changes only - do not describe existing security.
- **Diagram** (Mermaid `flowchart`): Authentication/authorization flows, trust boundaries, data protection points
- Authentication changes (new/modified identity providers, login flows, session management)
- Authorization changes (new/modified roles, permissions, access control)
- Data protection changes (encryption, secrets management, sensitive data handling)
- API security changes (new/modified endpoints requiring auth, rate limiting, input validation)
- Compliance considerations (if applicable)

## 4. Domain View
The organization of programming language elements into subdomains (slices of business functionality):
- **Diagram** (Mermaid `classDiagram`): Package/module structure showing key classes and their relationships
- Key domain concepts and entities
- Subdomain boundaries and responsibilities
- Key classes, interfaces, and their relationships
- Domain patterns being applied (e.g., aggregates, repositories, services)

## 5. Component View
The logical organization of subdomains into components, independent of deployment technology:
- **Diagram** (Mermaid `flowchart`): Show logical components and their interactions using subgraphs for component boundaries
- Component boundaries and responsibilities (e.g., "Spring Boot application", "message broker", "certificate authority" - NOT "container" or "Docker service")
- Which subdomains belong to which components
- Component interfaces and APIs (protocols, ports, endpoints)
- Inter-component communication patterns
- Dependencies between components

**Important:** This view describes WHAT the components are and how they interact logically. Deployment technology (Docker, Kubernetes, VMs) belongs in the Deployment View.

## 6. Deployment View
The technologies used to run and observe the components:
- **Diagram** (Mermaid `flowchart`): Show deployment artifacts (containers, pods, networks) and how components map to them
- Runtime environment (Docker Compose, Kubernetes, serverless, VMs, etc.)
- How components map to deployment artifacts (containers, pods, services, etc.)
- Infrastructure components (databases, message queues, caches)
- Observability stack (logging, metrics, tracing)
- Security infrastructure (authentication, authorization, secrets management)
- Scaling and resilience mechanisms
- **Startup sequence**: The ordered list of commands/scripts to bring up the system, including any initialization scripts that configure infrastructure (e.g., create topics, set up ACLs, initialize databases)
- **Shutdown sequence**: The ordered list of commands to cleanly stop the system

## 7. Build View
The organization of source code and the path from development to production:
- **Diagram** (Mermaid `flowchart`): Build pipeline and/or repository structure showing build projects and their relationships
- Source code repository structure (must include ALL scripts and configuration files mentioned elsewhere in the document)
- **Dataflow**: Describe how data and configuration flow through the system - what produces each artifact (scripts, files, environment variables), what consumes it, and how it propagates between components. Trace the flow from initial setup through runtime.
- Build projects and their relationships
- CI/CD pipeline stages
- Testing strategy at each stage
- Deployment pipeline (how changes flow to production)
- Environment progression (dev, staging, production)

**Consistency check:** Every script, configuration file, or artifact referenced in other sections must appear here with sufficient detail that a developer could implement it.

## 8. Key Design Decisions
- Important architectural choices and their rationale
- Trade-offs considered and why the chosen approach was selected
- Patterns or principles being applied

## 9. Technical Risks and Mitigations
- Identified technical risks
- Proposed mitigations or areas needing further investigation

## 10. Open Questions
- Design decisions that need further clarification
- Areas where multiple approaches are viable and a decision is deferred

Output:

- Save the design document as a markdown file in the same directory as the idea file.
- Use the naming convention:
  - For the idea file '<idea-name>-idea.md', call the design file '<idea-name>-design.md'.
- **IMPORTANT: Always generate a complete new design document from scratch.** Do NOT append to an existing file, do NOT just add a changelog entry, do NOT skip generation because a file exists.
- After saving the design document, invoke the `/review-design-doc` command to walk through the design decisions with the user.

## Design Document Update Guidelines

When modifying a design document after initial creation:

1. Add or update the `## Change History` section at the end of the document
2. For each change, record:
   - Date of change
   - Brief description of what changed
   - Rationale for the change
3. Format: `### YYYY-MM-DD: <brief description>`

This ensures design documents maintain an audit trail of how the architecture evolved.
