from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_prod_compose_keeps_browser_relay_private():
    compose = (ROOT / "deploy/ecs/compose.prod.yml").read_text(encoding="utf-8")

    assert "${HOST_API_BIND:-127.0.0.1}:${HOST_API_PORT:-18000}:8000" in compose
    assert "${HOST_NOVNC_BIND:-127.0.0.1}:${HOST_NOVNC_PORT:-6080}:6080" in compose
    assert "ATTACH_ON_START: ${ATTACH_ON_START:-false}" in compose
    assert "${HOST_BROWSER_DATA_DIR:-/root/browser-ai-relay-data/browser_data}:/app/browser_data" in compose
    assert "${HOST_LOGS_DIR:-/root/browser-ai-relay-data/logs}:/app/logs" in compose


def test_release_workflow_builds_and_deploys_browser_relay_image():
    workflow = (ROOT / ".github/workflows/release-deploy.yml").read_text(encoding="utf-8")

    assert "ghcr.io/${{ github.repository_owner }}/browser-ai-relay:${TAG}" in workflow
    assert "deploy/ecs/deploy.sh" in workflow
    assert "ECS_HOST" in workflow
    assert "ECS_SSH_KEY" in workflow


def test_release_meta_example_documents_required_private_values():
    example = (ROOT / "deploy/ecs/release-meta.env.example").read_text(encoding="utf-8")

    for key in (
        "GHCR_BASE=",
        "API_TOKEN=",
        "VNC_PASSWORD=",
        "HOST_API_PORT=18000",
        "HOST_NOVNC_PORT=6080",
        "ATTACH_ON_START=false",
    ):
        assert key in example
