#!/usr/bin/env python3
"""Compile extracted card serializers against test doubles, without MSBuild/game DLLs.

This is a focused contract test, not game integration. Requires .NET 9 on PATH
(or DOTNET). --mutations verifies that representative regressions are rejected.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
NAMES = ['BuildEnemyTargetRefs', 'GetCostDisplay', 'GetStarCostDisplay', 'BuildCardInfo', 'BuildCardState',
         'BuildPileCardList', 'BuildDeckCardList', 'GetPlayerDeckCards',
         'GetMemberValue', 'GetBoolMemberValue', 'AddCardHolderState', 'IsCardHolderSelectable']


def extract(source, name):
    match = re.search(r'^    (?:private|internal) static .*?\b' + name + r'\(', source, re.M)
    if not match:
        raise AssertionError(f'missing method: {name}')
    end = re.search(r'^    (?:private|internal) static ', source[match.end():], re.M)
    return source[match.start():match.end() + end.start() if end else len(source) - 2]


STUBS = r'''
using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
enum PileType { None, Hand, Draw, Discard, Exhaust }
enum UnplayableReason { None, Energy }
enum TargetType { AnyEnemy, Self }
class CombatManager { public static CombatManager Instance = new(); public bool IsInProgress=true, IsPlayPhase=true, PlayerActionsDisabled; }
class Monster { public (string Entry,int Other) Id=("RAT",0); public string Title="Rat"; }
class Creature { public bool IsAlive=true; public int CombatId; public Monster? Monster=new(); public CombatState? CombatState; }
class CombatState { public List<Creature> Enemies=new(); }
class Energy { public bool CostsX; public int Amount = 2; public int GetAmountToSpend() => Amount; }
class CardModel {
 public (string Entry, int Other) Id = ("CARD", 0);
 public string Title = "Card", Type = "Attack", Rarity = "Rare", UpgradePreviewType = "Upgrade"; public TargetType TargetType=TargetType.AnyEnemy;
 public Energy EnergyCost = new(); public bool HasStarCostX; public int CurrentStarCost = -1;
 public int StarModifier = 1; public bool IsUpgraded; public bool IsUpgradable = true; public bool IsMutable = true;
 public int CurrentUpgradeLevel; public int MaxUpgradeLevel = 1; public bool FailClone;
 public List<Dictionary<string, object?>> HoverTips = new() { new() { ["name"] = "Exhaust" } };
 public UnplayableReason Reason;
 public int GetStarCostWithModifiers() => CurrentStarCost + StarModifier;
 public bool CanPlay(out UnplayableReason reason, out object? other) { reason=Reason; other=null; return Reason==UnplayableReason.None; }
 public object MutableClone() { if(FailClone) throw new Exception(); var c=(CardModel)MemberwiseClone(); c.EnergyCost=new Energy { CostsX=EnergyCost.CostsX, Amount=EnergyCost.Amount }; return c; }
 public CardModel ToMutable() => (CardModel)MutableClone();
 public void UpgradeInternal() { IsUpgraded=true; CurrentUpgradeLevel++; EnergyCost.Amount--; CurrentStarCost=2; }
 public string GetDescriptionForUpgradePreview() => "fallback";
}
class Player { public object? Deck {get;set;} public Creature Creature=new() {CombatState=new()}; }
class DeckContainer { public object Cards = new ArrayList(); }
class Control { public bool Visible=true, InTree=true; }
class EnabledControl : Control { public bool IsEnabled {get;set;} = true; public bool IsSelected {get;set;} = true; }
class FieldControl : Control { private bool _isSelected = true; public string IsEnabled = "not a boolean"; }
class ReflectionProbe { public int Property => 7; private string Field = "field"; public int Throwing => throw new Exception(); }
class Test {
 static string? SafeGetText(Func<object?> getter) { try {return getter()?.ToString();} catch {return null;} }
 static string SafeGetCardDescription(CardModel card, PileType pile=PileType.Hand) => $"{pile}:{card.CurrentUpgradeLevel}";
 static object BuildHoverTips(object tips) => tips;
 static bool IsNodeVisible(Control c) => c.Visible && c.InTree;
'''
TESTS = r'''
 static int checks;
 static void Check(bool condition, string message) { checks++; if(!condition) throw new Exception(message); }
 static void Main() {
  var card = new CardModel();
  var info = BuildCardInfo(card);
  foreach(var key in new[] {"id","name","type","cost","star_cost","description","rarity","is_upgraded","is_upgradable","current_upgrade_level","max_upgrade_level","upgrade_preview_type","upgrade_preview_cost","upgrade_preview_star_cost","upgrade_preview_description","keywords"}) Check(info.ContainsKey(key), key);
  Check((string?)info["cost"]=="2" && info["star_cost"]==null,"normal cost");
  Check((string?)info["upgrade_preview_cost"]=="1" && (string?)info["upgrade_preview_star_cost"]=="3", "preview costs");
  Check((string?)info["description"]=="None:0" && (string?)info["upgrade_preview_description"]=="None:1", "pile propagation");
  Check(card.EnergyCost.Amount==2 && card.CurrentUpgradeLevel==0 && !card.IsUpgraded,"preview must not mutate original");
  Check(ReferenceEquals(info["keywords"],card.HoverTips),"structured keywords");
  card.EnergyCost.CostsX=true; card.HasStarCostX=true;
  Check(GetCostDisplay(card)=="X" && GetStarCostDisplay(card)=="X","X costs");
  card.HasStarCostX=false; card.CurrentStarCost=0;
  Check(GetStarCostDisplay(card)=="1","modified zero star cost");
  Check((string?)BuildCardInfo(card)["star_cost"]=="1","serialized star cost");
  card.CurrentStarCost=-1; Check(GetStarCostDisplay(card)==null,"no star cost");
  card.IsUpgradable=false; info=BuildCardInfo(card);
  Check(info["upgrade_preview_cost"]==null && info["upgrade_preview_star_cost"]==null && info["upgrade_preview_description"]==null,"no upgrade preview");
  card.IsUpgradable=true; card.FailClone=true; info=BuildCardInfo(card);
  Check(info["upgrade_preview_cost"]==null && (string?)info["upgrade_preview_description"]=="fallback","failed clone fallback");
  card.FailClone=false; card.IsMutable=false; info=BuildCardInfo(card);
  Check((string?)info["upgrade_preview_description"]=="None:1" && card.CurrentUpgradeLevel==0,"immutable clone");
  foreach(var pile in new[]{PileType.Draw,PileType.Discard,PileType.Exhaust}) {
   var list=BuildPileCardList(new[]{card,card},pile);
   Check(list.Count==2 && (int)list[0]["index"]! ==0 && (int)list[1]["index"]! ==1,"pile indexes");
   Check((string?)list[0]["description"]==$"{pile}:0" && list[0].ContainsKey("upgrade_preview_cost"),"pile metadata");
  }
  Check(BuildPileCardList(Array.Empty<CardModel>(),PileType.Draw).Count==0,"empty pile");
  var handPlayer=new Player(); var hand=BuildCardState(card,4,handPlayer);
  Check((int)hand["index"]! ==4 && (string?)hand["description"]=="Hand:0" && hand.ContainsKey("upgrade_preview_cost"),"hand metadata");
  Check(hand["can_play"] is true && hand["unplayable_reason"]==null,"playable preserved");
  card.Reason=UnplayableReason.Energy; hand=BuildCardState(card,0,handPlayer);
  Check(hand["can_play"] is false && (string?)hand["unplayable_reason"]=="Energy","unplayable preserved");
  card.Reason=UnplayableReason.None;
  CombatManager.Instance.IsPlayPhase=false; hand=BuildCardState(card,0,handPlayer);
  Check(hand["can_play"] is false && (string?)hand["unplayable_reason"]=="NotInPlayPhase","enemy turn blocked");
  CombatManager.Instance.IsPlayPhase=true; CombatManager.Instance.PlayerActionsDisabled=true;
  hand=BuildCardState(card,0,handPlayer); Check(hand["can_play"] is false && (string?)hand["unplayable_reason"]=="PlayerActionsDisabled","disabled actions blocked");
  CombatManager.Instance.PlayerActionsDisabled=false; CombatManager.Instance.IsInProgress=false;
  Check(BuildCardState(card,0,handPlayer)["can_play"] is false,"out of combat blocked");
  CombatManager.Instance.IsInProgress=true;
  handPlayer.Creature.CombatState!.Enemies.AddRange(new[]{new Creature{CombatId=10},new Creature{IsAlive=false},new Creature{CombatId=12}});
  hand=BuildCardState(card,0,handPlayer); var targets=(List<Dictionary<string,object?>>)hand["valid_targets"]!;
  Check(hand["requires_target"] is true && targets.Count==2,"living enemy targets");
  Check((string?)targets[0]["entity_id"]=="RAT_0" && (string?)targets[1]["entity_id"]=="RAT_1" && (int)targets[1]["combat_id"]! ==12,"stable living target identities");
  card.TargetType=TargetType.Self; hand=BuildCardState(card,0,handPlayer);
  Check(hand["requires_target"] is false && ((List<Dictionary<string,object?>>)hand["valid_targets"]!).Count==0,"self does not require enemy");
  Check(BuildEnemyTargetRefs(null).Count==0,"null combat targets");
  var player=new Player(); Check(BuildDeckCardList(player).Count==0,"absent deck");
  player.Deck=new object(); Check(BuildDeckCardList(player).Count==0,"nonenumerable deck");
  player.Deck=new ArrayList{card,"ignore",card}; var deck=BuildDeckCardList(player);
  Check(deck.Count==2 && (int)deck[1]["index"]! ==1 && deck[0].ContainsKey("upgrade_preview_description"),"direct deck");
  player.Deck=new DeckContainer {Cards=new ArrayList{card}};
  Check(BuildDeckCardList(player).Count==1,"wrapped deck");
  var probe=new ReflectionProbe();
  Check((int)GetMemberValue(probe,"Property")! ==7,"property reflection");
  Check((string?)GetMemberValue(probe,"Field")=="field","private field reflection");
  Check(GetMemberValue(probe,"Missing")==null && GetMemberValue(probe,"Throwing")==null,"safe reflection");
  var holder=new EnabledControl(); info=new(); AddCardHolderState(info,holder);
  Check(info["is_selected"] is true && info["is_visible"] is true && info["can_select"] is true,"holder ready");
  holder.IsEnabled=false; AddCardHolderState(info,holder); Check(info["can_select"] is false,"disabled holder");
  holder.IsEnabled=true; holder.Visible=false; AddCardHolderState(info,holder); Check(info["can_select"] is false && info["is_visible"] is false,"hidden holder");
  holder.Visible=true; holder.InTree=false; Check(!IsCardHolderSelectable(holder),"detached holder");
  AddCardHolderState(info,new Control()); Check(info["is_selected"] is false && info["can_select"] is true,"missing optional properties");
  AddCardHolderState(info,new FieldControl()); Check(info["is_selected"] is true && info["can_select"] is true,"field selection and nonboolean enabled");
  Console.WriteLine($"PASS: {checks} extracted card metadata checks (test doubles)");
 }
}
'''


def run(source, dotnet):
    helpers = (ROOT/'McpMod.Helpers.cs').read_text()
    code = STUBS + '\n'.join(extract(source, n) for n in NAMES)
    code += extract(helpers, 'SafeBuildUpgradedCardPreview') + extract(helpers, 'SafeGetCardUpgradePreviewDescription') + TESTS
    sdk = Path(dotnet).resolve().parent
    compiler = sorted((sdk/'sdk').glob('9.*/Roslyn/bincore/csc.dll'))[-1]
    refs = sorted((sdk/'packs/Microsoft.NETCore.App.Ref').glob('9.*/ref/net9.0'))[-1]
    with tempfile.TemporaryDirectory(prefix='sts-card-metadata-') as tmp:
        root = Path(tmp)
        (root/'Test.cs').write_text(code)
        subprocess.run([dotnet,str(compiler),'-nologo','-nullable:enable','-langversion:12','-target:exe',f'-out:{root}/Test.dll', *[f'-r:{p}' for p in refs.glob('*.dll')],str(root/'Test.cs')],check=True, capture_output=True,text=True)
        (root/'Test.runtimeconfig.json').write_text(json.dumps({'runtimeOptions':{'tfm':'net9.0','framework':{'name':'Microsoft.NETCore.App','version':'9.0.0'}}}))
        return subprocess.run([dotnet,str(root/'Test.dll')],capture_output=True,text=True)


def main():
    p=argparse.ArgumentParser(); p.add_argument('--mutations',action='store_true'); args=p.parse_args()
    source=(ROOT/'McpMod.StateBuilder.cs').read_text()
    for name in ['BuildCardState','BuildPileCardList','BuildDeckCardList','BuildShopState','BuildCardRewardState','BuildCardSelectState','BuildChooseCardState','BuildBundleSelectState','BuildHandSelectState']:
        assert 'BuildCardInfo(card' in extract(source,name), f'{name} must share card metadata'
    dotnet=os.environ.get('DOTNET') or shutil.which('dotnet')
    if not dotnet: raise SystemExit('Set DOTNET or put .NET 9 on PATH')
    result=run(source,dotnet)
    print(result.stdout,end=''); assert result.returncode==0,result.stderr
    if args.mutations:
        changes=[('["star_cost"] = GetStarCostDisplay(card)','["star_cost"] = null'),
                 ('BuildCardInfo(card, pile)','BuildCardInfo(card)'),
                 ('cardInfo["index"] = index++','cardInfo["index"] = 0'),
                 ('return (isEnabled ?? true) && IsNodeVisible(holder);','return IsNodeVisible(holder);')]
        for old,new in changes:
            assert old in source
            result=run(source.replace(old,new),dotnet)
            assert result.returncode!=0,f'mutation survived: {old}'
        print(f'PASS: {len(changes)} representative mutations rejected')

if __name__=='__main__': main()
