#!/usr/bin/env python3
"""Compile real state-builder prefixes with simulated RunManager, not game proof.

The MP source prefix includes initialization and every early return; a source
check rejects new alternate return paths. The separate menu closure suite compiles
the SP menu/FTUE/null-run paths and asserts their response envelopes.
"""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

p = argparse.ArgumentParser()
p.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
a = p.parse_args()
# SP menu/FTUE/null-run coverage lives in test_menu_closure; MP popup names and
# envelope/action agreement are compiled in test_multiplayer_popup_state.
subprocess.run([__import__('sys').executable, str(a.repo / 'scripts/test_menu_closure.py'), '--repo', str(a.repo)], check=True)
methods = []
for filename, name, boundary, expected_returns in [
    ('McpMod.MultiplayerState.cs', 'BuildMultiplayerGameState', '// Multiplayer metadata', 4),
]:
    source = (a.repo / filename).read_text()
    start = source.index('    private static Dictionary<string, object?> ' + name + '()')
    end = source.index('\n    private static ', start + 20)
    method = source[start:end]
    returns = re.findall(r'\breturn\s+([^;]+);', method)
    assert returns == ['result', 'result', 'result', 'WithStateEnvelope(ftueState, "multiplayer_state")', 'result'], (name, returns)
    prefix = method[:method.index(boundary)]
    methods.append(prefix + 'return result;\n    }\n')

stubs = '''
using System; using System.Collections.Generic;
namespace Godot {class SceneTree {public object? Root;} static class Engine {public static object? GetMainLoop()=>null;}}
class NetType { public bool Multiplayer = true; public bool IsMultiplayer() => Multiplayer; }
class Network { public NetType Type = new(); }
class RunManager {
 public static RunManager Instance = new();
 public bool IsInProgress; public object? State; public Network NetService = new();
 public object? DebugOnlyGetState() => State;
}
class Test {
 static Dictionary<string,object?>? BuildVisibleFtueState(object root)=>null;
 static Dictionary<string,object?> WithStateEnvelope(Dictionary<string,object?> s,string k)=>s;
'''
tests = '''
 static int count;
 static void Check(bool b, string name) { count++; if (!b) throw new Exception(name); }
 static void Verify(Dictionary<string,object?> data, string kind, string? state) {
  Check((string?)data["status"] == "ok", kind + " status");
  Check((string?)data["kind"] == kind, kind + " kind");
  if (state != null) Check((string?)data["state_type"] == state, kind + " state");
 }
 static void Main() {
  Verify(BuildMultiplayerGameState(), "multiplayer_state", "menu");
  RunManager.Instance.IsInProgress = true;
  Verify(BuildMultiplayerGameState(), "multiplayer_state", "unknown");
  RunManager.Instance.State = new object();
  RunManager.Instance.NetService.Type.Multiplayer = false;
  Verify(BuildMultiplayerGameState(), "multiplayer_state", "error");
  Check(((string)BuildMultiplayerGameState()["message"]!).Contains("singleplayer"), "wrong-mode guidance retained");
  RunManager.Instance.NetService.Type.Multiplayer = true;
  Verify(BuildMultiplayerGameState(), "multiplayer_state", null);
  Console.WriteLine($"PASS: {count} extracted state-envelope checks (simulated run state)");
 }
}
'''
dotnet = shutil.which('dotnet')
if not dotnet:
    raise SystemExit('The .NET 9 SDK is required on PATH')
sdk = Path(dotnet).resolve().parent
compiler = sorted((sdk / 'sdk').glob('9.*/Roslyn/bincore/csc.dll'))[-1]
references = sorted((sdk / 'packs/Microsoft.NETCore.App.Ref').glob('9.*/ref/net9.0'))[-1]
with tempfile.TemporaryDirectory(prefix='sts-envelope-test-') as tmp:
    root = Path(tmp)
    program = root / 'Program.cs'
    program.write_text(stubs + '\n'.join(methods) + tests)
    output = root / 'Test.dll'
    subprocess.run([dotnet, str(compiler), '-nologo', '-nullable:enable', '-langversion:12',
                    '-target:exe', f'-out:{output}',
                    *[f'-r:{p}' for p in references.glob('*.dll')], str(program)], check=True)
    (root / 'Test.runtimeconfig.json').write_text(json.dumps({'runtimeOptions': {
        'tfm': 'net9.0', 'framework': {'name': 'Microsoft.NETCore.App', 'version': '9.0.0'}}}))
    subprocess.run([dotnet, str(output)], check=True)
