Given the idea, specification and user stories files in $#ARGUMENTS, we need to create a detailed implementation plan that will be used by a LLM/GenAI coding agent to implement the idea.

I want to implement this idea using the Steel thread methodology.

* Each steel thread is one very narrow to end to end flow that delivers some value to the user.
* The first thread should setup the project
  * Whenever possible, it should use the recommended starter/template/skeleton for the technology stack.
  * It should setup the an automated deployment pipeline, e.g. Github Actions that builds and tests the application.
  * If applicable, the deployment pipeline should deploy the application
* Each of the following threads should implement exactly ONE user story scenario (not multiple scenarios)
* Clearly identify each scenario as "<User Story Name>: <Scenario Name>" 
* Implement happy path scenarios first, then add error handling and edge cases
* Organize the steel threads by causal dependencies and architectural priority.


* A Steel thread consists of a series of a hierarchy of tasks
* Each task implements a meaningful chunk of functionality
  * The lowest level task implements a software element - e.g. class or function or method
  * High-level tasks use the outputs of lower-level tasks to create a larger software element, e.g. package or module.
 * Each task is a series of steps
 * Each step corresponds to TDD principles
   * Write a test (as a single BDD test with Given/When/Then/And clauses, not separate items)
   * Write the code to make the test pass
   * Refactor the code
     * If necessary introduce new elements
     * Update the tasks to add new tests for those elements.


The implementation should be:

* Markdown document in the same directory as $#ARGUMENTS using the following naming convention: for the stories file called '<idea-name>-stories.md', call the plan file '<idea-name>-story-plan.md'
* Each task should be prompt that will be given to a coding agent
* Each task in the plan should have a checkbox '[ ]' at the start of the line
* Each subtask/step within a task should also have a checkbox '[ ]' for granular tracking
* BDD tests should be written as single test specifications with Given/When/Then/And clauses in a code block, not as individual checkbox items
* Include instructions for the coding LLM to mark each checkbox as '[x]' when the task/step is completed
* Make sure and separate each prompt section. Use markdown. Each prompt should be tagged as text using code tags. The goal is to output prompts, but context, etc is important as well.
