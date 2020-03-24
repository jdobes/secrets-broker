import sys
import logging

from apscheduler.schedulers.background import BackgroundScheduler
import connexion
from peewee import SQL

from .api import ALLOWED_GITHUB_REPOS, ALLOWED_GITHUB_ORGS, ALLOWED_GITHUB_USERS
from .model import init_schema, SecretsRequest

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def delete_old_requests():
    query = SecretsRequest.delete().where(SecretsRequest.created < SQL("datetime('now', '-30 seconds')"))
    deleted = query.execute()
    if deleted:
        logger.info("%s expired request(s) deleted.", deleted)


def main():
    logging.basicConfig(format="%(asctime)s:%(levelname)s:%(name)s:%(message)s")

    if not ALLOWED_GITHUB_REPOS:
        logger.critical("No allowed GitHub repos defined!")
        sys.exit(1)
    
    if not ALLOWED_GITHUB_ORGS and not ALLOWED_GITHUB_USERS:
        logger.critical("No allowed GitHub orgs or users defined!")
        sys.exit(1)

    init_schema()

    sched = BackgroundScheduler(daemon=True)
    sched.add_job(delete_old_requests, 'interval', [], seconds=10)
    sched.start()
    logger.info("Delete scheduler enabled.")

    app = connexion.FlaskApp(__name__, options={"swagger_ui": True, "swagger_url": "/api/v1",
                                                "openapi_spec_path": "/api/v1/openapi.json"})
    app.add_api('openapi.spec.yml', validate_responses=True, strict_validation=True)

    @app.app.after_request
    def set_default_headers(response): # pylint: disable=unused-variable
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Access-Control-Allow-Headers"
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        return response

    app.run(host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
