from environ.environ import Env


ORACLE_DESCRIPTOR = (
    "(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST=db.example.com)(PORT=1521))"
    "(CONNECT_DATA=(SERVICE_NAME=orclpdb1)))"
)
ORACLE_DESCRIPTOR_URL = f"oracle://user:password@{ORACLE_DESCRIPTOR}"


def test_db_url_config_treats_pathless_oracle_descriptor_as_decoded_name():
    config = Env.db_url_config(ORACLE_DESCRIPTOR_URL)

    assert config["NAME"] == ORACLE_DESCRIPTOR
    assert config["NAME"].startswith("(DESCRIPTION=")
    assert "%28DESCRIPTION" not in config["NAME"]


def test_db_url_config_leaves_host_empty_for_pathless_oracle_descriptor():
    config = Env.db_url_config(ORACLE_DESCRIPTOR_URL)

    assert config["HOST"] == ""


def test_db_url_reads_pathless_oracle_descriptor_from_environment(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", ORACLE_DESCRIPTOR_URL)

    config = Env().db_url()

    assert config["NAME"] == ORACLE_DESCRIPTOR
    assert config["HOST"] == ""


def test_db_url_config_still_parses_standard_oracle_urls():
    config = Env.db_url_config(
        "oracle://user:password@db.example.com:1521/orclpdb1"
    )

    assert isinstance(config, dict)
    assert config["ENGINE"] == "django.db.backends.oracle"
    assert config["NAME"] == "orclpdb1"
    assert config["HOST"] == "db.example.com"
