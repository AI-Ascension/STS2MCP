#!/usr/bin/env python3
"""Compile actual dispatch and CrystalSphere actions with observable fake controls."""
import json,os,re,subprocess,tempfile
from pathlib import Path
from test_missing_actions import method
import test_selection_guards as selection
root=Path(__file__).resolve().parents[1];a=(root/'McpMod.Actions.cs').read_text();mp=(root/'McpMod.MultiplayerActions.cs').read_text()
dotnet=os.environ.get('DOTNET','/tmp/sts-dotnet/dotnet');sdk=Path(dotnet).resolve().parent;csc=sorted((sdk/'sdk').glob('9.*/Roslyn/bincore/csc.dll'))[-1];refs=sorted((sdk/'packs/Microsoft.NETCore.App.Ref').glob('9.*/ref/net9.0'))[-1]
def run(code):
 with tempfile.TemporaryDirectory(prefix='sts-popup-sphere-') as tmp:
  p=Path(tmp);(p/'Test.cs').write_text(code);subprocess.run([dotnet,str(csc),'-nologo','-nullable:enable','-nowarn:0649','-target:exe',f'-out:{p}/Test.dll',*[f'-r:{r}' for r in refs.glob('*.dll')],str(p/'Test.cs')],check=True)
  (p/'Test.runtimeconfig.json').write_text(json.dumps({'runtimeOptions':{'tfm':'net9.0','framework':{'name':'Microsoft.NETCore.App','version':'9.0.0'}}}));subprocess.run([dotnet,str(p/'Test.dll')],check=True)
stubs=r'''
using System;using System.Collections.Generic;using System.Text.Json;using Godot;
namespace Godot{class Engine{public static object GetMainLoop()=>new SceneTree();}class SceneTree{public object Root=new();}}
class NetType{public bool IsMultiplayer()=>true;}class NetService{public NetType Type=new();}
class RunManager{public static RunManager Instance=new();public NetService NetService=new();public bool IsInProgress=true;public object DebugOnlyGetState()=>new();}
class Player{}class LocalContext{public static Player GetMe(object r)=>new();}
static class Test{static bool Popup;static bool IsAnyFtueVisible(object r)=>Popup;static int Calls;
static Dictionary<string,object?> Error(string s,string? code=null)=>new(){["status"]="error",["error_code"]=code};
'''
sp=method(a,'ExecuteAction');multi=method(mp,'ExecuteMultiplayerAction');spies=''
seen=set()
for name,args in re.findall(r'=> (Execute\w+)\(([^)]*)\)',sp+multi):
 if name in seen:continue
 seen.add(name);params=', '.join(('Player player' if arg.strip()=='player' else 'Dictionary<string,JsonElement> data') for arg in args.split(',') if arg.strip())
 spies+=f'static Dictionary<string,object?> {name}({params})'+'{Calls++;return new(){["status"]="ok"};}\n'
run(stubs+spies+sp+multi+r'''
static void Main(){int checks=0;foreach(var dispatch in new Func<string,Dictionary<string,JsonElement>,Dictionary<string,object?>>[]{ExecuteAction,ExecuteMultiplayerAction}){
 Popup=true;Calls=0;var r=dispatch("discard_potion",new());if((string?)r["status"]!="error"||(string?)r["error_code"]!="blocking_popup_active"||Calls!=0)throw new Exception("popup must block dispatch");checks++;
 Popup=false;r=dispatch("discard_potion",new());if((string?)r["status"]!="ok"||Calls!=1)throw new Exception("clear popup must allow dispatch");checks++;
}Console.WriteLine($"PASS: {checks} SP/MP popup dispatch checks (simulated popup)");}}
''')
stubs=selection.STUBS.replace('public void ForceClick()=>Clicks++;','public static class SignalName{public const string Released="released";}public void ForceClick()=>Clicks++;')
stubs=stubs.replace('static class Test{','class NCrystalSphereScreen:Godot.Control{}class NCrystalSphereCell:Godot.Control{public Cell Entity=new();}class Cell{public int X,Y;public bool IsHidden=true;}\nstatic class Test{')
run(stubs+method(a,'ExecuteCrystalSphereSetTool')+method(a,'ExecuteCrystalSphereClickCell')+r'''
static void Main(){var screen=new NCrystalSphereScreen();NOverlayStack.Instance!.Screen=screen;var tool=new NClickableControl();screen.Nodes["%BigDivinationButton"]=tool;var cell=new NCrystalSphereCell();screen.Children.Add(cell);
var toolData=new Dictionary<string,JsonElement>{["tool"]=JsonSerializer.SerializeToElement("big")};var cellData=new Dictionary<string,JsonElement>{["x"]=JsonSerializer.SerializeToElement(0),["y"]=JsonSerializer.SerializeToElement(0)};
tool.InTree=false;cell.InTree=false;Check(!Ok(ExecuteCrystalSphereSetTool(toolData))&&tool.Clicks==0,"detached tool");Check(!Ok(ExecuteCrystalSphereClickCell(cellData))&&cell.Clicks==0,"detached cell");
tool.InTree=true;cell.InTree=true;tool.Visible=false;cell.Visible=false;Check(!Ok(ExecuteCrystalSphereSetTool(toolData))&&tool.Clicks==0,"hidden tool");Check(!Ok(ExecuteCrystalSphereClickCell(cellData))&&cell.Clicks==0,"hidden cell");
tool.Visible=true;cell.Visible=true;tool.IsEnabled=false;Check(!Ok(ExecuteCrystalSphereSetTool(toolData))&&tool.Clicks==0,"disabled tool");tool.IsEnabled=true;Check(Ok(ExecuteCrystalSphereSetTool(toolData))&&tool.Clicks==1,"ready tool");Check(Ok(ExecuteCrystalSphereClickCell(cellData))&&cell.Clicks==1,"ready cell");cell.Entity.IsHidden=false;Check(!Ok(ExecuteCrystalSphereClickCell(cellData))&&cell.Clicks==1,"revealed cell");
Console.WriteLine("PASS: 8 CrystalSphere action visibility checks (simulated controls)");}}
''')
