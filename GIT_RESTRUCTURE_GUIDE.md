# Git History Restructure Guide

## Overview

This guide will help you restructure your BharatDoc repository from a single commit into 8 logical commits that tell the story of how the project was built.

---

## ⚠️ IMPORTANT: Backup First

Before running these commands, ensure you have a backup:

```bash
# Create a backup branch
git branch backup-original-commit
```

---

## 📋 The 8 Logical Commits

Your git history will be restructured into these commits:

1. **Schemas & Dependencies** - Define data models and pin dependencies
2. **Data Pipeline** - Synthetic data generation and augmentation
3. **Training** - LoRA fine-tuning scripts for all models
4. **Inference** - FastAPI server with batching and circuit breaker
5. **Router & Gateway** - CLIP classifier and API gateway
6. **Evaluation & Monitoring** - Metrics, Prometheus, Grafana
7. **Feedback & MLflow** - Active learning loop and model registry
8. **Apps & Deployment** - Streamlit apps, Docker, tests, docs

---

## 🚀 Step-by-Step Instructions

### Step 1: Navigate to Your Repository

```bash
cd C:\Users\91958\OneDrive\Desktop\BharatDoc
```

### Step 2: Verify Current State

```bash
git log --oneline
git status
```

You should see one commit with all files.

### Step 3: Run the Restructure Commands

Open the file `GIT_RESTRUCTURE_COMMANDS.txt` and run each command one by one.

**OR** run this single command to execute all at once:

```bash
# On Windows PowerShell
Get-Content GIT_RESTRUCTURE_COMMANDS.txt | ForEach-Object { Invoke-Expression $_ }
```

```bash
# On Windows CMD
for /f "delims=" %i in (GIT_RESTRUCTURE_COMMANDS.txt) do %i
```

```bash
# On Git Bash / Linux / Mac
bash GIT_RESTRUCTURE_COMMANDS.txt
```

### Step 4: Verify the New History

```bash
git log --oneline
```

You should now see 8 commits with meaningful messages.

### Step 5: Update README

```bash
# Backup old README
copy README.md README_OLD.md

# Replace with new README
copy README_NEW.md README.md

# Commit the README update
git add README.md
git commit --amend --no-edit

# Force push again
git push origin main --force
```

---

## 🔍 What Each Command Does

### Command 1: Reset the commit
```bash
git reset --soft HEAD~1
```
Undoes the last commit but keeps all changes staged.

### Command 2: Unstage everything
```bash
git reset HEAD .
```
Unstages all files so you can selectively stage them.

### Commands 3-18: Selective commits
Each pair of commands:
1. `git add <files>` - Stage specific files
2. `git commit -m "..."` - Commit with meaningful message

### Command 19: Force push
```bash
git push origin main --force
```
Overwrites the remote history with your new commits.

---

## ⚠️ Force Push Warning

**IMPORTANT**: `git push --force` will overwrite the remote history. Only do this if:

- ✅ You are the only contributor
- ✅ No one else has cloned the repository
- ✅ You have a backup branch
- ✅ You understand the consequences

If others have cloned your repo, coordinate with them first!

---

## 🎯 Expected Result

After running all commands, your git history will look like this:

```
* feat: add Streamlit apps, Docker deployment, test suite, documentation
* feat: add active learning feedback loop and MLflow model registry
* feat: add evaluation metrics, Prometheus monitoring, Grafana dashboard
* feat: add CLIP classifier router and API gateway
* feat: add FastAPI inference server with batching and circuit breaker
* feat: add LoRA fine-tuning scripts for Donut, LayoutLMv3, TrOCR
* feat: add synthetic data generation and augmentation pipeline
* feat: define Pydantic schemas for Indian document types
```

---

## 🔄 Rollback Plan

If something goes wrong:

```bash
# Switch back to backup branch
git checkout backup-original-commit

# Force push the backup to main
git push origin backup-original-commit:main --force

# Switch back to main
git checkout main
git pull
```

---

## ✅ Verification Checklist

After restructuring:

- [ ] Run `git log --oneline` and verify 8 commits
- [ ] Check each commit: `git show <commit-hash>`
- [ ] Verify files in each commit match the plan
- [ ] Push to GitHub: `git push origin main --force`
- [ ] Check GitHub repository to see new commit history
- [ ] Verify README displays correctly on GitHub
- [ ] Delete backup branch if satisfied: `git branch -D backup-original-commit`

---

## 📝 Commit Message Format

Each commit follows this format:

```
feat: <short description>

- <detail 1>
- <detail 2>
- <detail 3>
- <detail 4>
- <detail 5>
```

This format:
- Uses conventional commits (`feat:` prefix)
- Has a clear, concise title
- Includes 5 bullet points explaining what was added
- Tells a story of incremental development

---

## 🎓 Why This Matters

A well-structured git history:

1. **Shows your thought process** - Demonstrates how you approached the problem
2. **Makes code review easier** - Reviewers can understand changes incrementally
3. **Helps with debugging** - `git bisect` works better with logical commits
4. **Looks professional** - Shows you understand version control best practices
5. **Tells a story** - Each commit is a chapter in your project's development

---

## 📚 Additional Resources

- [Conventional Commits](https://www.conventionalcommits.org/)
- [Git Rewriting History](https://git-scm.com/book/en/v2/Git-Tools-Rewriting-History)
- [How to Write a Git Commit Message](https://chris.beams.io/posts/git-commit/)

---

## 🆘 Troubleshooting

### "fatal: refusing to merge unrelated histories"
```bash
git pull origin main --allow-unrelated-histories
```

### "error: failed to push some refs"
This is expected. Use `--force` flag as shown in the commands.

### "Your branch and 'origin/main' have diverged"
This is expected after rewriting history. Use `git push --force`.

### Commands not working on Windows
Use Git Bash instead of CMD or PowerShell for better compatibility.

---

**Status**: Ready to execute
**Estimated Time**: 5-10 minutes
**Risk Level**: Medium (requires force push)
**Backup Required**: Yes (create backup branch first)
