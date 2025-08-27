FILE=${1?}

claude "$FILE is a to-do list. 

I want you to refine the TODO list so it's a series of smaller tasks.

Analyze each item on the list and break it down into a series of smaller tasks. 
Repeat the analysis until you have a set of atomic tasks.
An atomic task should be as small as possible without breaking the tests

For example, if the existing todo item involves refactoring multiple classes, analyze the code to identify the classes and create separate tasks for each class.

Each atomic task should be implemented using TDD whenever possible. 

After implementing each atomic task, run gradlew check and commit changes. 

IMPORTANT A task should not reference specific line numbers because they might change

The result will be an updated to-do list that will be implemented later. "
