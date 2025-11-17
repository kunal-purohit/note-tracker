import os
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from git import Repo, InvalidGitRepositoryError

app = Flask(__name__)


def get_or_init_repo(directory):
    try:
        repo = Repo(directory)
    except InvalidGitRepositoryError:
        repo = Repo.init(directory)
    return repo


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/read-file", methods=["POST"])
def read_file():
    data = request.get_json()
    path = data.get("path")

    if not path:
        return jsonify({"error": "No path provided"}), 400

    path = path.strip().removeprefix('"').removesuffix('"')
    abs_path = os.path.abspath(path)

    print(f"Reading file: {abs_path}")

    # Create parent directories if they don't exist
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)

    # Create file if it doesn't exist
    if not os.path.exists(abs_path):
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write("")
        print(f"Created new file: {abs_path}")

    try:
        with open(abs_path, "r", encoding="utf-8") as f:
            content = f.read()
        return jsonify({"content": content})
    except FileNotFoundError:
        return jsonify({"error": "File not found"}), 404
    except Exception as e:
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
        dirname = os.path.dirname(abs_path)
        filename = os.path.basename(abs_path)

        # Ensure directory exists
        os.makedirs(dirname, exist_ok=True)

        # Write content to file
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)
        print("Written to file")

        # Git operations
        repo = get_or_init_repo(dirname)
        print("Git repository ready")

        repo.index.add([filename])
        print(f"Added {filename} to staging")

        repo.index.commit(
            f"Update {filename} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        print("Commit created")

        return jsonify({"message": "Success"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
