`i2code implement` sometimes fails to commit a task's changes.
For example, because of a permissions issue.
It exits because of the error leaving the repo in the following state:

* The plan file has uncommitted changes that mark the task as done
* There are uncommitted changes that implement the task's work
* `get-next-task` returns the next task

When `i2code implement` is rerun, it continues with the next task instead of retrying the commit.
The changes for both tasks are committed together.

What I would like `i2code implement` to do before entering the main loop is check for uncommitted changes that mark a task as completed and if there are any, attempt to commit them.
And then continue with the main loop as normal.