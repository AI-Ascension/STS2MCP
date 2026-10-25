#!/usr/bin/env python3
"""Compile complete shop/card-selection serializers with simulated UI and models.
Shared card serialization helpers remain production source; no proprietary game test.
"""
import json, os, subprocess, tempfile
from pathlib import Path
import test_card_metadata as card
ROOT=Path(__file__).resolve().parents[1]
source=(ROOT/'McpMod.StateBuilder.cs').read_text()
stubs=card.STUBS
stubs=stubs.replace('public int CombatId;', 'public int CombatId, CurrentHp=20, MaxHp=30;')
stubs=stubs.replace('public Creature Creature=new() {CombatState=new()};','public Creature Creature=new() {CombatState=new()}; public Character Character=new(); public int Gold=50; public List<object?> PotionSlots=new(){null};')
stubs=stubs.replace('class Control { public bool Visible=true, InTree=true; }', '''class Control {
 public bool Visible=true, InTree=true; public List<Control> Children=new(); public Dictionary<string,Control> Nodes=new();
 public bool IsVisibleInTree()=>InTree; public T? GetNodeOrNull<T>(string n) where T:Control => Nodes.GetValueOrDefault(n) as T;
 public Control? GetNodeOrNull(string n)=>Nodes.GetValueOrDefault(n); public Godot.Variant Get(string n)=>new();
}''')
extra=r'''
namespace Godot { class Control:global::Control {} class Variant { public enum Type {Nil,String}; public Type VariantType=Type.Nil; public string AsString()=>"Prompt"; } }
class Character { public string Title="Hero"; }
class RunState { public Player? Player=new(); }
static class LocalContext { public static Player? GetMe(RunState r)=>r.Player; }
class NClickableControl:Godot.Control {public bool IsEnabled=true;}
class NBackButton:NClickableControl {}
class NConfirmButton:NClickableControl {}
class Entry { public int Cost=42; public bool IsStocked=true,EnoughGold=true,IsOnSale; public Creation? CreationResult=new(); public Item? Model=new(); }
class Creation { public CardModel Card=new(); }
class Item { public (string Entry,int Other) Id=("ITEM",0); public string Title="Item",DynamicDescription="Description"; public object HoverTipsExcludingRelic=new(),ExtraHoverTips=new(); }
class Inventory { public List<Entry> CardEntries=new(),RelicEntries=new(),PotionEntries=new(); public Entry? CardRemovalEntry; }
class MerchantRoom { public Inventory? Inventory; }
class NMerchantRoom:Godot.Control { public static NMerchantRoom? Instance; public UIInventory? Inventory=new(); public NConfirmButton? ProceedButton; }
class UIInventory {public bool IsOpen;}
class NCardGridSelectionScreen:Godot.Control {public int MinSelect=1,MaxSelect=2;}
class NDeckTransformSelectScreen:NCardGridSelectionScreen {}
class NDeckUpgradeSelectScreen:NCardGridSelectionScreen {}
class NDeckCardSelectScreen:NCardGridSelectionScreen {}
class NSimpleCardSelectScreen:NCardGridSelectionScreen {}
class NGridCardHolder:Godot.Control { public CardModel? CardModel=new(); public bool IsSelected,IsEnabled=true; }
class NPreviewCardHolder:Godot.Control {public CardModel? CardModel=new();}
'''
stubs=stubs.replace('class Test {',extra+'''class Test {
 static IEnumerable<Control> Walk(Control c) { foreach(var child in c.Children) {yield return child; foreach(var x in Walk(child)) yield return x;} }
 static List<T> FindAll<T>(Control c) where T:Control=>Walk(c).OfType<T>().ToList();
 static List<T> FindAllSortedByPosition<T>(Control c) where T:Control=>FindAll<T>(c);
 static T? FindFirst<T>(Control c) where T:Control=>FindAll<T>(c).FirstOrDefault();
 static bool IsControlVisibleInTree(NClickableControl? c)=>c!=null && c.Visible && c.InTree;
 static string StripRichTextTags(string s)=>s;
''')
names=['BuildShopState','BuildCardSelectState','BuildCardInfo','GetCostDisplay','GetStarCostDisplay','GetMemberValue','GetBoolMemberValue','AddCardHolderState','IsCardHolderSelectable']
helpers=(ROOT/'McpMod.Helpers.cs').read_text()
code=stubs+'\n'.join(card.extract(source,n) for n in names)+card.extract(helpers,'IsControlVisibleOrActionable')+card.extract(helpers,'SafeBuildUpgradedCardPreview')+card.extract(helpers,'SafeGetCardUpgradePreviewDescription')+r'''
 static int count; static void Check(bool b,string m){count++;if(!b)throw new Exception(m);}
 static List<Dictionary<string,object?>> List(Dictionary<string,object?> s,string k)=>(List<Dictionary<string,object?>>)s[k]!;
 static void Main(){
 var run=new RunState(); var room=new MerchantRoom(); NMerchantRoom.Instance=new(){ProceedButton=new()};
 var state=BuildShopState(room,run); Check(List(state,"items").Count==0 && state.ContainsKey("error"),"null inventory readiness");
 Check(state["can_proceed"] is true,"visible proceed without inventory");
 room.Inventory=new(){CardEntries=new(){new()},RelicEntries=new(){new(){EnoughGold=false}},PotionEntries=new(){new(){IsStocked=false}},CardRemovalEntry=new()};
 state=BuildShopState(room,run); var items=List(state,"items"); Check(items.Count==4,"all categories");
 for(int i=0;i<4;i++)Check((int)items[i]["index"]! ==i,"stable cross-category index");
 Check((int)items[0]["cost"]! ==42 && (string?)items[0]["card_cost"]=="2","merchant versus energy price");
 Check(items[0].ContainsKey("card_upgrade_preview_description") && items[0].ContainsKey("card_star_cost"),"shared card metadata");
 Check(items[0]["can_purchase"] is true && items[1]["can_purchase"] is false && items[2]["can_purchase"] is false && items[3]["can_purchase"] is true,"purchase readiness");
 var back=new NBackButton(); NMerchantRoom.Instance.Children.Add(back);NMerchantRoom.Instance.Inventory!.IsOpen=true;NMerchantRoom.Instance.ProceedButton!.Visible=false;
 state=BuildShopState(room,run);Check(state["can_proceed"] is true && state["can_close_inventory"] is true,"inventory back proceeds");
 back.InTree=false;Check(BuildShopState(room,run)["can_proceed"] is false,"hidden back cannot proceed");
 NMerchantRoom.Instance=null;Check(BuildShopState(room,run)["can_proceed"] is false,"absent merchant UI");
 var screen=new NDeckUpgradeSelectScreen(); var selected=new NGridCardHolder(){IsSelected=true};screen.Children.AddRange(new Control[]{selected,new NGridCardHolder(){IsEnabled=false},new NGridCardHolder(){CardModel=null}});
 state=BuildCardSelectState(screen,run);Check((string?)state["screen_type"]=="upgrade","screen kind");
 Check(List(state,"cards").Count==2 && (int)state["selected_count"]! ==1,"selected count excludes empty holders");
 Check((int)state["min_select"]! ==1 && (int)state["max_select"]! ==2,"selection bounds");
 Check(List(state,"cards")[1]["can_select"] is false,"disabled grid card");
 Check(List(state,"selected_cards")[0].ContainsKey("upgrade_preview_cost"),"selected metadata");
 var preview=new Godot.Control();screen.Nodes["%PreviewContainer"]=preview;screen.Children.AddRange(new Control[]{new NPreviewCardHolder(),new NPreviewCardHolder(){Visible=false},new NPreviewCardHolder(){InTree=false},new NPreviewCardHolder(){CardModel=null}});
 state=BuildCardSelectState(screen,run);Check(state["preview_showing"] is true && List(state,"preview_cards").Count==1,"visible nonempty preview cards");
 Check(List(state,"cards").All(c=>c["can_select"] is false) && List(state,"selected_cards").All(c=>c["can_select"] is false),"preview blocks all grid and selected-card actions");
 preview.Visible=false;Check(List(BuildCardSelectState(screen,run),"preview_cards").Count==0,"hidden preview container");
 Check(BuildCardSelectState(screen,run)["can_confirm"] is false,"absent confirmation");
 var close=new NBackButton(){Visible=false};screen.Nodes["%Close"]=close;
 Check(BuildCardSelectState(screen,run)["can_cancel"] is false,"hidden close is not actionable");
 var confirm=new NConfirmButton(){Visible=false};screen.Nodes["Confirm"]=confirm;
 Check(BuildCardSelectState(screen,run)["can_confirm"] is false,"hidden main confirm is not actionable");
 preview.Visible=true;var previewCancel=new NBackButton();preview.Nodes["Cancel"]=previewCancel;
 Check(BuildCardSelectState(screen,run)["can_cancel"] is true,"preview cancel readiness");
 previewCancel.IsEnabled=false;Check(BuildCardSelectState(screen,run)["can_cancel"] is false,"disabled preview cancellation");
 run.Player=null;Check(!BuildShopState(room,run).ContainsKey("player") && !BuildCardSelectState(screen,run).ContainsKey("player"),"missing player tolerated");
 Console.WriteLine($"PASS: {count} complete shop/card-selection serializer checks (simulated UI)");
 }
}
'''
dotnet=os.environ.get('DOTNET','/tmp/sts-dotnet/dotnet'); sdk=Path(dotnet).resolve().parent
compiler=sorted((sdk/'sdk').glob('9.*/Roslyn/bincore/csc.dll'))[-1];refs=sorted((sdk/'packs/Microsoft.NETCore.App.Ref').glob('9.*/ref/net9.0'))[-1]
with tempfile.TemporaryDirectory(prefix='sts-shop-selection-') as tmp:
 p=Path(tmp);(p/'Test.cs').write_text(code)
 subprocess.run([dotnet,str(compiler),'-nologo','-nullable:enable','-nowarn:0649','-langversion:12','-target:exe',f'-out:{p}/Test.dll',*[f'-r:{r}' for r in refs.glob('*.dll')],str(p/'Test.cs')],check=True)
 (p/'Test.runtimeconfig.json').write_text(json.dumps({'runtimeOptions':{'tfm':'net9.0','framework':{'name':'Microsoft.NETCore.App','version':'9.0.0'}}}))
 subprocess.run([dotnet,str(p/'Test.dll')],check=True)
