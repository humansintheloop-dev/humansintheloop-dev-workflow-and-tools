The #$ARGUMENTS specify the following files:

- idea-file: the file containing the refined idea description
- discussion-file: the file where questions and answers were saved
  (including the classification of the idea type)

Now that we’ve wrapped up the brainstorming process, compile our findings into a comprehensive, developer-ready specification.  
This document will later serve as input to a steel-thread implementation plan, but in **this step you must NOT generate any plan**.  
Your output is the specification only.

First, read the discussion-file and determine the idea type:

- A. User-facing feature
- B. Architecture POC
- C. Platform/infrastructure capability
- D. Educational/example repo

Then, based on the type, produce the corresponding specification:

A. If it is a **user-facing feature**, produce a PRD-style spec that includes:
   - Purpose and background
   - Target users and personas
   - Problem statement and goals
   - In-scope and out-of-scope
   - High-level functional requirements
   - Non-functional requirements (UX, performance, reliability, etc.)
   - Success metrics
   - Epics and user stories
   - A set of user-facing scenarios appropriate for defining a later steel-thread plan  
     (identify the main end-to-end scenario, but do NOT generate a plan)

B. If it is an **architecture POC**, produce an Architecture Validation Requirements document that includes:
   - Architectural concern / risk being addressed
   - Architectural goals (quality attributes such as security, performance, etc.)
   - Required architectural capabilities
   - Validation scenarios (quality attribute scenarios)
   - One primary end-to-end thread the POC must demonstrate
   - Identify any possible refinements to that thread (but do NOT generate steel-thread stages or a plan)
   - Constraints and assumptions
   - Acceptance criteria for declaring the POC successful

C. If it is a **platform/infrastructure capability**, produce a Platform Capability Specification that includes:
   - Purpose and context
   - Consumers (teams, services, or systems that will use the platform capability)
   - Capabilities and behaviors the platform must provide
   - High-level APIs, contracts, or integration points
   - Non-functional requirements and SLAs
   - Scenarios and workflows (including one primary end-to-end scenario)  
     These prepare for a later steel-thread plan but do NOT create that plan.
   - Constraints and assumptions
   - Acceptance criteria

D. If it is an **educational/example repo**, produce a Didactic Example Specification that includes:
   - Learning goals
   - Concepts and patterns the example must demonstrate
   - End-to-end example flows
   - Capabilities and constraints
   - Scenarios that a user of the example should be able to run (including a primary scenario)  
     These scenarios support a later steel-thread plan but do NOT create that plan.

Output:

- Save the specification as a markdown document in the same directory as the idea file.
- Use the naming convention:
  - For the idea file '<idea-name>-idea.md', call the specification file '<idea-name>-spec.md'.
