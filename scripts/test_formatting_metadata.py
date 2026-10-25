#!/usr/bin/env python3
"""Compile the actual standalone formatter with Roslyn; no game or MSBuild required."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

p = argparse.ArgumentParser()
p.add_argument('--source-root', type=Path, default=Path(__file__).resolve().parents[1])
p.add_argument('--mutations', action='store_true')
a = p.parse_args()
source = (a.source_root / 'McpMod.Formatting.cs').read_text()
harness = r'''
using System; using System.Text; using System.Collections.Generic; using System.Linq; using System.Reflection;
using D = System.Collections.Generic.Dictionary<string, object?>;
using L = System.Collections.Generic.List<System.Collections.Generic.Dictionary<string, object?>>;
class Test {
 static int Count, Failures;
 static void Check(bool ok, string msg) { Count++; if(!ok) { Failures++; Console.WriteLine("FAIL: " + msg); } }
 static object? Call(string name, params object?[] args) => typeof(STS2_MCP.McpMod).GetMethod(name,BindingFlags.Static|BindingFlags.NonPublic)!.Invoke(null,args);
 static string Render(string method,D data) { var sb=new StringBuilder(); Call(method,sb,data); return sb.ToString(); }
 static L Keywords() => new() { new D { ["name"]="Ethereal",["description"]="Removed at end" }, new D { ["name"]=" " }, new D(), new D { ["name"]="Exhaust",["description"]="Removed on use" } };
 static D Card() => new() { ["index"]=0,["name"]="Meteor",["cost"]="X",["star_cost"]="2",["type"]="Attack",["rarity"]="Rare",["description"]="Deal damage.",["is_upgraded"]=true,["keywords"]=Keywords(),["can_play"]=true,["target_type"]="AnyEnemy" };
 static D Relic() => new() { ["index"]=1,["name"]="Amulet",["description"]="Gain block.",["keywords"]=Keywords(),["counter"]=3,["rarity"]="Rare" };
 static void CardCheck(string text,string context) {
  foreach(var part in new[] { "**Meteor**+", "(X energy + 2 star)", "[Attack]", "[Ethereal, Exhaust]", "Deal damage." }) Check(text.Contains(part),context+": "+part);
 }
 static void Main() {
  var card=Card(); var cards=new L { card };
  foreach(var method in new[] { "FormatCardRewardMarkdown", "FormatHandSelectMarkdown", "FormatCardSelectMarkdown" }) CardCheck(Render(method,new D { ["cards"]=cards }),method);
  CardCheck(Render("FormatHandSelectMarkdown",new D { ["selected_cards"]=cards }),"already selected");
  var bundle=new D { ["index"]=0,["card_count"]=1,["cards"]=cards };
  CardCheck(Render("FormatBundleSelectMarkdown",new D { ["bundles"]=new L { bundle } }),"bundle");
  CardCheck(Render("FormatBundleSelectMarkdown",new D { ["preview_showing"]=true,["preview_cards"]=cards }),"preview");
  var player=new D { ["character"]="Regent",["hp"]=20,["max_hp"]=40,["block"]=2,["energy"]=3,["max_energy"]=3,["gold"]=99,["hand"]=cards,["relics"]=new L { Relic() },["draw_pile_count"]=0,["discard_pile_count"]=0,["exhaust_pile_count"]=0,["is_local"]=true,["is_alive"]=true,["is_ready_to_end_turn"]=false };
  var battle=new D { ["round"]=1,["turn"]="player",["is_play_phase"]=true,["player"]=player,["players"]=new L { player } };
  foreach(var method in new[] { "FormatBattleMarkdown", "FormatMultiplayerBattleMarkdown" }) {
   var text=Render(method,battle); CardCheck(text,method);
   Check(text.Contains("(target: AnyEnemy) ✓"),method+" target/playability");
   Check(text.Contains("**Amulet** [3] Rare [Ethereal, Exhaust] - Gain block."),method+" relic details");
  }
  foreach(var method in new[] { "FormatRelicSelectMarkdown", "FormatTreasureMarkdown" }) {
   var text=Render(method,new D { ["relics"]=new L { Relic() } });
   Check(text.Contains("[1] **Amulet** Rare [Ethereal, Exhaust] - Gain block."),method+" relic details");
  }
  foreach(var category in new[] { "card", "relic", "potion" }) {
   var item=new D { ["category"]=category,["index"]=0,["is_stocked"]=true,["can_afford"]=false,["cost"]=20,["on_sale"]=true,[category+"_name"]="ShopItem",["keywords"]=Keywords() };
   var text=Render("FormatShopMarkdown",new D { ["items"]=new L { item } });
   Check(text.Contains("[Ethereal, Exhaust]"),category+" shop keywords");
   Check(text.Contains("20g **SALE** (can't afford)"),category+" shop cost/sale preserved");
   item["is_stocked"]=false;
   Check(Render("FormatShopMarkdown",new D { ["items"]=new L { item } }).Contains("SOLD"),category+" sold preserved");
  }
  foreach(var pile in new[] { "draw_pile", "discard_pile", "exhaust_pile" }) {
   player[pile]=cards;
   var text=Render("FormatDeckPilesMarkdown",player);
   Check(text.Contains("**Meteor**+ (X + 2 star) [Attack] Rare [Ethereal, Exhaust] - Deal damage."),pile+" metadata");
   player.Remove(pile);
  }
  var shopCard=new D { ["category"]="card",["index"]=0,["is_stocked"]=true,["can_afford"]=true,["cost"]=75,["card_cost"]="1",["card_star_cost"]="X",["card_name"]="Meteor",["card_is_upgraded"]=true,["card_description"]="Damage",["card_upgrade_preview_cost"]="0",["card_upgrade_preview_star_cost"]="2",["card_upgrade_preview_description"]="More damage" };
  var shopText=Render("FormatShopMarkdown",new D { ["items"]=new L { shopCard } });
  Check(shopText.Contains("**Meteor**+ (1 energy + X star)"),"shop card energy/upgrade distinct from purchase cost");
  Check(shopText.Contains("Upgrade: (0 energy + 2 star) More damage"),"shop upgrade preview");
  Check(shopText.Contains("75g"),"shop purchase cost preserved");
  shopCard["card_upgrade_preview_description"]="Damage";
  Check(!Render("FormatShopMarkdown",new D { ["items"]=new L { shopCard } }).Contains("Upgrade:"),"unchanged upgrade preview omitted");
  var minimal=new D { ["name"]="Plain",["index"]=2,["cost"]=0,["type"]="Skill",["rarity"]="Common",["description"]="Nothing." };
  var basic=Render("FormatCardRewardMarkdown",new D { ["cards"]=new L { minimal } });
  Check(!basic.Contains("**Plain**+"),"missing upgrade not upgraded"); Check(!basic.Contains(" star"),"missing star cost omitted");
  minimal["is_upgraded"]=false; minimal["keywords"]=new L(); minimal["star_cost"]=null;
  Check(Render("FormatCardRewardMarkdown",new D { ["cards"]=new L { minimal } })==basic,"false/null/empty optional metadata");
  var full=(string)Call("FormatAsMarkdown",new D { ["state_type"]="card_reward",["card_reward"]=new D { ["cards"]=cards } })!;
  CardCheck(full,"full dispatch"); Check(full.Contains("Removed at end"),"glossary preserved alongside inline association");
  Console.WriteLine($"{(Failures==0 ? "PASS" : "FAIL")}: {Count} compiled formatter checks; {Failures} failures");
  Environment.ExitCode=Failures==0 ? 0 : 1;
 }
}
'''
dotnet = shutil.which('dotnet')
if not dotnet:
    raise SystemExit('The .NET 9 SDK is required on PATH')
sdk = Path(dotnet).resolve().parent
compiler = sorted((sdk / 'sdk').glob('9.*/Roslyn/bincore/csc.dll'))[-1]
refs = sorted((sdk / 'packs/Microsoft.NETCore.App.Ref').glob('9.*/ref/net9.0'))[-1]
def run(code, label, expected=0):
    with tempfile.TemporaryDirectory(prefix='sts-format-test-') as tmp:
        root = Path(tmp)
        (root / 'Formatting.cs').write_text(code)
        (root / 'Test.cs').write_text(harness)
        output = root / 'Test.dll'
        subprocess.run([dotnet, str(compiler), '-nologo', '-nullable:enable', '-langversion:12', '-target:exe', f'-out:{output}', *[f'-r:{p}' for p in refs.glob('*.dll')], str(root / 'Formatting.cs'), str(root / 'Test.cs')], check=True)
        (root / 'Test.runtimeconfig.json').write_text(json.dumps({'runtimeOptions': {'tfm':'net9.0','framework':{'name':'Microsoft.NETCore.App','version':'9.0.0'}}}))
        result = subprocess.run([dotnet, str(output)], capture_output=True, text=True)
        print(f'{label}:\n{result.stdout}{result.stderr}')
        if result.returncode != expected:
            raise SystemExit(f'{label}: expected exit {expected}, got {result.returncode}')
run(source, 'actual formatter')
if a.mutations:
    mutations = {
        'drop keyword names': ('return names.Count > 0 ? $" [{string.Join(", ", names)}]" : "";', 'return "";'),
        'drop upgrade marker': ('string upgraded = FormatUpgradeMarker(card);', 'string upgraded = "";'),
        'drop star cost': ('{energy}{starCost})', '{energy})'),
        'drop relic keywords': ('{nameSuffix}{rarity}{keywords}{description}', '{nameSuffix}{rarity}{description}'),
        'drop bundle details': ('sb.AppendLine($"  {FormatCardDetails(card)}");', 'sb.AppendLine($"  {card["name"]}");'),
        'drop hand details': ('sb.AppendLine($"- [{card["index"]}] {FormatCardDetails(card, includeTarget: true)} {playable}");', 'sb.AppendLine($"- [{card["index"]}] {card["name"]} {playable}");'),
    }
    mutations['drop pile details'] = ('sb.AppendLine($"- {FormatCardDetails(card, energyLabel: false)}");', 'sb.AppendLine($"- {card["name"]}");')
    mutations['drop shop preview'] = ('{cardUpgrade}",', '",')
    for label,(before,after) in mutations.items():
        if before not in source: raise SystemExit(f'Mutation target missing: {label}')
        run(source.replace(before, after), label, expected=1)
