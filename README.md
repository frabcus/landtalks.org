# Hello World Static Site

A minimal static website hosted on GitHub Pages.

## Setup Instructions

1. Initialize a git repository (if not already done):
   ```bash
   git init
   ```

2. Add and commit your files:
   ```bash
   git add .
   git commit -m "Initial commit: Hello World site"
   ```

3. Create a new repository on GitHub (at github.com/new)

4. Add the remote and push:
   ```bash
   git remote add origin https://github.com/YOUR_USERNAME/landtalks.org.git
   git branch -M main
   git push -u origin main
   ```

5. Enable GitHub Pages:
   - Go to your repository on GitHub
   - Navigate to Settings > Pages
   - Under "Source", select "Deploy from a branch"
   - Select the "main" branch and "/ (root)" folder
   - Click Save

6. Your site will be live at: `https://YOUR_USERNAME.github.io/landtalks.org/`

## Files

- `index.html` - The main page displaying "Hello World"
- `README.md` - This file with setup instructions
