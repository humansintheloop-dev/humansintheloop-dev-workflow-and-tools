Given the idea and specification files in $#ARGUMENTS, we need to create a detailed implementation plan that will be used by a LLM/GenAI coding agent to implement the idea.

I want to implement this using the Steel thread methodology.

* Each steel thread is one very narrow to end to end flow that delivers some value to the user.
* The first thread should setup the project
  * Whenever possible, it should use the recommended starter/template/skeleton for the technology stack.
  * It should setup the an automated deployment pipeline, e.g. Github Actions that builds and tests the application.
  * If applicable, the deployment pipeline should deploy the application

* Each of the following threads should build on the previous ones, adding more functionality.
* Organize the steel threads by causal dependencies and architectural priority.
* Ideally a thread should implement an end-to-end flow through the architecture: for example, Controller (or message handler) -> Service -> Repository -> DB and back.


The process for defining the threads should be iterative:

* Draft the initial set of threads based on the requirements and architecture defined in the specification.
* Review each thread and whenever possible, break it down into smaller threads - ensuring that each thread delivers value.

Each thread should include the steps that implement the thread using TDD principles:

* Write a test
* Implement the code to make the test pass
* Refactor whenever necessary
* If new tests are needed, update the thread to include them.

The implementation should be:

* Markdown document in the same directory as $#ARGUMENTS using the following naming convention: for the specification file called '<idea-name>-spec.md, call the plan '<idea-name>-plan.md'

* Each task should be prompt that will be given to a coding agent
* Each task in the plan should have a checkbox '[ ]' at the start of the line
* Each subtask/step within a task should also have a checkbox '[ ]' for granular tracking
* Include instructions for the coding LLM to mark each checkbox as '[x]' when the task/step is completed
* Make sure and separate each prompt section. Use markdown. Each prompt should be tagged as text using code tags. The goal is to output prompts, but context, etc is important as well.

The final section of the plan is a "## Change History".
It's initially empty.
You must record any changes to the plan requested during a conversation in this section.
