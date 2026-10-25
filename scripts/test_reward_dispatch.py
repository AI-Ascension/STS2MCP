#!/usr/bin/env python3
"""Compile actual SP/MP state dispatch with simulated rooms and overlays.
Not a game integration test. Requires a .NET 9 SDK on PATH.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

p = argparse.ArgumentParser()
p.add_argument('--source-root', type=Path, default=Path(__file__).resolve().parents[1])
a = p.parse_args()
methods = []
for filename, method_name in [('McpMod.StateBuilder.cs', 'BuildGameState'), ('McpMod.MultiplayerState.cs', 'BuildMultiplayerGameState')]:
    source = (a.source_root / filename).read_text()
    start = source.index(f'    private static Dictionary<string, object?> {method_name}()')
    end = source.index('    private static ', start + 10)
    extracted = source[start:end]
    if method_name == 'BuildGameState':
        # The full real menu prefix is compiled separately by test_menu_closure.py.
        # This harness tests the actual in-run dispatch, not a reimplementation.
        boundary = extracted.index('        // Card selection overlays')
        extracted = extracted[:extracted.index('        var result =')] + """
        var result = new Dictionary<string,object?>();
        SceneTree? tree = null;
        var runState = RunManager.Instance.DebugOnlyGetState();
""" + extracted[boundary:]
    methods.append(extracted)

stubs = r'''
using System; using System.Collections.Generic;
interface IOverlayScreen { }
class NGameOverScreen : IOverlayScreen { }
class SceneTree { public object? Root; }
namespace Godot { class SceneTree:global::SceneTree {} static class Engine {public static object? GetMainLoop()=>null;} }
class NCharacterSelectScreen { }
class NOverlayStack { public static NOverlayStack Instance = new(); public object? Top; public object? Peek() => Top; }
class NCardGridSelectionScreen : IOverlayScreen { }
class NChooseACardSelectionScreen : IOverlayScreen { }
class NChooseABundleSelectionScreen : IOverlayScreen { }
class NChooseARelicSelection : IOverlayScreen { }
class NCrystalSphereScreen : IOverlayScreen { }
class NRewardsScreen : IOverlayScreen { }
class NCardRewardSelectionScreen : IOverlayScreen { }
class UnknownOverlay : IOverlayScreen { }
class Room { }
class CombatRoom : Room { public string RoomType = "monster"; }
class EventRoom : Room { public object? CanonicalEvent; }
class FakeMerchant { }
class MerchantRoom : Room { }
class MapRoom : Room { }
class RestSiteRoom : Room { }
class TreasureRoom : Room { }
class RunState { public Room? CurrentRoom; public int CurrentActIndex; public int TotalFloor; public int AscensionLevel; public List<object> Players = new(); }
class NetType { public bool IsMultiplayer() => true; }
class NetService { public NetType Type = new(); }
class RunManager { public static RunManager Instance = new(); public bool IsInProgress = true; public RunState State = new(); public NetService NetService = new(); public RunState DebugOnlyGetState() => State; }
class CombatManager { public static CombatManager Instance = new(); public bool IsInProgress; }
class LocalContext { public static object? GetMe(RunState s) => null; }
class NPlayerHand { public static NPlayerHand? Instance; public bool IsInCardSelection; }
class NMapScreen { public static NMapScreen Instance = new(); public bool IsOpen; public bool Visible; }
class Inventory { public bool IsOpen = true; }
class NMerchantRoom { public static NMerchantRoom? Instance; public Inventory Inventory = new(); public void OpenInventory() => Inventory.IsOpen = true; }
class Test {
 static Dictionary<string,object?>? BuildVisibleFtueState(object root)=>null;
 static Dictionary<string,object?> WithStateEnvelope(Dictionary<string,object?> s,string k)=>s;
 static T? FindFirst<T>(object root) where T:class => null;
 static bool IsNodeVisible(object node) => false;
 static void AddCharacterSelectMenuState(Dictionary<string,object?> result, object screen) => throw new Exception("outside in-run dispatch scope");
 static Dictionary<string,object?> BuildActiveRunContext() => new();
 static Dictionary<string,object?> BuildPlayerState(object player) => new();
 static bool IsMapScreenOpenOrVisible() => NMapScreen.Instance.IsOpen || NMapScreen.Instance.Visible;
 static Dictionary<string,object?> Marker(string name) => new() { ["builder"] = name };
'''
for name in ['BuildFakeMerchantState','BuildCardSelectState','BuildChooseCardState','BuildBundleSelectState','BuildRelicSelectState','BuildCrystalSphereState','BuildRewardsState','BuildHandSelectState','BuildBattleState','BuildEventState','BuildShopState','BuildRestSiteState','BuildTreasureState','BuildMultiplayerBattleState','BuildMultiplayerEventState','BuildMultiplayerTreasureState']:
    stubs += f' static Dictionary<string,object?> {name}(object a, object b) => Marker("{name}");\n'
for name in ['BuildCardRewardState','BuildMapState','BuildMultiplayerMapState','BuildAllPlayersState']:
    stubs += f' static Dictionary<string,object?> {name}(object a) => Marker("{name}");\n'
tests = r'''
 static void Check(bool ok, string message) { if (!ok) throw new Exception(message); }
 static void Main() {
  int count = 0;
  foreach (var build in new Func<Dictionary<string,object?>>[] { BuildGameState, BuildMultiplayerGameState }) {
   foreach (var room in new Room[] { new EventRoom(), new TreasureRoom(), new RestSiteRoom(), new MerchantRoom(), new CombatRoom() }) {
    RunManager.Instance.State.CurrentRoom = room;
    foreach (var overlay in new object[] { new NRewardsScreen(), new NCardRewardSelectionScreen() }) {
     NOverlayStack.Instance.Top = overlay;
     NMapScreen.Instance.IsOpen = false;
     var state = build();
     var expected = overlay is NRewardsScreen ? "rewards" : "card_reward";
     Check((string?)state["state_type"] == expected, $"{build.Method.Name}/{room.GetType().Name}/{overlay.GetType().Name}: expected {expected}, got {state["state_type"]}"); count++;
     Check(state.ContainsKey(expected), "overlay data present"); count++;
     foreach (var flags in new[] { (true, false), (false, true), (true, true) }) {
      NMapScreen.Instance.IsOpen = flags.Item1; NMapScreen.Instance.Visible = flags.Item2;
      Check((string?)build()["state_type"] == "map", "open or visible map retains precedence after rewards"); count++;
     }
     NMapScreen.Instance.Visible = false;
    }
   }
   NMapScreen.Instance.IsOpen = false;
   NOverlayStack.Instance.Top = null;
   RunManager.Instance.State.CurrentRoom = new EventRoom { CanonicalEvent = new FakeMerchant() };
   Check((string?)build()["state_type"] == "fake_merchant", "fake merchant uses dedicated state"); count++;
   NOverlayStack.Instance.Top = new UnknownOverlay();
   Check((string?)build()["state_type"] == "overlay", "unknown overlay retained"); count++;
  }
  NMapScreen.Instance.IsOpen = false; NMapScreen.Instance.Visible = false;
  NOverlayStack.Instance.Top = new NGameOverScreen();
  foreach (var build in new Func<Dictionary<string,object?>>[] { BuildGameState, BuildMultiplayerGameState }) {
   var ended = build();
   Check((string?)ended["state_type"] == "game_over", "game over must precede generic overlay in both modes"); count++;
   Check(ended.ContainsKey("game_over"), "game over payload present"); count++;
  }
  Console.WriteLine($"PASS: {count} extracted SP/MP reward dispatch checks (simulated rooms)");
 }
}
'''
with tempfile.TemporaryDirectory(prefix='sts-reward-test-') as tmp:
    root = Path(tmp)
    (root / 'Program.cs').write_text(stubs + '\n'.join(methods) + tests)
    dotnet = shutil.which('dotnet')
    if not dotnet:
        raise SystemExit('The .NET 9 SDK is required on PATH')
    sdk_root = Path(dotnet).resolve().parent
    compiler = sorted((sdk_root / 'sdk').glob('9.*/Roslyn/bincore/csc.dll'))[-1]
    references = sorted((sdk_root / 'packs/Microsoft.NETCore.App.Ref').glob('9.*/ref/net9.0'))[-1]
    output = root / 'Test.dll'
    subprocess.run([dotnet, str(compiler), '-nologo', '-nullable:enable', '-langversion:12', '-nowarn:0649',
                    '-target:exe', f'-out:{output}',
                    *[f'-r:{p}' for p in references.glob('*.dll')], str(root / 'Program.cs')], check=True)
    (root / 'Test.runtimeconfig.json').write_text(json.dumps({'runtimeOptions': {
        'tfm': 'net9.0', 'framework': {'name': 'Microsoft.NETCore.App', 'version': '9.0.0'}}}))
    subprocess.run([dotnet, str(output)], check=True)
