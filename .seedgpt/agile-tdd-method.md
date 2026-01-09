On seedgpt the planting is done once. 
from that point we will do this in a loop:
1. status recap  - evaluate new client communication, where were at, update docs accordingly. check if we need to update the roadmap and PRD according to recent work. check the git status and commit the changes if needed. check current roadmap and PRD and client communication and current state of the project in the filesystem and update the sprint plan accordingly.
2. planning - plan the next sprint. We multiple the work effort by 2 and seperate to 2 different developers - test and dev. The tester starts first and provides a black-box testing code that tests and verifies the PRD as a blackbox and using the app's officials APIs (he can write himself utilities and simulators and mocks and unittests for his verification code), the dev writes his code and delivers the require feature (he also creates his own unittests). this is done on feature-name/dev and feature-name/test branches (e.g)
3. a. Implementation - each worker (dev/test) fully implmenets his tasks and pass his local tests.
3. b. update plans
4. integration - both test and dev are merge into feature-name branch and tests are executed, and dev/test code is debugged until all tests pass.
5. a. Merge - feature-name branch is merged to main branch, and all tests cycle runs again and code/tests are debugged and fixed until its all green.
5. b. update plans
6. a. Deploy, test post deployment 
6. b. update plans
7. meet with client and present results, analyse them etc. 
8. gather new inputs and record them. 
9. update docs and roadmap and PRD and client communication and current state of the project in the filesystem and update the sprint plan accordingly.

## CRITICAL: Sprint YAML Updates
**After EACH sprint is completed, you MUST:**
1. Update the sprint YAML file (`/.seedgpt/sprints/sprint-vXX-*.yml`) with:
   - `status: complete`
   - `completed_date: "YYYY-MM-DD"`
   - `progress: 100`
   - Mark each story with `status: complete` and `completed_date`
2. Commit this update to main with message like: `chore: Mark Sprint vX.X as 100% complete`
3. Push to origin immediately

**After EACH story is completed:**
1. Update the story in sprint YAML with `status: complete` and `completed_date`
2. If multiple stories done in batch, update them together

This ensures the sprint state is always accurately tracked in git history.

---

When this file is referenced, it is expected that the reader will understand the context and the flow of the project and the different roles and responsibilities of the different agents and the different tasks and the different periods of time and the different ai agents with different capabilities and differnet prompts and goals and do it all autonomously.

when auto-mode is used, Do not ask the user questions, and decide everything autonomously.

YOU ARE AND AGENT, and you will be solving the tasks. IT DOES NOT take human hours to solve the tasks, it takes AI to solve the tasks, and usually done in minutes. so lets put all the time calculations a side and just say easy/hard/medium etc.

At the end of each operations/call/task - also update roadmap and PRD to the current progress and state of the project.

For each new task, thoroughly read the PRD and roadmap and the filesystem actual state to understand where we are and where we need to go and what we have done so far and update the docs accordingly.

The tests of the TDD should be well structured and cover all the possible cases and edge cases. they should be well documented and easy to understand. They should be saved in nice and smart and meaningful hierarchy and structure and naming in the filesystem.