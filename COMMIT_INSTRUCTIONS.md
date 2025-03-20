# Commit and Push Instructions

Follow these steps to commit the recent changes and push them to your GitHub repository:

## 1. Initialize Git Repository (if not already done)

```bash
git init
```

## 2. Add All Files to Staging

```bash
git add .
```

## 3. Commit the Changes

```bash
git commit -m "Add interactive multi-agent visualization feature

- Added real-time visualization of agent interactions
- Created multi-agent workflow visualization interface
- Fixed route conflicts between hyphen and underscore URL formats
- Added proper error handling for MCP client initialization
- Updated README with new features and documentation"
```

## 4. Add Remote Repository (if not already set up)

Replace `yourusername` and `yourrepository` with your GitHub username and repository name:

```bash
git remote add origin https://github.com/yourusername/yourrepository.git
```

If you've already set up the remote but need to change it:

```bash
git remote set-url origin https://github.com/yourusername/yourrepository.git
```

## 5. Push Changes to GitHub

```bash
git push -u origin main
```

If your default branch is called "master" rather than "main", use:

```bash
git push -u origin master
```

## 6. Check the Status

```bash
git status
```

This should show you that everything is up to date.

## GitHub Desktop Alternative

If you prefer using GitHub Desktop instead of command line:

1. Open GitHub Desktop
2. Add the local repository (File > Add local repository)
3. Write the commit message in the summary field
4. Click "Commit to main"
5. Click "Push origin" 