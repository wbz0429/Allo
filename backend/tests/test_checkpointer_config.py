import os

from deerflow.config.checkpointer_config import load_checkpointer_config_from_dict


def test_load_checkpointer_config_uses_checkpoint_postgres_uri_env(monkeypatch):
    monkeypatch.setenv("CHECKPOINT_POSTGRES_URI", "postgresql://user:pass@localhost:5432/checkpoints")

    load_checkpointer_config_from_dict({"type": "postgres"})

    from deerflow.config.checkpointer_config import get_checkpointer_config

    config = get_checkpointer_config()
    assert config is not None
    assert config.connection_string == os.environ["CHECKPOINT_POSTGRES_URI"]
