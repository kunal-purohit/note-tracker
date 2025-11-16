import os
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from git import Repo, InvalidGitRepositoryError

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security: Define allowed base directory (change this to your preference)
ALLOWED_BASE_DIR = os.path.expanduser("~/Documents/notes")

# Create the directory if it doesn't exist
os.makedirs(ALLOWED_BASE_DIR, exist_ok=True)


def is_safe_path(path):
    """Check if the path is within the allowed directory."""
    abs_path = os.path.abspath(path)
    allowed_abs = os.path.abspath(ALLOWED_BASE_DIR)
    return abs_path.startswith(allowed_abs)


def get_or_init_repo(directory):
    """Get existing repo or initialize a new one."""
    try:
        repo = Repo(directory)
        logger.info(f"Using existing repository at {directory}")
    except InvalidGitRepositoryError:
        repo = Repo.init(directory)
        logger.info(f"Initialized new repository at {directory}")
    return repo


@app.route("/")
def index():
    return render_template("index.html", allowed_dir=ALLOWED_BASE_DIR)


@app.route("/read-file", methods=["POST"])
def read_file():
    data = request.get_json()
    path = data.get("path")

    if not path:
        return jsonify({"error": "No path provided"}), 400

    path = path.strip().removeprefix('"').removesuffix('"')
    abs_path = os.path.abspath(path)

    # Security check
    if not is_safe_path(abs_path):
        return jsonify({"error": f"Path must be within {ALLOWED_BASE_DIR}"}), 403

    logger.info(f"Reading file: {abs_path}")

    # Create parent directories if they don't exist
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)

    # Create file if it doesn't exist
    if not os.path.exists(abs_path):
        try:
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write("")
            logger.info(f"Created new file: {abs_path}")
        except Exception as e:
            logger.error(f"Error creating file: {e}")
            return jsonify({"error": f"Could not create file: {str(e)}"}), 500

    try:
        with open(abs_path, "r", encoding="utf-8") as f:
            content = f.read()
        return jsonify({"content": content, "path": abs_path})
    except FileNotFoundError:
        return jsonify({"error": "File not found"}), 404
    except Exception as e:
        logger.error(f"Error reading file: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/file-updated", methods=["POST"])
def update_file():
    try:
        data = request.get_json()
        path = data.get("path")
        content = data.get("content")

        if not path:
            return jsonify({"error": "No path provided"}), 400

        path = path.strip().removeprefix('"').removesuffix('"')
        abs_path = os.path.abspath(path)

        # Security check
        if not is_safe_path(abs_path):
            return jsonify({"error": f"Path must be within {ALLOWED_BASE_DIR}"}), 403

        dirname = os.path.dirname(abs_path)
        filename = os.path.basename(abs_path)

        # Ensure directory exists
        os.makedirs(dirname, exist_ok=True)

        # Write content to file
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"Written to file: {abs_path}")

        # Git operations
        repo = get_or_init_repo(dirname)

        # Add file to staging
        repo.index.add([filename])
        logger.info(f"Added {filename} to staging")

        # Create commit with better message
        commit_message = (
            f"Update {filename} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        repo.index.commit(commit_message)
        logger.info(f"Commit created: {commit_message}")

        return jsonify({"message": "File saved and committed successfully"}), 200
    except Exception as e:
        logger.error(f"Error updating file: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/get-history", methods=["POST"])
def get_history():
    """Get commit history for a file's directory."""
    try:
        data = request.get_json()
        path = data.get("path")

        if not path:
            return jsonify({"error": "No path provided"}), 400

        path = path.strip().removeprefix('"').removesuffix('"')
        abs_path = os.path.abspath(path)

        # Security check
        if not is_safe_path(abs_path):
            return jsonify({"error": f"Path must be within {ALLOWED_BASE_DIR}"}), 403

        dirname = os.path.dirname(abs_path)

        # Check if git repo exists
        try:
            repo = Repo(dirname)
        except InvalidGitRepositoryError:
            return jsonify({"commits": [], "message": "No git history yet"}), 200

        commits = []
        for commit in repo.iter_commits(max_count=20):
            commits.append(
                {
                    "message": commit.message.strip(),
                    "date": commit.committed_datetime.strftime("%Y-%m-%d %H:%M:%S"),
                    "sha": commit.hexsha[:7],
                    "author": str(commit.author),
                }
            )

        return jsonify({"commits": commits})
    except Exception as e:
        logger.error(f"Error getting history: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
