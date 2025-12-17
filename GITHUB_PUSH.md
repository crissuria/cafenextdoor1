# Push to GitHub - Quick Guide

## If you already have a GitHub repository:

Replace `YOUR_USERNAME` and `YOUR_REPO_NAME` with your actual GitHub username and repository name, then run:

```bash
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git branch -M main
git push -u origin main
```

## If you need to create a repository:

1. Go to https://github.com/new
2. Repository name: `cafenextdoor` (or any name you prefer)
3. Description: "Cafe Next Door - Flask Web Application"
4. Choose Public or Private
5. **DO NOT** check "Initialize with README" (we already have files)
6. Click "Create repository"
7. Copy the repository URL
8. Run the commands above with your repository URL

## Example:

If your username is `cristiansudaria` and repo is `cafenextdoor`:

```bash
git remote add origin https://github.com/cristiansudaria/cafenextdoor.git
git branch -M main
git push -u origin main
```

## Authentication:

GitHub may ask for authentication:
- **Personal Access Token** (recommended) - Create at: https://github.com/settings/tokens
- Or use GitHub CLI: `gh auth login`

## After Pushing:

Your code will be on GitHub! You can then:
- Deploy directly from GitHub to Railway/Render
- Share the repository
- Continue development with version control


