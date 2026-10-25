#!/usr/bin/env python3
"""Compile complete production enemy/CrystalSphere state builders against test doubles."""
import json,os,subprocess,tempfile
from pathlib import Path
from test_card_metadata import extract
root=Path(__file__).resolve().parents[1]; source=(root/'McpMod.StateBuilder.cs').read_text()
stubs=r'''
using System;using System.Collections.Generic;using System.Linq;
namespace Godot { class Variant{public enum Type{Nil,String};public Type VariantType=Type.Nil;public string AsString()=>"text";} class Control{public bool Visible=true,InTree=true;public List<Control> Children=new();public Dictionary<string,Control> Nodes=new();public bool IsVisibleInTree()=>InTree;public T? GetNodeOrNull<T>(string n) where T:Control=>Nodes.GetValueOrDefault(n) as T;public Variant Get(string n)=>new();}}
class NClickableControl:Godot.Control{public bool IsEnabled=true;}
class NProceedButton:NClickableControl{}
class NCrystalSphereScreen:Godot.Control{}
class NCrystalSphereCell:Godot.Control{public Cell Entity=new();}
class Cell {public int X,Y;public bool IsHidden=true,IsHighlighted,IsHovered;public Item? Item;}
class Item {public bool IsGood;public (int X,int Y) Position,Size;}
class RunState{public Player? Player;}
static class LocalContext{public static Player? GetMe(RunState r)=>r.Player;}
class Player{public Character Character=new();public Creature Creature=new();public int Gold;}
class Character{public string Title="Hero";}
class Creature{public Monster? Monster=new();public int CombatId,CurrentHp=10,MaxHp=20,Block;public bool IsAlive=true;public CombatState? CombatState;}
class CombatState{public List<Creature> PlayerCreatures=new();}
class Monster{public (string Entry,int Other) Id=("RAT",0);public string Title="Rat";public MoveState? NextMove;}
class MoveState{public List<Intent> Intents=new();}
class Intent {public string IntentType="Attack";public Label GetIntentLabel(List<Creature> t,Creature c)=>new();public Tip GetHoverTip(List<Creature> t,Creature c)=>new();}
class Label{public string GetFormattedText()=>"attack";}
class Tip{public string? Title="Title",Description="Description";}
class Test{
static string? SafeGetText(Func<object?> f)=>f()?.ToString();static string StripRichTextTags(string s)=>s;static object BuildPowersState(Creature c)=>new object();
static List<T> FindAll<T>(Godot.Control c) where T:Godot.Control=>c.Children.OfType<T>().ToList();
static int count;static void Check(bool b,string m){count++;if(!b)throw new Exception(m);}
'''
tests=r'''
static void Main(){
var enemy=new Creature(){CombatId=7,CombatState=new(),Monster=new(){NextMove=new(){Intents=new(){new()}}}};var ids=new Dictionary<string,int>();
var e=BuildEnemyState(enemy,ids);Check((string?)e["entity_id"]=="RAT_0" && (int)e["combat_id"]! ==7,"enemy identity");
foreach(var k in new[]{"is_alive","is_visible","can_target","can_select"})Check(e[k] is true,k);
Check(((List<Dictionary<string,object?>>)e["intents"]!).Count==1,"intents retained");enemy.IsAlive=false;e=BuildEnemyState(enemy,ids);
foreach(var k in new[]{"is_alive","is_visible","can_target","can_select"})Check(e[k] is false,"dead "+k);
var screen=new NCrystalSphereScreen();var run=new RunState();var hidden=new NCrystalSphereCell(){InTree=false,Entity=new(){X=1}};var live=new NCrystalSphereCell();screen.Children.AddRange(new Godot.Control[]{hidden,live});
var big=new NClickableControl(){IsEnabled=false};var small=new NClickableControl(){InTree=false};var proceed=new NProceedButton(){Visible=false};screen.Nodes["%BigDivinationButton"]=big;screen.Nodes["%SmallDivinationButton"]=small;screen.Nodes["%ProceedButton"]=proceed;
var s=BuildCrystalSphereState(screen,run);Check((int)s["grid_width"]! ==2 && (int)s["grid_height"]! ==1,"grid retained");
Check(((List<Dictionary<string,object?>>)s["clickable_cells"]!).Count==1,"detached cell not clickable");
Check(s["can_use_big_tool"] is false && s["can_use_small_tool"] is false,"disabled/detached tools blocked");Check(s["can_proceed"] is false,"hidden proceed blocked");
big.IsEnabled=true;small.InTree=true;proceed.Visible=true;s=BuildCrystalSphereState(screen,run);Check(s["can_use_big_tool"] is true && s["can_use_small_tool"] is true && s["can_proceed"] is true,"ready controls");
live.Entity.IsHidden=false;live.Entity.Item=new(){IsGood=true,Position=(0,0),Size=(1,1)};s=BuildCrystalSphereState(screen,run);Check(((List<Dictionary<string,object?>>)s["revealed_items"]!).Count==1 && ((List<Dictionary<string,object?>>)s["clickable_cells"]!).Count==0,"revealed cell not clickable");
Console.WriteLine($"PASS: {count} complete enemy/CrystalSphere state checks (simulated controls)");}
}
'''
code=stubs+extract(source,'BuildEnemyState')+extract(source,'BuildCrystalSphereState')+tests
dotnet=os.environ.get('DOTNET','/tmp/sts-dotnet/dotnet');sdk=Path(dotnet).resolve().parent;csc=sorted((sdk/'sdk').glob('9.*/Roslyn/bincore/csc.dll'))[-1];refs=sorted((sdk/'packs/Microsoft.NETCore.App.Ref').glob('9.*/ref/net9.0'))[-1]
with tempfile.TemporaryDirectory(prefix='sts-enemy-crystal-') as tmp:
 p=Path(tmp);(p/'Test.cs').write_text(code);subprocess.run([dotnet,str(csc),'-nologo','-nullable:enable','-nowarn:0649','-target:exe',f'-out:{p}/Test.dll',*[f'-r:{r}' for r in refs.glob('*.dll')],str(p/'Test.cs')],check=True)
 (p/'Test.runtimeconfig.json').write_text(json.dumps({'runtimeOptions':{'tfm':'net9.0','framework':{'name':'Microsoft.NETCore.App','version':'9.0.0'}}}));subprocess.run([dotnet,str(p/'Test.dll')],check=True)
