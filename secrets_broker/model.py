from peewee import SqliteDatabase, Model, TextField, DateTimeField

sqlite_db = SqliteDatabase("/tmp/sb.db", pragmas={"journal_mode": "wal",
                                                  "foreign_keys": 1})


class BaseModel(Model):
    """A base model that will use our Sqlite database."""
    class Meta:
        database = sqlite_db


class SecretsRequest(BaseModel):
    repo = TextField(null=False)
    actions_id = TextField(null=False)
    gh_token = TextField(null=False)
    validation_token = TextField(null=False)
    created = DateTimeField(null=False)

    class Meta:
        indexes = (
            # create a unique index
            (('repo', 'actions_id'), True),
        )


def init_schema():
    sqlite_db.create_tables([SecretsRequest])
