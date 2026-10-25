#!/usr/bin/env python3
"""Compile actual selection actions/serializers against simulated UI. No game proof."""
import argparse,json,subprocess,tempfile
from pathlib import Path
from test_missing_actions import method
ROOT=Path(__file__).resolve().parents[1]
ACTIONS=['ExecuteSelectCardReward','ExecuteSkipCardReward','ExecuteSelectCard','ExecuteConfirmSelection','ExecuteCancelSelection','ExecuteSelectBundle','ExecuteConfirmBundleSelection','ExecuteCancelBundleSelection','ExecuteCombatSelectCard','ExecuteCombatConfirmSelection','ExecuteSelectRelic','ExecuteSkipRelicSelection','ExecuteClaimTreasureRelic']
STATES=['BuildCardRewardState','BuildChooseCardState','BuildHandSelectState','BuildBundleSelectState','BuildRelicSelectState','BuildTreasureState']
STUBS=r'''
using System;using System.Collections.Generic;using System.Linq;using System.Text.Json;
namespace Godot {
 public class Control {public bool Visible=true,InTree=true;public int Clicks;public List<Control> Children=new();public Dictionary<string,Control> Nodes=new();public bool IsVisibleInTree()=>InTree;public T? GetNodeOrNull<T>(string n) where T:Control=>Nodes.GetValueOrDefault(n) as T;public Variant Get(string n)=>new();public void EmitSignal(string n,Control c){c.Clicks++;}}
 public class Variant{public enum Type{Nil,String};public Type VariantType=Type.Nil;public string AsString()=>"prompt";}
 public class SceneTree{public Control Root=new();}public static class Engine{public static SceneTree Tree=new();public static object GetMainLoop()=>Tree;}
}
class NClickableControl:Godot.Control{public bool IsEnabled=true;public void ForceClick()=>Clicks++;}
class NConfirmButton:NClickableControl{}class NBackButton:NClickableControl{}
class CardModel{public string Title="Card";}class NCardHolder:Godot.Control{public CardModel? CardModel=new();public bool IsEnabled=true,IsSelected;public static class SignalName{public const string Pressed="pressed";}}
class NGridCardHolder:NCardHolder{}class NSelectedHandCardHolder:NCardHolder{}class NPreviewCardHolder:NCardHolder{}
class NCardGrid:Godot.Control{public static class SignalName{public const string HolderPressed="pressed";}}
class NCardGridSelectionScreen:Godot.Control{}class NChooseACardSelectionScreen:Godot.Control{}class NCardRewardSelectionScreen:Godot.Control{}
class NCardRewardAlternativeButton:NClickableControl{}class NChooseABundleSelectionScreen:Godot.Control{}class NChooseARelicSelection:Godot.Control{}
class NOverlayStack{public static NOverlayStack? Instance=new();public Godot.Control? Screen;public Godot.Control? Peek()=>Screen;}
class NCardBundle:Godot.Control{public List<CardModel> Bundle=new(){new()};public NClickableControl Hitbox=new();}
class NPlayerHand:Godot.Control{public static NPlayerHand? Instance;public bool IsInCardSelection=true;public enum Mode{SimpleSelect,UpgradeSelect};public Mode CurrentMode;public List<NCardHolder> ActiveHolders=new();}
class RelicModel{public (string Entry,int Dummy) Id=("RELIC",0);public string Title="Relic",DynamicDescription="desc",Rarity="Common";public object HoverTipsExcludingRelic=new();}class Relic{public RelicModel? Model=new();}
class NRelicBasicHolder:NClickableControl{public Relic? Relic=new();}class NTreasureRoomRelicHolder:NRelicBasicHolder{}class NTreasureRoomRelicCollection:Godot.Control{}
class NTreasureRoom:Godot.Control{public NConfirmButton ProceedButton=new();}class TreasureRoom{}
class Player{public Character Character=new();public Creature Creature=new();public int Gold=7;}class Character{public string Title="Hero";}class Creature{public int CurrentHp=20,MaxHp=30;}class RunState{}static class LocalContext{public static Player? GetMe(RunState s)=>new();}
static class Test{
 static IEnumerable<Godot.Control> Walk(Godot.Control c){foreach(var x in c.Children.Concat(c.Nodes.Values).Distinct()){yield return x;foreach(var y in Walk(x))yield return y;}}
 static List<T> FindAll<T>(Godot.Control c) where T:Godot.Control=>Walk(c).OfType<T>().ToList();static List<T> FindAllSortedByPosition<T>(Godot.Control c) where T:Godot.Control=>FindAll<T>(c);static T? FindFirst<T>(Godot.Control c) where T:Godot.Control=>FindAll<T>(c).FirstOrDefault();
 static bool IsControlVisibleOrActionable(NClickableControl? c)=>c!=null&&c.IsEnabled&&c.Visible&&c.IsVisibleInTree();static bool IsNodeVisible(Godot.Control c)=>c.Visible&&c.IsVisibleInTree();
 static bool IsCardHolderSelectable(NCardHolder h)=>h.CardModel!=null&&h.IsEnabled&&IsNodeVisible(h);static void AddCardHolderState(Dictionary<string,object?> d,NCardHolder h){d["can_select"]=IsCardHolderSelectable(h);}
 static Dictionary<string,object?> BuildCardInfo(CardModel c)=>new(){["name"]=c.Title};static string SafeGetCardDescription(CardModel c,object? pile=null)=>"desc";static object BuildHoverTips(object o)=>o;static string StripRichTextTags(string s)=>s;static string? SafeGetText(Func<string?> f)=>f();
 static Dictionary<string,object?> Error(string s)=>new(){["status"]="error",["error"]=s};static bool Ok(Dictionary<string,object?> d)=>d.GetValueOrDefault("status") is "ok";static Dictionary<string,JsonElement> Id(int i,string k="index")=>new(){[k]=JsonSerializer.SerializeToElement(i)};
 static List<Dictionary<string,object?>> Items(Dictionary<string,object?> s,string k)=>(List<Dictionary<string,object?>>)s[k]!;static int Checks;static void Check(bool b,string m){Checks++;if(!b)throw new Exception(m);}
'''
TESTS=r'''
 static void Main(){var run=new RunState();
 var rewards=new NCardRewardSelectionScreen();NOverlayStack.Instance!.Screen=rewards;var hidden=new NCardHolder{Visible=false};var detached=new NCardHolder{InTree=false};var empty=new NCardHolder{CardModel=null};var real=new NCardHolder();rewards.Children.AddRange(new Godot.Control[]{empty,hidden,detached,real});
 Check(Items(BuildCardRewardState(rewards),"cards").Count==1,"reward state filters empty and invisible");Check(Ok(ExecuteSelectCardReward(Id(0,"card_index")))&&real.Clicks==1&&hidden.Clicks==0&&empty.Clicks==0,"reward advertised index matches action");Check(!Ok(ExecuteSelectCardReward(Id(1,"card_index"))),"reward upper bound");
 real.IsEnabled=false;Check(Items(BuildCardRewardState(rewards),"cards")[0]["can_select"] is false&&!Ok(ExecuteSelectCardReward(Id(0,"card_index")))&&real.Clicks==1,"disabled reward cannot emit press");real.IsEnabled=true;
 var alt=new NCardRewardAlternativeButton{InTree=false};rewards.Children.Add(alt);Check(BuildCardRewardState(rewards)["can_skip"] is false&&!Ok(ExecuteSkipCardReward())&&alt.Clicks==0,"hidden reward skip");alt.InTree=true;alt.IsEnabled=false;Check(!Ok(ExecuteSkipCardReward()),"disabled reward skip");alt.IsEnabled=true;Check(Ok(ExecuteSkipCardReward())&&alt.Clicks==1,"reward skip success");
 var grid=new NCardGridSelectionScreen();NOverlayStack.Instance.Screen=grid;var gridUi=new NCardGrid();var g0=new NGridCardHolder{CardModel=null};var g1=new NGridCardHolder();grid.Children.AddRange(new Godot.Control[]{gridUi,g0,g1});
 Check(Ok(ExecuteSelectCard(Id(0)))&&g1.Clicks==1&&g0.Clicks==0,"grid skips empty index");g1.IsEnabled=false;Check(!Ok(ExecuteSelectCard(Id(0)))&&g1.Clicks==1,"disabled grid");g1.IsEnabled=true;g1.InTree=false;Check(!Ok(ExecuteSelectCard(Id(0))),"hidden grid");g1.InTree=true;grid.Nodes["%PreviewContainer"]=new Godot.Control();Check(!Ok(ExecuteSelectCard(Id(0))),"preview blocks selection");grid.Nodes.Clear();
 var confirm=new NConfirmButton{Visible=false};var close=new NBackButton{InTree=false};grid.Nodes["%Confirm"]=confirm;grid.Nodes["%Close"]=close;Check(!Ok(ExecuteConfirmSelection())&&confirm.Clicks==0,"hidden confirm");Check(!Ok(ExecuteCancelSelection())&&close.Clicks==0,"hidden cancel");confirm.Visible=true;close.InTree=true;Check(Ok(ExecuteConfirmSelection())&&confirm.Clicks==1,"confirm success");Check(Ok(ExecuteCancelSelection())&&close.Clicks==1,"cancel success");
 var choose=new NChooseACardSelectionScreen();NOverlayStack.Instance.Screen=choose;choose.Children.AddRange(new Godot.Control[]{g0,g1});var skip=new NClickableControl{InTree=false};choose.Nodes["SkipButton"]=skip;Check(Items(BuildChooseCardState(choose,run),"cards").Count==1,"choose empty filter");Check(Ok(ExecuteSelectCard(Id(0)))&&g1.Clicks==2,"choose index");Check(BuildChooseCardState(choose,run)["can_skip"] is false&&!Ok(ExecuteCancelSelection()),"choose hidden skip");
 var bundles=new NChooseABundleSelectionScreen();NOverlayStack.Instance.Screen=bundles;var bh=new NCardBundle{Visible=false};var bd=new NCardBundle();bd.Hitbox.IsEnabled=false;var bv=new NCardBundle();bundles.Children.AddRange(new Godot.Control[]{bh,bd,bv});var bs=Items(BuildBundleSelectState(bundles,run),"bundles");Check(bs.Count==2&&bs[0]["can_select"] is false&&bs[1]["can_select"] is true,"bundle stable visible indices");Check(!Ok(ExecuteSelectBundle(Id(0)))&&bd.Hitbox.Clicks==0,"disabled bundle rejected without reindex");Check(Ok(ExecuteSelectBundle(Id(1)))&&bv.Hitbox.Clicks==1,"bundle state index action matches");
 bv.Hitbox.InTree=false;Check(!Ok(ExecuteSelectBundle(Id(1))),"bundle hidden hitbox reject");bv.Hitbox.InTree=true;
 var bundlePreview=new Godot.Control();bundles.Nodes["%BundlePreviewContainer"]=bundlePreview;bs=Items(BuildBundleSelectState(bundles,run),"bundles");Check(bs.All(b=>b["can_select"] is false)&&!Ok(ExecuteSelectBundle(Id(1)))&&bv.Hitbox.Clicks==1,"bundle preview blocks advertised readiness and selection");bundlePreview.Visible=false;bs=Items(BuildBundleSelectState(bundles,run),"bundles");Check(bs[0]["can_select"] is false&&bs[1]["can_select"] is true&&Ok(ExecuteSelectBundle(Id(1)))&&bv.Hitbox.Clicks==2,"closing bundle preview restores readiness without reindexing");
 var bc=new NConfirmButton{InTree=false};var bx=new NBackButton{Visible=false};bundles.Nodes["%Confirm"]=bc;bundles.Nodes["%Cancel"]=bx;var bstate=BuildBundleSelectState(bundles,run);Check(bstate["can_confirm"] is false&&!Ok(ExecuteConfirmBundleSelection()),"hidden bundle confirm");Check(bstate["can_cancel"] is false&&!Ok(ExecuteCancelBundleSelection()),"hidden bundle cancel");bc.InTree=true;bx.Visible=true;Check(Ok(ExecuteConfirmBundleSelection())&&Ok(ExecuteCancelBundleSelection()),"bundle controls success");
 var hand=new NPlayerHand();NPlayerHand.Instance=hand;hand.ActiveHolders.AddRange(new[]{empty,real});Check(Items(BuildHandSelectState(hand,run),"cards").Count==1,"hand empty filter");Check(Ok(ExecuteCombatSelectCard(Id(0,"card_index")))&&real.Clicks==2,"hand advertised index");real.IsEnabled=false;Check(!Ok(ExecuteCombatSelectCard(Id(0,"card_index"))),"hand disabled reject");var hc=new NConfirmButton{InTree=false};hand.Nodes["%SelectModeConfirmButton"]=hc;Check(BuildHandSelectState(hand,run)["can_confirm"] is false&&!Ok(ExecuteCombatConfirmSelection()),"hand hidden confirm");hc.InTree=true;Check(Ok(ExecuteCombatConfirmSelection())&&hc.Clicks==1,"hand confirm success");
 var relics=new NChooseARelicSelection();NOverlayStack.Instance.Screen=relics;var rn=new NRelicBasicHolder{Relic=null};var rh=new NRelicBasicHolder{InTree=false};var rd=new NRelicBasicHolder{IsEnabled=false};var rv=new NRelicBasicHolder();relics.Children.AddRange(new Godot.Control[]{rn,rh,rd,rv});Check(Items(BuildRelicSelectState(relics,run),"relics").Count==1,"relic filters");Check(Ok(ExecuteSelectRelic(Id(0)))&&rv.Clicks==1&&rn.Clicks==0,"relic matching index");relics.Nodes["SkipButton"]=skip;Check(BuildRelicSelectState(relics,run)["can_skip"] is false&&!Ok(ExecuteSkipRelicSelection()),"relic hidden skip");
 var treasure=new NTreasureRoom();Godot.Engine.Tree.Root.Children.Add(treasure);var collection=new NTreasureRoomRelicCollection();treasure.Nodes["%RelicCollection"]=collection;var tn=new NTreasureRoomRelicHolder{Relic=null};var th=new NTreasureRoomRelicHolder{InTree=false};var tv=new NTreasureRoomRelicHolder();collection.Children.AddRange(new Godot.Control[]{tn,th,tv});Check(Items(BuildTreasureState(new(),run),"relics").Count==1,"treasure filters empty hidden");Check(Ok(ExecuteClaimTreasureRelic(Id(0)))&&tv.Clicks==1&&tn.Clicks==0,"treasure matching index");collection.InTree=false;Check(!Ok(ExecuteClaimTreasureRelic(Id(0)))&&!BuildTreasureState(new(),run).ContainsKey("relics"),"hidden collection rejects");var chest=new NClickableControl{InTree=false};treasure.Nodes["Chest"]=chest;Check(!BuildTreasureState(new(),run).ContainsKey("message")&&chest.Clicks==0,"hidden chest is not auto-clicked");treasure.ProceedButton.InTree=false;Check(BuildTreasureState(new(),run)["can_proceed"] is false,"hidden treasure proceed");
 Console.WriteLine($"PASS: {Checks} compiled selection checks");}
}
'''
def main():
 p=argparse.ArgumentParser();p.add_argument('--dotnet',default='/tmp/sts-dotnet/dotnet');p.add_argument('--revision');p.add_argument('--mutation', choices=['reward-filter','bundle-reindex','treasure-null','hand-null','hidden-confirm']);a=p.parse_args()
 def source(f):return subprocess.check_output(['git','-C',str(ROOT),'show',a.revision+':'+f],text=True) if a.revision else (ROOT/f).read_text()
 actions='\n'.join(method(source('McpMod.Actions.cs'),n) for n in ACTIONS)
 states='\n'.join(method(source('McpMod.StateBuilder.cs'),n) for n in STATES)
 mutations={
  'reward-filter':('holder.CardModel != null && holder.Visible && holder.IsVisibleInTree()', 'true'),
  'bundle-reindex':('bundle.Visible && bundle.IsVisibleInTree()', 'bundle.Visible && bundle.IsVisibleInTree() && bundle.Hitbox.IsEnabled'),
  'treasure-null':('h.Relic?.Model != null && h.IsEnabled', 'h.IsEnabled'),
  'hand-null':('holder.CardModel != null', 'true'),
  'hidden-confirm':('IsControlVisibleOrActionable(mainConfirm)', 'mainConfirm?.IsEnabled == true'),
 }
 if a.mutation:
  before,after=mutations[a.mutation];assert before in actions
  if a.mutation=='hand-null':
   old=method(actions,'ExecuteCombatSelectCard');actions=actions.replace(old,old.replace(before,after))
  else:actions=actions.replace(before,after)
 code=STUBS+actions+'\n'+states+TESTS
 sdk=Path(a.dotnet).resolve().parent; csc=sorted((sdk/'sdk').glob('*/Roslyn/bincore/csc.dll'))[-1];refs=sorted((sdk/'packs/Microsoft.NETCore.App.Ref').glob('*/ref/net9.0'))[-1];ver=sorted((sdk/'shared/Microsoft.NETCore.App').iterdir())[-1].name
 with tempfile.TemporaryDirectory() as td:
  d=Path(td);(d/'Test.cs').write_text(code);(d/'Test.runtimeconfig.json').write_text(json.dumps({'runtimeOptions':{'tfm':'net9.0','framework':{'name':'Microsoft.NETCore.App','version':ver}}}))
  subprocess.run([a.dotnet,str(csc),'-nologo','-nullable:enable','-target:exe',f'-out:{d}/Test.dll',*[f'-r:{x}' for x in refs.glob('*.dll')],str(d/'Test.cs')],check=True)
  subprocess.run([a.dotnet,str(d/'Test.dll')],check=True)
if __name__=='__main__':main()
