import os
from datetime import datetime
import uuid
import json
from io import BytesIO
from zipfile import ZipFile

import connexion
import requests

from .log import get_logger
from .model import SecretsRequest

LOGGER = get_logger(__name__)

ALLOWED_GITHUB_REPOS = [repo.strip() for repo in os.getenv("ALLOWED_GITHUB_REPOS", "jdobes/secrets-broker").split(",") if repo.strip()]
ALLOWED_GITHUB_ORGS = [org.strip() for org in os.getenv("ALLOWED_GITHUB_ORGS", "").split(",") if org.strip()]
ALLOWED_GITHUB_USERS = [user.strip() for user in os.getenv("ALLOWED_GITHUB_USERS", "jdobes").split(",") if user.strip()]

SECRETS = json.loads(os.getenv("SECRETS", "{}"))

GITHUB_API = "https://api.github.com"
GITHUB_API_RUN_ENDPOINT = "/repos/%s/actions/runs/%s"
GITHUB_API_ARTIFACT_ENDPOINT = "/repos/%s/actions/runs/%s/artifacts"
GITHUB_API_USER_ORGS_ENDPOINT = "/users/%s/orgs"


def initialize():
    run_id = connexion.request.headers["x-run-id"]
    repo = connexion.request.headers["x-github-repo"]
    gh_token = connexion.request.headers["x-github-token"]

    if repo not in ALLOWED_GITHUB_REPOS:
        return {"error": "GitHub repo not specified or allowed."}, 403

    secrets_request = SecretsRequest.get_or_none((SecretsRequest.run_id == run_id) & (SecretsRequest.repo == repo))
    if secrets_request:
        return {"error": "Repo & Run ID already initialized."}, 409

    token = uuid.uuid4().hex
    LOGGER.debug("storing: repo=%s, run_id=%s, gh_token=%s, validation_token=%s", repo, run_id, gh_token, token)
    record = SecretsRequest(repo=repo, run_id=run_id, gh_token=gh_token, validation_token=token, created=datetime.now())
    record.save()
    return {"validation_token": token}


def secrets():
    run_id = connexion.request.headers["x-run-id"]
    repo = connexion.request.headers["x-github-repo"]
    gh_token = connexion.request.headers["x-github-token"]

    if repo not in ALLOWED_GITHUB_REPOS:
        return {"error": "GitHub repo not specified or allowed."}, 403
    
    secrets_request = SecretsRequest.get_or_none((SecretsRequest.run_id == run_id) & 
                                                 (SecretsRequest.repo == repo) &
                                                 (SecretsRequest.gh_token == gh_token))
    if not secrets_request:
        return {"error": "Secrets request not initialized."}, 403

    # check github API about action run initiator
    response = requests.get("%s%s" % (GITHUB_API, GITHUB_API_RUN_ENDPOINT % (repo, run_id)),
                            headers={"Authorization": "token %s" % gh_token})
    if response.status_code != 200:
        LOGGER.debug("Invalid HTTP code from Github: %s", response.status_code)
        return {"error": "Validation failed."}, 403
    run_detail = response.json()
    head_repository_name = run_detail["head_repository"]["full_name"]
    owner_login = run_detail["head_repository"]["owner"]["login"]
    owner_type = run_detail["head_repository"]["owner"]["type"].lower()
    if head_repository_name == repo:
        LOGGER.debug("Initiator's head repo is allowed repo: %s", repo)
    elif owner_type == "user" and owner_login in ALLOWED_GITHUB_USERS:
        LOGGER.debug("Initiator's head repo owner is in allowed users: %s.", owner_login)
    elif owner_type == "organization" and owner_login in ALLOWED_GITHUB_ORGS:
        LOGGER.debug("Initiator's head repo owner is in allowed orgs: %s.", owner_login)
    elif owner_type == "user":  # check user's org
        response = requests.get("%s%s" % (GITHUB_API, GITHUB_API_USER_ORGS_ENDPOINT % (owner_login)),
                                headers={"Authorization": "token %s" % gh_token})
        if response.status_code != 200:
            LOGGER.debug("Invalid HTTP code from Github: %s", response.status_code)
            return {"error": "Validation failed."}, 403
        org_list = response.json()
        valid_orgs = [org["login"] for org in org_list if org["login"] in ALLOWED_GITHUB_ORGS]
        if not valid_orgs:
            LOGGER.debug("Initiator's head repo owner is NOT a member of allowed orgs: %s.", owner_login)
            return {"error": "Validation failed."}, 403
        LOGGER.debug("Initiator's head repo owner is a member of allowed orgs: %s.", owner_login)
    else:
        LOGGER.debug("Permission denied for owner: login=%s, type=%s.", owner_login, owner_type)
        return {"error": "Validation failed."}, 403

    # check token in artifacts
    response = requests.get("%s%s" % (GITHUB_API, GITHUB_API_ARTIFACT_ENDPOINT % (repo, run_id)),
                            #allow_redirects=True,
                            headers={"Authorization": "token %s" % gh_token})
    if response.status_code != 200:
        LOGGER.debug("Invalid HTTP code from Github: %s", response.status_code)
        return {"error": "Validation failed."}, 403
    
    artifacts = response.json()
    for a in artifacts.get("artifacts", []):
        LOGGER.debug(a["name"])
    artifacts_download_urls = [artifact["archive_download_url"] for artifact in artifacts.get("artifacts", []) if artifact["name"] == "validation_token"]
    if not artifacts_download_urls:
        LOGGER.debug("No artifact found")
        return {"error": "Validation failed."}, 403
    
    artifacts_download_url = artifacts_download_urls[0]

    #zipfile = ZipFile(BytesIO(response.content))
    #for zip_file in zipfile.namelist():
    #    LOGGER.debug(zip_file)

    LOGGER.debug("Permission granted: login=%s, type=%s.", owner_login, owner_type)
    requested_keys = [key.strip() for key in connexion.request.args["keys"].split(",") if key.strip()]
    return [{"key": key, "value": SECRETS[key]} for key in requested_keys if key in SECRETS]
