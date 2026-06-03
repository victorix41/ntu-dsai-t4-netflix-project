As a collaborator:
Do not fork.
Clone the official private repo directly after accepting the collaborator invite.
Work on branches.
Open PRs into main.

1. Use upon accepting invite: 
git clone https://github.com/kennywong85/ntu-dsai-t4-netflix-project.git
cd ntu-dsai-t4-netflix-project

2. Then each time before work:
git checkout main
git pull origin main

3. Then create your own branch:
git checkout -b "feature/your-task-name"

4. After edits
git status
git add .
git commit -m "Add short description of your change"
git push origin feature/your-task-name

5. Then open a Pull Requet back into main.