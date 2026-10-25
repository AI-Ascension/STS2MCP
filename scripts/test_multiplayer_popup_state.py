#!/usr/bin/env python3
"""Compile MP state prefix, actual FTUE state helper and gameplay dispatch together.
Route ordering is checked in production source; no real HTTP/game calls occur.
"""
import json,os,re,subprocess,tempfile
from pathlib import Path
from test_missing_actions import method
root=Path(__file__).resolve().parents[1];state=(root/'McpMod.MultiplayerState.cs').read_text();actions=(root/'McpMod.MultiplayerActions.cs').read_text();helpers=(root/'McpMod.Helpers.cs').read_text();routes=(root/'McpMod.cs').read_text()
route=method(routes,'HandlePostMultiplayerAction')
assert route.index('if (action == "menu_select")') < route.index('ExecuteMultiplayerAction(action, parsed)')
assert 'ExecuteMenuSelect(option, seed)' in route
body=method(state,'BuildMultiplayerGameState');body=body[:body.index('        // Multiplayer metadata')]+'return result;\n    }'
dispatch=method(actions,'ExecuteMultiplayerAction')
stubs=r'''
using System;using System.Collections.Generic;using System.Text.Json;using Godot;
namespace Godot{class Node{}class SceneTree{public Node Root=new();}static class Engine{public static SceneTree Tree=new();public static object GetMainLoop()=>Tree;}}
class NetType{public bool IsMultiplayer()=>true;}class Network{public NetType Type=new();}
class RunManager{public static RunManager Instance=new();public bool IsInProgress=true;public Network NetService=new();public object DebugOnlyGetState()=>new();}
class Player{}static class LocalContext{public static Player GetMe(object s)=>new();}
static class Test{
static int Kind,Calls;static object? FindVisibleAcceptTutorialsFtue(Node n)=>Kind==1?new object():null;static bool IsFtueNodeActive(object n)=>true;
static object? FindVisibleGenericFtue(Node n)=>Kind==2?new object():null;static object? FindFtueAdvanceButton(object n)=>new();
static Dictionary<string,object?>? BuildVisiblePopupState(Node n)=>null;
static Dictionary<string,object?> Error(string s,string? code=null)=>new(){["status"]="error",["error_code"]=code};
'''
spies=''
for name,args in re.findall(r'=> (Execute\w+)\(([^)]*)\)',dispatch):
 params=', '.join(('Player player' if arg.strip()=='player' else 'Dictionary<string,JsonElement> data') for arg in args.split(',') if arg.strip())
 spies+=f'static Dictionary<string,object?> {name}({params})'+'{Calls++;return new(){["status"]="ok"};}\n'
tests=r'''
static void Main(){int checks=0;foreach(var kind in new[]{1,2}){Kind=kind;Calls=0;var s=BuildMultiplayerGameState();
 if((string?)s["kind"]!="multiplayer_state"||(string?)s["status"]!="ok"||(string?)s.GetValueOrDefault("state_type")!="menu")throw new Exception("MP popup requires menu with MP envelope");checks++;
 var options=(List<Dictionary<string,object?>>)s["options"]!;var expected=kind==1?new[]{"no","yes"}:new[]{"advance","proceed"};
 for(int i=0;i<2;i++){if((string?)options[i]["name"]!=expected[i]||options[i]["enabled"] is not true)throw new Exception("actual option names unavailable");checks++;}
 var blocked=ExecuteMultiplayerAction("discard_potion",new());if((string?)blocked["error_code"]!="blocking_popup_active"||Calls!=0)throw new Exception("popup gameplay bypass");checks++;
}Kind=0;var r=ExecuteMultiplayerAction("discard_potion",new());if((string?)r["status"]!="ok"||Calls!=1)throw new Exception("clear popup blocks gameplay");checks++;
Console.WriteLine($"PASS: {checks} MP popup state/action checks plus native menu route ordering");}}
'''
code=stubs+spies+method(helpers,'BuildVisibleFtueState')+method(helpers,'WithStateEnvelope')+method(helpers,'IsAnyFtueVisible')+body+dispatch+tests
dotnet=os.environ.get('DOTNET','/tmp/sts-dotnet/dotnet');sdk=Path(dotnet).resolve().parent;csc=sorted((sdk/'sdk').glob('9.*/Roslyn/bincore/csc.dll'))[-1];refs=sorted((sdk/'packs/Microsoft.NETCore.App.Ref').glob('9.*/ref/net9.0'))[-1]
with tempfile.TemporaryDirectory(prefix='sts-mp-popup-') as tmp:
 p=Path(tmp);(p/'Test.cs').write_text(code);subprocess.run([dotnet,str(csc),'-nologo','-nullable:enable','-nowarn:0649','-target:exe',f'-out:{p}/Test.dll',*[f'-r:{r}' for r in refs.glob('*.dll')],str(p/'Test.cs')],check=True)
 (p/'Test.runtimeconfig.json').write_text(json.dumps({'runtimeOptions':{'tfm':'net9.0','framework':{'name':'Microsoft.NETCore.App','version':'9.0.0'}}}));subprocess.run([dotnet,str(p/'Test.dll')],check=True)
