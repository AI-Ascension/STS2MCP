#!/usr/bin/env python3
"""Compile actual map/reward serializers and actions with simulated controls, not game DLLs."""
import argparse,json,shutil,subprocess,tempfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,default=Path(__file__).resolve().parents[1]);a=p.parse_args()
names=[('McpMod.StateBuilder.cs',n) for n in ['BuildMapState(', 'BuildMapNode(', 'BuildRewardsState(', 'GetRelicRewardModel(']]+[('McpMod.Actions.cs',n) for n in ['ExecuteChooseMapNode(', 'ExecuteClaimReward(']]
# Locate declarations rather than callsites.
methods=[]
for file,name in names:
 s=(a.source_root/file).read_text(); import re
 match=re.search(r'    private static [^\n]+ '+re.escape(name),s)
 if match is None and name=='GetRelicRewardModel(': continue # Baseline lacks this helper.
 assert match, f'Missing method {name}'
 start=match.start();end=s.find('\n    private static ',match.end());methods.append(s[start:end if end>=0 else len(s)])
stubs=r'''
using System;using System.Linq;using System.Collections.Generic;using System.Text.Json;
class Node {public bool Visible=true,Tree=true,IsEnabled=true; public List<Node> Children=new();public bool IsVisibleInTree()=>Tree;}
class NMapScreen:Node {public static NMapScreen? Instance; public bool IsOpen=true;public NMapPoint? Selected;public void OnMapPointSelectedLocally(NMapPoint p)=>Selected=p;}
enum MapPointState {Travelable,Locked}
class NMapPoint:Node {public MapPointState State;public MapPoint? Point;}
class MapPoint {public (int col,int row) coord; public string PointType="monster";public List<MapPoint> Children=new();}
class Map {public MapPoint StartingMapPoint=new(),BossMapPoint=new(),SecondBossMapPoint=new();public List<MapPoint> Nodes=new();public MapPoint? GetPoint((int col,int row) c)=>Nodes.FirstOrDefault(p=>p.coord==c);public List<MapPoint> GetAllMapPoints()=>Nodes;}
class RunState {public Map Map=new();public List<(int col,int row)> VisitedMapCoords=new();}
class Player {public List<object?> PotionSlots=new(); public Character Character=new(); public Creature Creature=new(); public int Gold;}
class Character {public string Title="hero";}
class Creature {public int CurrentHp=10,MaxHp=20;}
class LocalContext {public static Player? Player;public static Player? GetMe(RunState s)=>Player;}
class NRewardsScreen:Node {}
class NOverlayStack {public static NOverlayStack? Instance;public object? Top;public object? Peek()=>Top;}
class Reward {public string Description="reward";}
class GoldReward:Reward {public int Amount;}
class CardReward:Reward {}
class PotionReward:Reward {public Potion? Potion;}
class Id {public string Entry="id";}
class Potion {public Id Id=new();public string Title="potion",DynamicDescription="details",Rarity="common",TargetType="enemy",Usage="combat";public List<object> ExtraHoverTips=new();}
class RelicModel {public Id Id=new();public string Title="relic",DynamicDescription="relic details",Rarity="rare";public List<object> HoverTipsExcludingRelic=new();}
class RelicReward:Reward {public RelicModel? Relic;}
class NRewardButton:Node {public Reward? Reward;public bool Clicked;public void ForceClick()=>Clicked=true;}
class NProceedButton:Node {}
class Test {
 static List<T> FindAll<T>(Node root) where T:Node => root.Children.OfType<T>().ToList();
 static T? FindFirst<T>(Node root) where T:Node => FindAll<T>(root).FirstOrDefault();
 static bool IsNodeVisible(Node? n)=>n!=null&&n.Visible&&n.Tree;
 static bool IsControlVisibleOrActionable(Node? n)=>IsNodeVisible(n)&&n!.IsEnabled;
 static string SafeGetText(Func<string?> f)=>f()??"";
 static object BuildHoverTips(object tips)=>tips;
 static string GetRewardTypeName(Reward r)=>r switch {GoldReward=>"gold",PotionReward=>"potion",RelicReward=>"relic",_=>"card"};
 static Dictionary<string,object?> Error(string e)=>new(){["status"]="error",["error"]=e};
 static Dictionary<string,JsonElement> Index(int i)=>new(){["index"]=JsonSerializer.SerializeToElement(i)};
 static int count;static void Check(bool yes,string label){count++;if(!yes)throw new Exception(label);}
'''
tests=r'''
 static void Main(){
 var run=new RunState();var map=new NMapScreen();NMapScreen.Instance=map;
 var hidden=new NMapPoint{Point=new(){coord=(0,1)},Visible=false};var treeHidden=new NMapPoint{Point=new(){coord=(1,1)},Tree=false};var invalid=new NMapPoint();var good=new NMapPoint{Point=new(){coord=(3,1)}};var earlier=new NMapPoint{Point=new(){coord=(2,1)}};
 map.Children.AddRange(new Node[]{hidden,treeHidden,invalid,good,earlier});
 var state=BuildMapState(run);var options=(List<Dictionary<string,object?>>)state["next_options"]!;
 Check(options.Count==2,"only visible valid map nodes");Check((int)options[0]["col"]! ==2,"map order preserved");Check((bool)options[0]["is_visible"]!&&(bool)options[0]["can_travel"]!,"map readiness metadata");Check(state.ContainsKey("nodes")&&state.ContainsKey("boss"),"full map preserved");
 map.IsOpen=false;Check((string)ExecuteChooseMapNode(Index(0))["status"]! =="ok"&&map.Selected==earlier,"visible-only map action aligned");
 map.Visible=false;Check((string)ExecuteChooseMapNode(Index(0))["status"]! =="error","closed hidden map rejected");map.Visible=true;
 Check((string)ExecuteChooseMapNode(Index(-1))["status"]! =="error","negative map index");Check((string)ExecuteChooseMapNode(Index(2))["status"]! =="error","map bounds filtered");
 var screen=new NRewardsScreen();NOverlayStack.Instance=new(){Top=screen};var gold=new NRewardButton{Reward=new GoldReward{Amount=7}};var hiddenReward=new NRewardButton{Reward=new GoldReward{Amount=99},Visible=false};var treeReward=new NRewardButton{Reward=new GoldReward(),Tree=false};var disabled=new NRewardButton{Reward=new GoldReward(),IsEnabled=false};var missing=new NRewardButton();var potion=new NRewardButton{Reward=new PotionReward{Potion=new()}};var relic=new NRewardButton{Reward=new RelicReward{Relic=new()}};var proceed=new NProceedButton{Visible=false};
 screen.Children.AddRange(new Node[]{hiddenReward,treeReward,disabled,missing,gold,potion,relic,proceed});
 var rewards=BuildRewardsState(screen,run);var items=(List<Dictionary<string,object?>>)rewards["items"]!;
 Check(items.Count==3,"only visible enabled nonnull rewards");Check((int)items[0]["gold_amount"]! ==7,"gold metadata");Check((bool)items[0]["is_visible"]!&&(bool)items[0]["can_claim"]!,"reward readiness metadata");Check(items[1].ContainsKey("potion_description")&&items[1].ContainsKey("potion_usage"),"potion metadata");Check(items[2].ContainsKey("relic_description")&&items[2].ContainsKey("relic_rarity"),"relic reflection metadata");
 Check(!(bool)rewards["can_proceed"]!,"hidden proceed not ready");proceed.Visible=true;proceed.IsEnabled=false;Check(!(bool)BuildRewardsState(screen,run)["can_proceed"]!,"disabled proceed");proceed.IsEnabled=true;Check((bool)BuildRewardsState(screen,run)["can_proceed"]!,"visible enabled proceed");
 Check((string)ExecuteClaimReward(Index(0))["status"]! =="ok"&&gold.Clicked&&!hiddenReward.Clicked,"reward index aligned");Check((string)ExecuteClaimReward(Index(3))["status"]! =="error","reward bounds filtered");
 LocalContext.Player=new();Check(BuildMapState(run).ContainsKey("player")&&BuildRewardsState(screen,run).ContainsKey("player"),"new player summaries preserved");
 Console.WriteLine($"PASS: {count} compiled map/reward contract checks (simulated controls)");
 }
}
'''
with tempfile.TemporaryDirectory(prefix='sts-map-rewards-') as tmp:
 root=Path(tmp);(root/'Program.cs').write_text(stubs+'\n'.join(methods)+tests)
 dotnet=shutil.which('dotnet'); assert dotnet,'Requires .NET 9 SDK on PATH';sdk=Path(dotnet).resolve().parent
 compiler=sorted((sdk/'sdk').glob('9.*/Roslyn/bincore/csc.dll'))[-1];refs=sorted((sdk/'packs/Microsoft.NETCore.App.Ref').glob('9.*/ref/net9.0'))[-1]
 subprocess.run([dotnet,str(compiler),'-nologo','-nullable:enable','-langversion:12','-nowarn:0649','-target:exe',f'-out:{root}/Test.dll',*[f'-r:{p}' for p in refs.glob('*.dll')],str(root/'Program.cs')],check=True)
 (root/'Test.runtimeconfig.json').write_text(json.dumps({'runtimeOptions':{'tfm':'net9.0','framework':{'name':'Microsoft.NETCore.App','version':'9.0.0'}}}))
 subprocess.run([dotnet,str(root/'Test.dll')],check=True)

# Both documented JSON and Markdown dispatch use rewards, never combat_rewards.
for filename in ['McpMod.StateBuilder.cs','McpMod.MultiplayerState.cs']:
 if (a.source_root/filename).exists():
  assert '["state_type"] = "combat_rewards"' not in (a.source_root/filename).read_text(), 'Inconsistent reward state key'
