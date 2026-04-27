Lab and practice files for Agentic AI & Prompt Engineering Class!

## VS Code Setup

### Recommended extensions
- Microsoft Python (ms-python.python)
- Jupyter (ms-toolsai.jupyter)
- Check that python was properly installed => run the terminal command: python3 --version

### Create and activate the virtual environment (for editable install)
- macOS/Linux: `python3 -m venv .venv && source venv/bin/activate`
- Windows (PowerShell): `python -m venv .venv; .\venv\Scripts\Activate.ps1`
- Then install the project in editable mode: `pip install -e .`

### Install dependencies
- Standard: `pip install -r requirements.txt`
- Editable project install (recommended for notebooks/imports): `pip install -e .`

### Configure VS Code to use the venv
- Open the Command Palette → “Python: Select Interpreter” → choose the interpreter inside `.venv`.

### Open the integrated terminal in VS Code
- Terminal → New Terminal
- In the terminal, activate venv if needed: `source venv/bin/activate` (macOS/Linux) or `.\venv\Scripts\Activate.ps1` (Windows PowerShell)


Here is the new section for your `README.md`. I have written it to be clear and safe for beginners, while highlighting the "danger" of the last-resort option.

---

## 🔄 Updating & Managing Changes

Since you are working on a live project, the instructor might occasionally update the core files. If you have made your own changes to those same files, follow these steps to get the updates without losing your work.

### The Recommended Way: "Stash and Pull"
This is the safest way to "tuck away" your homework, download the instructor's updates, and then bring your homework back.

1. **Save your work in a temporary "stash":**
   ```bash
   git stash
   ```
2. **Download the instructor's updates:**
   ```bash
   git pull
   ```
3. **Apply your saved work back onto the new code:**
   ```bash
   git stash pop
   ```

> **Note on Merge Conflicts:** If you and the instructor edited the **exact same line**, Git will be confused. In VS Code, the text will turn green and blue. Simply click **"Accept Both Changes"** to keep both versions, or choose the one you prefer.

---

### Last resort trick to resolve git conflicts
If your Git gets into a "mess" and you can't seem to pull the latest changes, or if you simply want to delete all your experiments and start fresh with the instructor's latest version, use this command.

**⚠️ WARNING:** This will **permanently delete** any changes you have made that haven't been committed. There is no "Undo" for this command.

```bash
# 1. Download the latest data from GitHub (without merging yet)
git fetch origin

# 2. Force your local files to match the instructor's 'main' exactly
git reset --hard origin/main
```

**Use this if:**
* You are stuck in a "Merge Conflict" loop you can't solve.
* You accidentally deleted a file and want it back.
* You want to reset your project to the exact state of the master repository.