from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_prod_compose_keeps_browser_relay_private():
    compose = (ROOT / "deploy/ecs/compose.prod.yml").read_text(encoding="utf-8")

    assert "${HOST_API_BIND:-127.0.0.1}:${HOST_API_PORT:-18000}:8000" in compose
    assert "${HOST_NOVNC_BIND:-127.0.0.1}:${HOST_NOVNC_PORT:-6080}:6080" in compose
    assert "ATTACH_ON_START: ${ATTACH_ON_START:-false}" in compose
    assert "${HOST_BROWSER_DATA_DIR:-/root/browser-ai-relay-data/browser_data}:/app/browser_data" in compose
    assert "${HOST_LOGS_DIR:-/root/browser-ai-relay-data/logs}:/app/logs" in compose


def test_local_compose_binds_to_loopback_by_default():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "${HOST_API_BIND:-127.0.0.1}:${API_PORT:-8000}:8000" in compose
    assert "${HOST_NOVNC_BIND:-127.0.0.1}:${NOVNC_PORT:-6080}:6080" in compose


def test_release_workflow_builds_and_deploys_browser_relay_image():
    workflow = (ROOT / ".github/workflows/release-deploy.yml").read_text(encoding="utf-8")

    assert "name: browser-ai-relay-release-deploy" in workflow
    assert "ghcr.io/${{ github.repository_owner }}/browser-ai-relay:${TAG}" in workflow
    assert "deploy/ecs/deploy.sh" in workflow
    assert "ECS_HOST" in workflow
    assert "ECS_SSH_KEY" in workflow
    assert "Resetting tracked files to origin/main" in workflow
    assert "git reset --hard origin/main" in workflow
    assert "git pull --ff-only origin main" not in workflow


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

    assert "API_TOKEN=replace_with_long_random_api_token" in example
    assert "VNC_PASSWORD=changeme" in example
    assert "VNC_PASSWORD=replace_with_strong_vnc_password" not in example


def test_runtime_example_uses_short_vnc_password():
    example = (ROOT / "deploy/ecs/runtime.env.example").read_text(encoding="utf-8")

    assert "VNC_PASSWORD=changeme" in example
    assert "API_TOKEN=replace_with_long_random_api_token" in example


def test_deploy_scripts_use_explicit_compose_project_name():
    for path in (ROOT / "deploy/ecs").glob("*.sh"):
        text = path.read_text(encoding="utf-8")
        if "docker compose" in text:
            assert '-p "${COMPOSE_PROJECT_NAME:-browser-ai-relay}"' in text, path.name


def test_deploy_script_migrates_old_compose_project_container():
    deploy = (ROOT / "deploy/ecs/deploy.sh").read_text(encoding="utf-8")

    assert "docker inspect browser-ai-relay" in deploy
    assert 'existing_project" != "$COMPOSE_PROJECT_NAME"' in deploy
    assert "docker rm -f browser-ai-relay" in deploy


def test_entrypoint_warns_about_vnc_password_truncation():
    entrypoint = (ROOT / "docker/entrypoint.sh").read_text(encoding="utf-8")

    assert "VNC_PASSWORD is longer than 8 chars" in entrypoint
    assert "${#VNC_PASSWORD}" in entrypoint


def test_troubleshooting_documents_compose_and_vnc_checks():
    troubleshooting = (ROOT / "docs/troubleshooting.md").read_text(encoding="utf-8")

    for required in (
        "ssh -L 6080:127.0.0.1:6080 -L 18000:127.0.0.1:18000 root@ECS_IP",
        "http://127.0.0.1:6080/vnc.html",
        "http://127.0.0.1:18000",
        "docker ps --format 'table {{.Names}}\\t{{.Image}}\\t{{.Ports}}\\t{{.Status}}'",
        "docker inspect browser-ai-relay --format '{{json .Config.Labels}}' | python3 -m json.tool",
        "docker exec browser-ai-relay printenv | grep -E 'VNC_PASSWORD|API_TOKEN|API_PORT|NOVNC_PORT|HOST_API_PORT|HOST_NOVNC_PORT'",
        "docker exec browser-ai-relay tail -n 100 /app/logs/x11vnc.log",
        "com.docker.compose.project",
        "VNC_PASSWORD 如果超过 8 位",
    ):
        assert required in troubleshooting
