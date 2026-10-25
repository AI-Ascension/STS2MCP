#!/usr/bin/env python3
"""Bridge-only contract tests. All HTTP calls use MockTransport; no game needed."""
import asyncio
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_mcp_server import _load_server_module


async def test_restored_read_routes():
    server = _load_server_module()
    seen = []

    def handler(request):
        seen.append((request.method, request.url.path, dict(request.url.params)))
        assert request.headers['authorization'] == 'Bearer fixture-token'
        return httpx.Response(200, json={'status': 'ok', 'path': request.url.path})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), headers={'Authorization': 'Bearer fixture-token'}) as client:
        server._http = client
        cases = [
            ('get_api_index', '/', {}),
            ('get_settings', '/api/v1/settings', {}),
            ('get_profile', '/api/v1/profile', {}),
            ('get_compendium', '/api/v1/compendium', {}),
            ('get_bestiary', '/api/v1/bestiary', {}),
            ('get_glossary_cards', '/api/v1/glossary/cards', {}),
            ('get_glossary_relics', '/api/v1/glossary/relics', {}),
            ('get_glossary_potions', '/api/v1/glossary/potions', {}),
            ('get_glossary_keywords', '/api/v1/glossary/keywords', {}),
            ('list_profiles', '/api/v1/profiles', {}),
            ('list_snapshots', '/api/v1/snapshots', {}),
            ('search_wiki', '/api/v1/wiki', {'query': 'silver spoon', 'item_type': 'relic', 'limit': 3}),
        ]
        for name, path, arguments in cases:
            result = json.loads(await getattr(server, name)(**arguments))
            assert result == {'status': 'ok', 'path': path}
            assert seen[-1][:2] == ('GET', path)
        assert seen[-1][2] == {'query': 'silver spoon', 'item_type': 'relic', 'limit': '3'}


async def test_snapshot_payloads_and_structured_failures():
    server = _load_server_module()
    seen = []

    def handler(request):
        seen.append((request.method, request.url.path, json.loads(request.content)))
        return httpx.Response(409, json={'status': 'error', 'error': 'Run active', 'error_code': 'run_in_progress', 'detail': {'retry': False}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        server._http = client
        for call, body in [(server.create_snapshot, {'action': 'create'}), (lambda: server.resume_snapshot('fixture-id'), {'action': 'resume', 'snapshot_id': 'fixture-id'})]:
            payload = json.loads(await call())
            assert payload['error_code'] == 'run_in_progress'
            assert payload['http_status'] == 409
            assert payload['detail'] == {'retry': False}
            assert seen[-1] == ('POST', '/api/v1/snapshots', body)
        assert len(seen) == 2, 'non-menu conflicts must not trigger retries'


def test_error_shape_fallbacks():
    server = _load_server_module()
    for body in [b'not json', b'[]', b'null', b'{"status":"ok"}']:
        response = httpx.Response(502, content=body, request=httpx.Request('GET', 'http://localhost/'))
        error = httpx.HTTPStatusError('fixture', request=response.request, response=response)
        assert server._handle_error(error).startswith('Error: HTTP 502')
    response = httpx.Response(400, json={'status': 'error', 'error': 'bad', 'http_status': 422}, request=httpx.Request('GET', 'http://localhost/'))
    error = httpx.HTTPStatusError('fixture', request=response.request, response=response)
    assert json.loads(server._handle_error(error))['http_status'] == 422


def test_cli_configuration():
    server = _load_server_module()
    original_argv = sys.argv
    seen = []
    try:
        server._get_client = lambda: seen.append((server._base_url, server._trust_env))
        server.mcp.run = lambda **kwargs: seen.append(kwargs)
        sys.argv = ['server.py', '--host', '127.0.0.2', '--port', '15527', '--no-trust-env']
        server.main()
        assert seen == [('http://127.0.0.2:15527', False), {'transport': 'stdio'}]
    finally:
        sys.argv = original_argv



async def test_profile_restart_warning_is_preserved():
    server = _load_server_module()
    calls = []
    async def no_delay(_):
        pass
    server.asyncio = SimpleNamespace(sleep=no_delay)
    async def profiles_get():
        calls.append("get")
        return json.dumps({"current_profile_id": 2, "profiles": []})
    server._profiles_get = profiles_get
    for initial in [
        {"status": "ok", "message": "Switched to profile 2 (requires restart)", "current_profile_id": 2},
        {"status": "ok", "message": "Restart before continuing", "requires_restart": True, "current_profile_id": 2},
    ]:
        async def profiles_post(body):
            assert body == {"action": "switch", "profile_id": 2}
            return json.dumps(initial)
        server._profiles_post = profiles_post
        result = json.loads(await server.switch_profile(2))
        assert result == {**initial, "requires_restart": True}
        assert not calls, "profile ID polling cannot prove restart-required data reloaded"
    initial = {"status": "ok", "message": "Switch requested for profile 2 (via UI)", "warning": "fixture warning", "target_profile_id": 2}
    result = json.loads(await server._wait_for_profile(2, json.dumps(initial)))
    assert result["message"] == initial["message"]
    assert result["warning"] == "fixture warning"
    assert result["current_profile_id"] == 2 and calls == ["get"]

if __name__ == '__main__':
    asyncio.run(test_restored_read_routes())
    asyncio.run(test_snapshot_payloads_and_structured_failures())
    test_error_shape_fallbacks()
    test_cli_configuration()
    asyncio.run(test_profile_restart_warning_is_preserved())
    print('PASS: restored read routes, snapshot payload/errors, error fallbacks, CLI proxy/host/port contracts')
