#!/usr/bin/env python3
"""Compile actual event/rest methods against simulated model and UI controls, not game DLLs."""
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
source_units = []
namespace_names = set()
for filename, names in [('McpMod.StateBuilder.cs', ['BuildEventState', 'BuildRestSiteState']), ('McpMod.Actions.cs', ['ExecuteChooseEventOption', 'ExecuteChooseRestOption'])]:
    source = (a.source_root / filename).read_text()
    unit_methods = []
    imports = re.findall(r'^using ([^;]+);', source, re.M)
    namespace_names.update(n for n in imports if not n.startswith('System'))
    for name in names:
        m = re.search(r'    private static [^\n]+\b' + name + r'\(', source)
        if not m:
            raise SystemExit('Missing method: ' + name)
        end = source.index('    private static ', m.start() + 10)
        unit_methods.append(source[m.start():end])
    source_units.append(('\n'.join('using '+n+';' for n in imports))+'\npartial class Test {\n'+'\n'.join(unit_methods)+'\n}')
stubs = r'''
using System; using System.Collections.Generic; using System.Linq; using System.Text.Json;
using MegaCrit.Sts2.Core.Nodes.RestSite;
class Node { public List<Node> Children=new(); public bool Visible=true, TreeVisible=true; public bool IsVisibleInTree()=>Visible && TreeVisible; public T? GetNodeOrNull<T>(string path) where T:Node => Children.OfType<T>().FirstOrDefault(); }
class NClickableControl:Node { public bool IsEnabled=true; public int Clicks; public void ForceClick()=>Clicks++; }
class NEventRoom:Node { public static NEventRoom? Instance; }
class NAncientEventLayout:Node { }
class NEventOptionButton:NClickableControl { public Option Option=new(); }
namespace MegaCrit.Sts2.Core.Nodes.RestSite { class NRestSiteButton:global::NClickableControl { public global::Option Option=new(); } }
class NRestSiteRoom:Node { public static NRestSiteRoom? Instance; public NClickableControl? ProceedButton; }
class Id { public string Entry="event"; }
class Relic { public Id Id=new(); public string Title="Relic", DynamicDescription="Relic desc", Rarity="Rare"; public object HoverTipsExcludingRelic=new(); }
class Option { public string Title="Option", Description="Description", OptionId="REST"; public bool IsLocked, IsProceed, WasChosen, IsEnabled=true; public Relic? Relic; public object HoverTips=new(); }
class EventModel { public Id Id=new(); public string Title="Canonical", Description="Original"; }
class AncientEventModel:EventModel { }
class EventRoom { public EventModel CanonicalEvent=new(); public EventModel? LocalMutableEvent; }
class RestSiteRoom { public List<Option> Options=new(); }
class Character { public string Title="Character"; }
class Creature { public int CurrentHp=30, MaxHp=40; }
class Player { public Character Character=new(); public Creature Creature=new(); public int Gold=10; }
class RunState { public Player? Player; }
class LocalContext { public static Player? GetMe(RunState r)=>r.Player; }
partial class Test {
 static string? SafeGetText(Func<string?> f)=>f();
 static object BuildHoverTips(object x)=>x;
 static bool IsControlVisibleOrActionable(NClickableControl? c)=>c!=null && c.Visible && c.IsVisibleInTree() && c.IsEnabled;
 static List<T> FindAll<T>(Node node) where T:Node { var all=new List<T>(); foreach(var child in node.Children) { if(child is T t) all.Add(t); all.AddRange(FindAll<T>(child)); } return all; }
 static T? FindFirst<T>(Node n) where T:Node=>FindAll<T>(n).FirstOrDefault();
 static Dictionary<string,object?> Error(string message)=>new(){["status"]="error",["error"]=message};
 static Dictionary<string,JsonElement> Index(int i)=>new(){["index"]=JsonSerializer.SerializeToElement(i)};
 static int count; static void Check(bool value,string message) { count++; if(!value)throw new Exception(message); }
 static List<Dictionary<string,object?>> Options(Dictionary<string,object?> state)=>(List<Dictionary<string,object?>>)state["options"]!;
 static bool IsError(Dictionary<string,object?> r)=>(string?)r["status"]=="error";
'''
tests = r'''
 static void Main() {
  var run=new RunState {Player=new()}; var ev=new EventRoom {LocalMutableEvent=new EventModel {Title="Mutable",Description="Updated"}};
  var hidden=new NEventOptionButton {Visible=false}; var ancestorHidden=new NEventOptionButton {TreeVisible=false}; var active=new NEventOptionButton();
  NEventRoom.Instance=new(); NEventRoom.Instance.Children.AddRange(new Node[]{hidden,ancestorHidden,active});
  var state=BuildEventState(ev,run); var options=Options(state);
  Check((string?)state["event_name"]=="Mutable" && (string?)state["body"]=="Updated","mutable event model");
  Check(state.ContainsKey("player"),"retain player summary");
  Check(options.Count==1 && (int)options[0]["index"]! == 0,"only visible event options indexed");
  Check((bool)options[0]["can_choose"]! && (bool)options[0]["is_enabled"]! && (bool)options[0]["is_visible"]!,"ready event option metadata");
  Check(!IsError(ExecuteChooseEventOption(Index(0))) && active.Clicks==1 && hidden.Clicks==0 && ancestorHidden.Clicks==0,"event action uses same visible index");
  active.IsEnabled=false; Check(!(bool)Options(BuildEventState(ev,run))[0]["can_choose"]!,"disabled event metadata");
  Check(IsError(ExecuteChooseEventOption(Index(0))) && active.Clicks==1,"disabled event rejected");
  active.IsEnabled=true; active.Option.IsLocked=true;
  Check(!(bool)Options(BuildEventState(ev,run))[0]["can_choose"]! && IsError(ExecuteChooseEventOption(Index(0))) && active.Clicks==1,"locked event rejected");
  active.Option.IsLocked=false; active.Option.Relic=new(); options=Options(BuildEventState(ev,run));
  Check((string?)options[0]["relic_rarity"]=="Rare" && options[0].ContainsKey("relic_id") && options[0].ContainsKey("relic_keywords"),"relic metadata");
  Check(IsError(ExecuteChooseEventOption(Index(-1))) && IsError(ExecuteChooseEventOption(Index(1))),"event bounds");
  Check(IsError(ExecuteChooseEventOption(new())),"missing event index");
  ev.LocalMutableEvent=null; Check((string?)BuildEventState(ev,run)["event_name"]=="Canonical","canonical fallback");
  active.TreeVisible=false; Check(Options(BuildEventState(ev,run)).Count==0 && IsError(ExecuteChooseEventOption(Index(0))),"hidden parent removes options");
  NEventRoom.Instance=null; Check(Options(BuildEventState(ev,run)).Count==0 && IsError(ExecuteChooseEventOption(Index(0))),"no event UI");
  run.Player=null; Check(!BuildEventState(ev,run).ContainsKey("player"),"optional player");
  var rest=new RestSiteRoom(); rest.Options.Add(new Option {Title="Model-only not clickable"});
  var rh=new NRestSiteButton {Visible=false}; var rth=new NRestSiteButton {TreeVisible=false}; var ra=new NRestSiteButton {Option=new Option {Title="Actual UI"}};
  var proceed=new NClickableControl(); NRestSiteRoom.Instance=new(){ProceedButton=proceed}; NRestSiteRoom.Instance.Children.AddRange(new Node[]{rh,rth,ra});
  state=BuildRestSiteState(rest,run); options=Options(state);
  Check(options.Count==1 && (string?)options[0]["name"]=="Actual UI" && (int)options[0]["index"]! == 0,"rest reflects clickable UI not model order");
  Check((bool)options[0]["can_choose"]! && (bool)options[0]["is_visible"]! && (bool)state["can_proceed"]!,"rest ready metadata");
  Check(!IsError(ExecuteChooseRestOption(Index(0))) && ra.Clicks==1 && rh.Clicks==0 && rth.Clicks==0,"rest action index matches state");
  ra.IsEnabled=false; Check(!(bool)Options(BuildRestSiteState(rest,run))[0]["can_choose"]! && IsError(ExecuteChooseRestOption(Index(0))) && ra.Clicks==1,"UI disabled rest rejected");
  ra.IsEnabled=true; ra.Option.IsEnabled=false; Check(!(bool)Options(BuildRestSiteState(rest,run))[0]["can_choose"]! && IsError(ExecuteChooseRestOption(Index(0))) && ra.Clicks==1,"model disabled rest rejected");
  Check(IsError(ExecuteChooseRestOption(Index(-1))) && IsError(ExecuteChooseRestOption(Index(1))),"rest bounds");
  Check(IsError(ExecuteChooseRestOption(new())),"missing rest index");
  proceed.Visible=false; Check(!(bool)BuildRestSiteState(rest,run)["can_proceed"]!,"hidden proceed unavailable");
  proceed.Visible=true; proceed.TreeVisible=false; Check(!(bool)BuildRestSiteState(rest,run)["can_proceed"]!,"ancestor hidden proceed unavailable");
  proceed.TreeVisible=true; proceed.IsEnabled=false; Check(!(bool)BuildRestSiteState(rest,run)["can_proceed"]!,"disabled proceed unavailable");
  NRestSiteRoom.Instance.ProceedButton=null; Check(!(bool)BuildRestSiteState(rest,run)["can_proceed"]!,"null proceed unavailable");
  ra.Visible=false; Check(Options(BuildRestSiteState(rest,run)).Count==0 && IsError(ExecuteChooseRestOption(Index(0))),"no visible rest options");
  NRestSiteRoom.Instance=null; Check(Options(BuildRestSiteState(rest,run)).Count==0 && IsError(ExecuteChooseRestOption(Index(0))),"no rest UI");
  Console.WriteLine($"PASS: {count} event/rest checks (simulated models/UI)");
 }
}
'''
with tempfile.TemporaryDirectory(prefix='sts-event-rest-') as tmp:
    root = Path(tmp)
    (root/'Program.cs').write_text(stubs+tests)
    # Preserve each production compilation unit's own imports. A using in the
    # Actions partial must not accidentally make StateBuilder compile.
    (root/'NamespacePlaceholders.cs').write_text('\n'.join('namespace '+n+' {}' for n in namespace_names))
    for index, unit in enumerate(source_units):
        (root/f'Production{index}.cs').write_text(unit)
    dotnet=shutil.which('dotnet')
    if not dotnet: raise SystemExit('.NET 9 SDK required on PATH')
    sdk=Path(dotnet).resolve().parent
    compiler=sorted((sdk/'sdk').glob('9.*/Roslyn/bincore/csc.dll'))[-1]
    refs=sorted((sdk/'packs/Microsoft.NETCore.App.Ref').glob('9.*/ref/net9.0'))[-1]
    output=root/'Test.dll'
    subprocess.run([dotnet,str(compiler),'-nologo','-nullable:enable','-langversion:12','-nowarn:0649','-target:exe',f'-out:{output}',*[f'-r:{x}' for x in refs.glob('*.dll')],*[str(p) for p in root.glob('*.cs')]],check=True)
    (root/'Test.runtimeconfig.json').write_text(json.dumps({'runtimeOptions':{'tfm':'net9.0','framework':{'name':'Microsoft.NETCore.App','version':'9.0.0'}}}))
    subprocess.run([dotnet,str(output)],check=True)
