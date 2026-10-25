#!/usr/bin/env python3
"""Compile the actual character-menu action; simulated controls, no game calls."""
import json,os,subprocess,tempfile
from pathlib import Path
from test_missing_actions import method
root=Path(__file__).resolve().parents[1];source=(root/'McpMod.Actions.cs').read_text()
stubs=r'''
using System;using System.Linq;using System.Collections.Generic;
class NClickableControl{public bool IsEnabled=true,Visible=true,InTree=true;public int Clicks;public void ForceClick()=>Clicks++;}
class NCharacterSelectScreen{public Lobby? Lobby;public NClickableControl? _embarkButton=new();}
class Lobby{public int SeedChanges;public string? Seed;public void SetSeed(string s){SeedChanges++;Seed=s;}}
class NCharacterSelectButton{public Character? Character;public bool IsLocked;public void Select(){}}
class Character{public Id Id=new();public string Title="Ironclad";}class Id{public string Entry="IRONCLAD";}
static class Test{
static object? GetInstanceFieldValue(object s,string n)=>s.GetType().GetField(n)?.GetValue(s);
static bool IsControlVisibleOrActionable(NClickableControl? c)=>c!=null&&c.IsEnabled&&c.Visible&&c.InTree;
static string? SafeGetText(Func<string> f)=>f();static List<T> FindAll<T>(object s)=>new();
static Dictionary<string,object?> Error(string s)=>new(){["status"]="error",["error"]=s};
static int count;static void Check(bool b,string m){count++;if(!b)throw new Exception(m);}
'''
tests=r'''
static void Main(){
foreach(var option in new[]{"confirm","embark"}){
 var s=new NCharacterSelectScreen(){Lobby=new()}; var b=s._embarkButton!;
 b.Visible=false;var r=ExecuteCharacterSelectMenuOption(s,option,"SEED");Check((string?)r["status"]=="error"&&b.Clicks==0&&s.Lobby.SeedChanges==0,"hidden must not seed or embark");
 b.Visible=true;b.InTree=false;r=ExecuteCharacterSelectMenuOption(s,option,"SEED");Check((string?)r["status"]=="error"&&b.Clicks==0&&s.Lobby.SeedChanges==0,"detached must not seed or embark");
 b.InTree=true;b.IsEnabled=false;r=ExecuteCharacterSelectMenuOption(s,option,"SEED");Check((string?)r["status"]=="error"&&b.Clicks==0&&s.Lobby.SeedChanges==0,"disabled must not seed or embark");
 b.IsEnabled=true;r=ExecuteCharacterSelectMenuOption(s,option," SEED ");Check((string?)r["status"]=="ok"&&b.Clicks==1&&s.Lobby.SeedChanges==1&&s.Lobby.Seed=="SEED","enabled trimmed seed before embark");
 s.Lobby=null;r=ExecuteCharacterSelectMenuOption(s,option,"SEED");Check((string?)r["status"]=="error"&&b.Clicks==1,"unsupported singleplayer seed cannot click");
 r=ExecuteCharacterSelectMenuOption(s,option,null);Check((string?)r["status"]=="ok"&&b.Clicks==2,"unseeded singleplayer still works");
 s._embarkButton=null;r=ExecuteCharacterSelectMenuOption(s,option,null);Check((string?)r["status"]=="error","missing embark control");
}
Console.WriteLine($"PASS: {count} character embark readiness checks (simulated controls)");}}
'''
code=stubs+method(source,'ExecuteCharacterSelectMenuOption')+tests
dotnet=os.environ.get('DOTNET','/tmp/sts-dotnet/dotnet');sdk=Path(dotnet).resolve().parent;csc=sorted((sdk/'sdk').glob('9.*/Roslyn/bincore/csc.dll'))[-1];refs=sorted((sdk/'packs/Microsoft.NETCore.App.Ref').glob('9.*/ref/net9.0'))[-1]
with tempfile.TemporaryDirectory(prefix='sts-embark-') as tmp:
 p=Path(tmp);(p/'Test.cs').write_text(code);subprocess.run([dotnet,str(csc),'-nologo','-nullable:enable','-nowarn:0649','-target:exe',f'-out:{p}/Test.dll',*[f'-r:{r}' for r in refs.glob('*.dll')],str(p/'Test.cs')],check=True)
 (p/'Test.runtimeconfig.json').write_text(json.dumps({'runtimeOptions':{'tfm':'net9.0','framework':{'name':'Microsoft.NETCore.App','version':'9.0.0'}}}));subprocess.run([dotnet,str(p/'Test.dll')],check=True)
