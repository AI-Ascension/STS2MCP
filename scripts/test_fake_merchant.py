#!/usr/bin/env python3
"""Exercise actual fake merchant methods with simulated models/UI, not game DLLs."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

p = argparse.ArgumentParser()
p.add_argument('--source-root', type=Path, default=Path(__file__).resolve().parents[1])
a = p.parse_args()
methods = []
for filename, names in [('McpMod.Actions.cs', ['ExecuteShopPurchase', 'ExecuteProceed']), ('McpMod.StateBuilder.cs', ['BuildFakeMerchantState', 'BuildFakeMerchantShopItems']), ('McpMod.Formatting.cs', ['FormatFakeMerchantMarkdown', 'FormatShopMarkdown', 'FormatKeywordNames'])]:
    source = (a.source_root / filename).read_text()
    for name in names:
        match = re.search(r'    private static [^\n]+\b' + name + r'\(', source)
        if match is None:
            raise SystemExit(f'Missing required method: {name}')
        start = match.start()
        end = source.index('    private static ', start + 10)
        methods.append(source[start:end])
stubs = r'''
using System; using System.Text; using System.Collections.Generic; using System.Linq; using System.Text.Json;
using System.Diagnostics.CodeAnalysis;
namespace Godot {
 class Node { public List<Node> Children = new(); }
 class SceneTree { public Node Root = new(); }
 static class Engine { public static SceneTree Tree = new(); public static object GetMainLoop() => Tree; }
}
class NClickableControl : Godot.Node { public bool Visible=true, InTree=true; public bool IsEnabled=true; public int Clicks; public Action? OnClick; public void ForceClick() { Clicks++; OnClick?.Invoke(); } }
class NBackButton : NClickableControl { }
class NProceedButton : NClickableControl { }
class NRewardsScreen : Godot.Node { }
class NOverlayStack { public static NOverlayStack Instance = new(); public object? Top; public object? Peek() => Top; }
class NRestSiteRoom : Godot.Node { public static NRestSiteRoom? Instance; public NProceedButton ProceedButton=new(); }
class NTreasureRoom : Godot.Node { public NProceedButton ProceedButton=new(); }
class NMerchantInventory : Godot.Node { public bool IsOpen; }
class NMerchantRoom : Godot.Node { public static NMerchantRoom? Instance; public NMerchantInventory Inventory=new(); public NProceedButton ProceedButton=new(); public void OpenInventory() => Inventory.IsOpen=true; }
class NEventRoom : Godot.Node { public static NEventRoom? Instance; }
class NFakeMerchant : Godot.Node { public NClickableControl MerchantButton=new(); }
class Id { public string Entry="fake"; }
class Relic { public Id Id=new(); public string Title="relic", DynamicDescription="description", Rarity="rare"; public object HoverTipsExcludingRelic=new(); }
class Entry {
 public int Cost=10; public bool IsStocked=true, EnoughGold=true; public Relic? Model=new();
 public MerchantInventory? PurchasedFrom;
 public System.Threading.Tasks.Task OnTryPurchaseWrapper(MerchantInventory inventory) { PurchasedFrom=inventory; return System.Threading.Tasks.Task.CompletedTask; }
}
class MerchantInventory { public List<Entry> RelicEntries=new(); public IEnumerable<Entry> AllEntries => RelicEntries; }
class FakeMerchant { public Id Id=new(); public string Title="Fake Merchant"; public bool StartedFight; public MerchantInventory? Inventory; }
class EventRoom { public object CanonicalEvent=new FakeMerchant(); public object? LocalMutableEvent; }
class MerchantRoom { public MerchantInventory? Inventory; }
class RunState { public object? CurrentRoom; }
class Player { public RunState RunState=new(); public int Gold=20; }
class Test {
 static T? FindFirst<T>(Godot.Node root) where T:Godot.Node {
  if(root is T self) return self;
  foreach(var child in root.Children) { var match=FindFirst<T>(child); if(match!=null)return match; }
  return null;
 }
 static bool IsControlVisibleOrActionable([NotNullWhen(true)] NClickableControl? c) => c != null && c.Visible && c.InTree && c.IsEnabled;
 static string? SafeGetText(Func<string?> get) => get();
 static List<string> BuildHoverTips(object tips) => new();
 static Dictionary<string,object?> Error(string message) => new() { ["status"]="error", ["error"]=message };
'''
tests = r'''
 static int Count;
 static void Check(bool ok,string message) { Count++; if(!ok)throw new Exception(message); }
 static Dictionary<string,JsonElement> Index(int i) => new() { ["index"] = JsonSerializer.SerializeToElement(i) };
 static void Main() {
  var canonical=new FakeMerchant();
  var inventory=new MerchantInventory(); var entry=new Entry(); inventory.RelicEntries.Add(entry);
  var local=new FakeMerchant { Inventory=inventory };
  var room=new EventRoom { CanonicalEvent=canonical, LocalMutableEvent=local };
  var player=new Player { RunState = new RunState { CurrentRoom=room } };
  var ui=new NFakeMerchant(); var inventoryUi=new NMerchantInventory();
  var back=new NBackButton(); var proceed=new NProceedButton { IsEnabled=false };
  ui.Children.AddRange(new Godot.Node[] { inventoryUi, back, proceed });
  ui.MerchantButton.OnClick=()=>inventoryUi.IsOpen=true;
  back.OnClick=()=> { inventoryUi.IsOpen=false; proceed.IsEnabled=true; };
  NEventRoom.Instance=new NEventRoom(); NEventRoom.Instance.Children.Add(ui);
  var state=BuildFakeMerchantState(room,player.RunState);
  var shop=(Dictionary<string,object?>)state["shop"]!;
  var items=(List<Dictionary<string,object?>>)shop["items"]!;
  var markdown = new StringBuilder(); FormatFakeMerchantMarkdown(markdown, state);
  Check(markdown.ToString().Contains("10g"),"fake merchant markdown renders price");
  Check(items.Count==1,"uses populated local inventory rather than empty canonical template");
  Check((int)items[0]["index"]! == 0,"item index");
  Check((bool)shop["inventory_open"]! && ui.MerchantButton.Clicks==1,"opens via merchant button");
  Check((bool)shop["can_close_inventory"]! && (bool)shop["can_proceed"]!,"exposes close-first proceed");
  Check((string?)ExecuteShopPurchase(player,Index(0))["status"]=="ok","fake purchase succeeds");
  Check(ReferenceEquals(entry.PurchasedFrom,inventory),"purchase uses local inventory");
  Check((string?)ExecuteShopPurchase(player,Index(-1))["status"]=="error","negative index");
  Check((string?)ExecuteShopPurchase(player,Index(1))["status"]=="error","index beyond stock");
  entry.IsStocked=false; Check((string?)ExecuteShopPurchase(player,Index(0))["status"]=="error","sold out");
  entry.IsStocked=true; entry.EnoughGold=false; Check((string?)ExecuteShopPurchase(player,Index(0))["status"]=="error","insufficient gold"); entry.EnoughGold=true;
  Check((string?)ExecuteProceed()["status"]=="ok","fake proceed succeeds");
  Check(back.Clicks==1 && proceed.Clicks==1 && !inventoryUi.IsOpen,"close inventory before proceeding");
  proceed.IsEnabled=false; Check((string?)ExecuteProceed()["status"]=="error","disabled proceed");
  local.Inventory=null;
  Check((string?)ExecuteShopPurchase(player,Index(0))["status"]=="error","inventory unavailable");
  Check(BuildFakeMerchantShopItems(null).ContainsKey("error"),"missing inventory state is explicit");
  local.StartedFight=true;
  Check(((List<Dictionary<string,object?>>)((Dictionary<string,object?>)BuildFakeMerchantState(room,player.RunState)["shop"]!)["items"]!).Count==0,"fight state hides stock");
  local.Inventory=inventory; entry.PurchasedFrom=null;
  Check((string?)ExecuteShopPurchase(player,Index(0))["status"]=="error","fight started rejects retained inventory");
  Check(entry.PurchasedFrom==null,"fight started never invokes purchase");
  player.RunState.CurrentRoom=new MerchantRoom { Inventory=inventory };
  Check((string?)ExecuteShopPurchase(player,Index(0))["status"]=="ok","regular merchant remains supported");
  NEventRoom.Instance=null;
  foreach(var context in new[]{"rewards","rest","merchant","treasure"}) {
   NOverlayStack.Instance.Top=null;NRestSiteRoom.Instance=null;NMerchantRoom.Instance=null;Godot.Engine.Tree.Root.Children.Clear();
   var button=new NProceedButton();
   if(context=="rewards") {var reward=new NRewardsScreen();reward.Children.Add(button);NOverlayStack.Instance.Top=reward;}
   if(context=="rest") NRestSiteRoom.Instance=new(){ProceedButton=button};
   if(context=="merchant") NMerchantRoom.Instance=new(){ProceedButton=button};
   if(context=="treasure") Godot.Engine.Tree.Root.Children.Add(new NTreasureRoom(){ProceedButton=button});
   button.Visible=false;Check((string?)ExecuteProceed()["status"]=="error"&&button.Clicks==0,context+" hidden proceed");
   button.Visible=true;button.InTree=false;Check((string?)ExecuteProceed()["status"]=="error"&&button.Clicks==0,context+" detached proceed");
   button.InTree=true;button.IsEnabled=false;Check((string?)ExecuteProceed()["status"]=="error"&&button.Clicks==0,context+" disabled proceed");
   button.IsEnabled=true;Check((string?)ExecuteProceed()["status"]=="ok"&&button.Clicks==1,context+" ready proceed");
  }
  Godot.Engine.Tree.Root.Children.Clear();NMerchantRoom.Instance=new();NMerchantRoom.Instance.Inventory.IsOpen=true;NMerchantRoom.Instance.ProceedButton.Visible=false;
  var regularBack=new NBackButton(){Visible=false};NMerchantRoom.Instance.Children.Add(regularBack);
  Check((string?)ExecuteProceed()["status"]=="error"&&regularBack.Clicks==0,"hidden merchant back not clicked");
  Console.WriteLine($"PASS: {Count} extracted fake merchant checks (simulated models/UI)");
 }
}
'''
with tempfile.TemporaryDirectory(prefix='sts-merchant-test-') as tmp:
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
