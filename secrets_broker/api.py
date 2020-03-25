import os
from datetime import datetime
import uuid
import json

import connexion

from .log import get_logger
from .model import SecretsRequest

LOGGER = get_logger(__name__)

ALLOWED_GITHUB_REPOS = [repo.strip() for repo in os.getenv("ALLOWED_GITHUB_REPOS", "jdobes/secrets-broker").split(",") if repo.strip()]
ALLOWED_GITHUB_ORGS = [org.strip() for org in os.getenv("ALLOWED_GITHUB_ORGS", "").split(",") if org.strip()]
ALLOWED_GITHUB_USERS = [user.strip() for user in os.getenv("ALLOWED_GITHUB_USERS", "jdobes").split(",") if user.strip()]

SECRETS = json.loads(os.getenv("SECRETS", "{}"))

def initialize():
    try:
        run_id = int(connexion.request.headers.get("x-run-id", "?"))
    except ValueError:
        return {"error": "Run ID missing or invalid."}, 400

    repo = connexion.request.headers.get("x-github-repo", "?")
    if repo not in ALLOWED_GITHUB_REPOS:
        return {"error": "GitHub repo not specified or allowed."}, 403

    secrets_request = SecretsRequest.get_or_none((SecretsRequest.run_id == run_id) & (SecretsRequest.repo == repo))
    if secrets_request:
        return {"error": "Repo & Run ID already initialized."}, 409

    gh_token = connexion.request.headers.get("x-github-token", "?")
    token = uuid.uuid4().hex
    LOGGER.info("Received initialization request from repo: %s (run ID %s)", repo, run_id)
    LOGGER.debug("storing: repo=%s, run_id=%s, gh_token=%s, validation_token=%s", repo, run_id, gh_token, token)
    record = SecretsRequest(repo=repo, run_id=run_id, gh_token=gh_token, validation_token=token, created=datetime.now())
    record.save()
    response = {"validation_token": token}
    return response
