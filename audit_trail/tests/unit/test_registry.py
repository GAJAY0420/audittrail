from audit_trail.registry.registry import register_model, registry


def test_registry_register_and_get():
    registry.clear()
    register_model("app.Model", fields=["status"], sensitive=["secret"], m2m=["tags"])
    config = registry.get("app.Model")
    assert config is not None
    assert "status" in config.fields
    assert "secret" in config.sensitive
