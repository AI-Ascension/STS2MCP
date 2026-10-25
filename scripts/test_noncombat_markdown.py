#!/usr/bin/env python3
"""Compile the complete real formatter and verify noncombat local-player context."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('--source-root', type=Path, default=Path(__file__).resolve().parents[1])
parser.add_argument('--mutations', action='store_true')
args = parser.parse_args()
source = (args.source_root / 'McpMod.Formatting.cs').read_text()
harness = r'''
using System; using System.Collections.Generic; using System.Reflection;
using D = System.Collections.Generic.Dictionary<string,object?>;
using L = System.Collections.Generic.List<System.Collections.Generic.Dictionary<string,object?>>;
class Test {
 static int checks, failures;
 static void Check(bool value,string label) { checks++; if(!value){failures++;Console.WriteLine("FAIL: "+label);} }
 static string Render(D state) => (string)typeof(STS2_MCP.McpMod).GetMethod("FormatAsMarkdown",BindingFlags.Static|BindingFlags.NonPublic)!.Invoke(null,new object[]{state})!;
 static D Player() => new() { ["character"]="Regent",["hp"]=32,["max_hp"]=80,["gold"]=53,["stars"]=2,
 ["relics"]=new L { new D { ["name"]="Amulet",["description"]="Gain block",["counter"]=3,["rarity"]="Rare" } },
 ["potions"]=new L { new D { ["slot"]=2,["name"]="Healing potion",["description"]="Heal 10" } },["max_potion_slots"]=4 };
 static void Main(){
  foreach(var mode in new[]{"singleplayer","multiplayer"}) {
   var p=Player();var state=new D { ["state_type"]="event",["game_mode"]=mode,["player"]=p,["event"]=new D { ["event_name"]="Test event" } };
   var text=Render(state);
   foreach(var expected in new[]{"## Player (You)","**Regent** - HP: 32/80 | Gold: 53 | Stars: 2","**Amulet** [3] Rare - Gain block","### Potions (1/4)","[2] **Healing potion**: Heal 10","Test event"}) Check(text.Contains(expected),mode+" "+expected);
   Check(text.IndexOf("## Player (You)")==text.LastIndexOf("## Player (You)"),mode+" one local section");
   p["potions"]=new L();text=Render(state);Check(text.Contains("### Potions (0/4)"),mode+" empty capacity");
   p.Remove("potions");p.Remove("relics");p.Remove("stars");text=Render(state);Check(!text.Contains("### Potions"),mode+" absent potions");Check(!text.Contains("Stars:"),mode+" absent stars");
   p["potions"]=new L {new D {["slot"]=1,["name"]="Legacy",["description"]="legacy potion"}};p.Remove("max_potion_slots");Check(Render(state).Contains("### Potions (1/1)"),mode+" legacy capacity");
   state["battle"]=null;Check(Render(state).Contains("## Player (You)"),mode+" null battle is not rendered battle");
   state.Remove("player");Check(!Render(state).Contains("## Player (You)"),mode+" no player tolerated");
  }
  var local=Player();local["block"]=0;local["energy"]=3;local["max_energy"]=3;local["draw_pile_count"]=0;local["discard_pile_count"]=0;local["exhaust_pile_count"]=0;
  var battle=new D { ["round"]=1,["turn"]="player",["is_play_phase"]=true,["player"]=local };
  var combat=Render(new D { ["state_type"]="battle",["player"]=Player(),["battle"]=battle });
  Check(combat.IndexOf("## Player (You)")==combat.LastIndexOf("## Player (You)"),"combat no duplicate player");
  Check(combat.Contains("Energy: 3/3"),"combat detail intact");
  Check(!combat.Contains("### Potions (1/4)"),"combat does not use noncombat formatter");
  var menu=Render(new D { ["state_type"]="menu",["menu_screen"]="main",["message"]="Choose mode",["player"]=Player() });
  Check(menu.Contains("Choose mode"),"menu unchanged");Check(!menu.Contains("## Player (You)"),"menu no stale run player");
  var message=Render(new D { ["state_type"]="unknown",["message"]="Unavailable",["player"]=Player() });
  Check(message.Contains("Unavailable")&&!message.Contains("## Player (You)"),"early error/message unchanged");
  Console.WriteLine($"{(failures==0?"PASS":"FAIL")}: {checks} compiled noncombat Markdown checks; {failures} failures");Environment.ExitCode=failures==0?0:1;
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
    with tempfile.TemporaryDirectory(prefix='sts-noncombat-markdown-') as tmp:
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
if args.mutations:
    for before,after in [('            FormatPotionsSection(sb, topPlayer);',''), ('r, counter)}','r)}'), ('if (!(state.TryGetValue("battle", out var renderedBattle) && renderedBattle is Dictionary<string, object?>)','if (true')]:
        if before not in source:
            raise SystemExit('Mutation target missing: '+before)
        run(source.replace(before,after),'regression mutation',expected=1)
