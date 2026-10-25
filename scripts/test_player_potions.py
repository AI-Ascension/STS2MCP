#!/usr/bin/env python3
"""Compile production player/potion methods against simulated models, not game DLLs."""
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
source = (a.source_root / 'McpMod.StateBuilder.cs').read_text()
methods = []
for name in ['BuildPlayerState', 'GetPotionUseBlockedReason', 'BuildPotionTargetRefs', 'BuildEnemyTargetRefs']:
    m = re.search(r'    private static [^\n]+\b' + name + r'\(', source)
    if not m:
        raise SystemExit(f'Missing method {name}')
    end = source.index('    private static ', m.start() + 10)
    methods.append(source[m.start():end])
action_source=(a.source_root / 'McpMod.Actions.cs').read_text()
start=action_source.index('    private static Dictionary<string, object?> ExecuteUsePotion(')
end=action_source.index('    private static ',start+10)
methods.append(action_source[start:end])
stubs = r'''
using System; using System.Collections.Generic; using System.Linq; using System.Text.Json;
enum TargetType { AnyEnemy, Self, None, AnyAlly, AnyPlayer }
enum PotionUsage { CombatOnly, AnyTime, Automatic }
enum PileType { Draw, Discard, Exhaust }
class Id { public string Entry="id"; }
class Text { public void Add(string key, object value) {} }
class Character { public string Title="Character"; public bool ShouldAlwaysShowStarCounter; public Character CardPool => this; }
class Monster { public Id Id=new(); public string Title="Monster"; }
class Creature { public int CurrentHp=50, MaxHp=60, Block, CombatId; public bool IsDead; public bool IsAlive=>!IsDead; public Monster? Monster; public CombatState? CombatState; }
class CombatState { public List<Creature> Enemies=new(); }
class Card { }
class Pile { public List<Card> Cards=new(); }
class Orb { public Text SmartDescription=new(); public Player Owner=new(); public int PassiveVal, EvokeVal; public Id Id=new(); public string Title="Orb"; public object HoverTips=new(); }
class OrbQueue { public int Capacity; public List<Orb> Orbs=new(); }
class PlayerCombatState { public int Energy { get { if(!CombatManager.Instance.IsInProgress) throw new Exception("stale energy access"); return 3; } } public int MaxEnergy=>3; public int Stars; public Pile Hand=new(), DrawPile=new(), DiscardPile=new(), ExhaustPile=new(); public OrbQueue OrbQueue=new(); }
class Relic { public Id Id=new(); public string Title="Relic", DynamicDescription="desc", Rarity="Rare"; public bool ShowCounter; public int DisplayAmount; public object HoverTipsExcludingRelic=new(); }
class PotionModel { public Id Id=new(); public string Title="Potion", DynamicDescription="desc", Rarity="Common"; public Player Owner=null!; public bool IsQueued; public bool PassesCustomUsabilityCheck=true; public PotionUsage Usage=PotionUsage.AnyTime; public TargetType TargetType=TargetType.Self; public object ExtraHoverTips=new(); public int Uses; public Creature? LastTarget; public void EnqueueManualUse(Creature? c){Uses++;LastTarget=c;} }
class Player { public Creature Creature=new(); public PlayerCombatState? PlayerCombatState; public Character Character=new(); public int Gold=99, MaxPotionCount=5; public List<Relic> Relics=new(); public List<PotionModel?> PotionSlots=new(); public List<Dictionary<string,object?>> Deck=new(); public PotionModel? GetPotionAtSlotIndex(int i)=>PotionSlots[i]; }
class CombatManager { public static CombatManager Instance=new(); public bool IsInProgress, IsPlayPhase=true, PlayerActionsDisabled; }
class Test {
 static Dictionary<string,object?> Error(string message)=>new(){["status"]="error",["message"]=message};
 static Creature? ResolveTarget(CombatState c,string id)=>c.Enemies.FirstOrDefault(e=>e.IsAlive);
 static Dictionary<string,JsonElement> Input(string s)=>JsonSerializer.Deserialize<Dictionary<string,JsonElement>>(s)!;

 static string? SafeGetText<T>(Func<T> f)=>f()?.ToString();
 static object BuildHoverTips(object x)=>x;
 static object BuildPowersState(Creature x)=>new object();
 static Dictionary<string,object?> BuildCardState(Card c,int i)=>new();
 static Dictionary<string,object?> BuildCardState(Card c,int i,Player p)=>new();
 static object BuildPileCardList(List<Card> c,PileType p)=>c;
 static List<Dictionary<string,object?>> BuildDeckCardList(Player p)=>p.Deck;
 static int count;
 static void Check(bool value,string name) { count++; if(!value)throw new Exception(name); }
 static void Reason(PotionModel p,string? expected,string label) => Check(GetPotionUseBlockedReason(p,BuildPotionTargetRefs(p,p.Owner))==expected,label);
'''
tests = r'''
 static void Main() {
  var player=new Player { PlayerCombatState=new() }; var potion=new PotionModel { Owner=player };
  player.PotionSlots.AddRange(new PotionModel?[]{null,potion,null}); player.Relics.Add(new Relic());
  var state=BuildPlayerState(player);
  Check(!state.ContainsKey("energy"),"lingering combat state skips energy hooks");
  Check((int)state["deck_count"]! == 0 && !state.ContainsKey("deck"),"empty deck count");
  Check((int)state["max_potion_slots"]! == 5,"slot capacity not occupied count");
  Check((string)((List<Dictionary<string,object?>>)state["relics"]!)[0]["rarity"]! == "Rare","relic rarity");
  var ps=((List<Dictionary<string,object?>>)state["potions"]!)[0];
  Check((int)ps["slot"]! == 1,"sparse potion slot retains index");
  Check((bool)ps["can_use"]! && (bool)ps["can_discard"]!,"anytime potion readiness");
  Check((string)ps["usage"]! == "AnyTime" && (string)ps["rarity"]! == "Common","potion metadata");
  player.Deck.Add(new() { ["id"]="deck" }); state=BuildPlayerState(player);
  Check((int)state["deck_count"]! == 1 && ReferenceEquals(state["deck"],player.Deck),"permanent deck");
  potion.IsQueued=true; Reason(potion,"AlreadyQueued","queued takes precedence"); state=BuildPlayerState(player); ps=((List<Dictionary<string,object?>>)state["potions"]!)[0];
  Check(!(bool)ps["can_use"]! && !(bool)ps["can_discard"]! && (string)ps["discard_blocked_reason"]! == "AlreadyQueued","queued state metadata");
  potion.IsQueued=false; player.Creature.IsDead=true; Reason(potion,"PlayerDead","dead"); player.Creature.IsDead=false;
  potion.PassesCustomUsabilityCheck=false; Reason(potion,"CustomUsabilityCheckFailed","custom check"); potion.PassesCustomUsabilityCheck=true;
  potion.Usage=PotionUsage.Automatic; Reason(potion,"Automatic","automatic");
  potion.Usage=PotionUsage.CombatOnly; Reason(potion,"CombatOnly","combat only outside combat");
  CombatManager.Instance.IsInProgress=true; CombatManager.Instance.IsPlayPhase=false; Reason(potion,"NotInPlayPhase","not play phase");
  CombatManager.Instance.IsPlayPhase=true; CombatManager.Instance.PlayerActionsDisabled=true; Reason(potion,"PlayerActionsDisabled","disabled actions");
  CombatManager.Instance.PlayerActionsDisabled=false; potion.TargetType=TargetType.AnyEnemy; Reason(potion,"NoValidTargets","no combat state");
  player.Creature.CombatState=new(); var enemy=new Creature { Monster=new(), CombatId=7 }; player.Creature.CombatState.Enemies.Add(enemy);
  player.Creature.CombatState.Enemies.Add(new Creature { Monster=new(), IsDead=true }); player.Creature.CombatState.Enemies.Add(new Creature { Monster=new(), CombatId=9 });
  var targets=BuildPotionTargetRefs(potion,player); Check(targets.Count==2,"dead enemies excluded");
  Check((string)targets[0]["entity_id"]! == "id_0" && (string)targets[1]["entity_id"]! == "id_1","same-model target indices");
  Check((int)targets[1]["combat_id"]! == 9,"combat ID retained"); Reason(potion,null,"usable enemy potion");
  state=BuildPlayerState(player); ps=((List<Dictionary<string,object?>>)state["potions"]!)[0];
  Check((bool)ps["requires_target"]! && ((List<Dictionary<string,object?>>)ps["valid_targets"]!).Count==2,"targets serialized");
  Check((int)state["energy"]! == 3,"live combat energy");
  potion.TargetType=TargetType.Self; Check(BuildPotionTargetRefs(potion,player).Count==0,"self potion no enemy choices");
  CombatManager.Instance.IsInProgress=false; potion.Usage=PotionUsage.AnyTime; potion.TargetType=TargetType.AnyEnemy;
  Reason(potion,"EnemyTargetRequiresCombat","enemy targeting outside combat"); Check(BuildPotionTargetRefs(potion,player).Count==0,"stale enemies hidden");
  var used=ExecuteUsePotion(player,Input("{\"slot\":1,\"target\":\"id_0\"}"));
  Check((string?)used["status"]=="error" && potion.Uses==0,"enemy-target action rejects stale out-of-combat target");
  potion.TargetType=TargetType.Self;used=ExecuteUsePotion(player,Input("{\"slot\":1}"));
  Check((string?)used["status"]=="ok" && potion.Uses==1 && ReferenceEquals(potion.LastTarget,player.Creature),"anytime self action outside combat");
  potion.IsQueued=true;used=ExecuteUsePotion(player,Input("{\"slot\":1}"));
  Check((string?)used["status"]=="error" && potion.Uses==1,"queued action prevented");
  potion.IsQueued=false;potion.TargetType=TargetType.AnyEnemy;CombatManager.Instance.IsInProgress=true;
  used=ExecuteUsePotion(player,Input("{\"slot\":1,\"target\":\"id_0\"}"));
  Check((string?)used["status"]=="ok" && potion.Uses==2 && ReferenceEquals(potion.LastTarget,enemy),"live enemy action allowed");
  Console.WriteLine($"PASS: {count} player/potion checks (simulated models)");
 }
}
'''
with tempfile.TemporaryDirectory(prefix='sts-player-test-') as tmp:
    root=Path(tmp); (root/'Program.cs').write_text(stubs+'\n'.join(methods)+tests)
    dotnet=shutil.which('dotnet')
    if not dotnet: raise SystemExit('The .NET 9 SDK is required on PATH')
    sdk_root=Path(dotnet).resolve().parent
    compiler=sorted((sdk_root/'sdk').glob('9.*/Roslyn/bincore/csc.dll'))[-1]
    references=sorted((sdk_root/'packs/Microsoft.NETCore.App.Ref').glob('9.*/ref/net9.0'))[-1]
    output=root/'Test.dll'
    subprocess.run([dotnet,str(compiler),'-nologo','-nullable:enable','-langversion:12','-nowarn:0649','-target:exe',f'-out:{output}',*[f'-r:{p}' for p in references.glob('*.dll')],str(root/'Program.cs')],check=True)
    (root/'Test.runtimeconfig.json').write_text(json.dumps({'runtimeOptions':{'tfm':'net9.0','framework':{'name':'Microsoft.NETCore.App','version':'9.0.0'}}}))
    subprocess.run([dotnet,str(output)],check=True)
