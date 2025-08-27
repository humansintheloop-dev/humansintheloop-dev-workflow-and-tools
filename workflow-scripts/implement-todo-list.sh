FILE=${1?}
shift

SPECIFIC_TASK="Implement all tasks one by one"

if [ -n "$1" ] ; then
  SPECIFIC_TASK="Implement this task only: $1"
fi

claude "$FILE is a to-do list of tasks.

${SPECIFIC_TASK} 

IMPORTANT when a task is implemented, Update the to-do list file to mark the task as completed.
Do this  BEFORE committing the task's changes  so that the commit includes the task's changes and the updated to-do list"
