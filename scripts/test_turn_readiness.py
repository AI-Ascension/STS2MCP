#!/usr/bin/env python3
"""Compile actual SP/MP battle builders and readiness helpers against simulated controls.
Not a real-game integration test. --baseline demonstrates missing metadata failure.
"""
import argparse, json, shutil, subprocess, tempfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--baseline',action='store_true');a=p.parse_args()
repo=Path(__file__).resolve().parents[1]
def method(file,name):
 s=subprocess.check_output(['git','show','2d3e90a:'+file],cwd=repo,text=True) if a.baseline else (repo/file).read_text()
 import re
 m=re.search(r'    private static [^\n]+ '+name+r'\(',s)
 if not m: return ''
 end=s.find('\n    private static ',m.end())
 return s[m.start():end if end>=0 else s.rfind('\n}')]
names=[('McpMod.StateBuilder.cs',n) for n in ['BuildBattleState','GetEndTurnBlockedReason']]+[('McpMod.MultiplayerState.cs',n) for n in ['BuildMultiplayerBattleState','GetMultiplayerEndTurnBlockedReason','GetMultiplayerUndoEndTurnBlockedReason']]
code=r'''
using System; using System.Collections.Generic;
class NPlayerHand { public enum Mode { Play, Select }; public bool InCardPlay; public Mode CurrentMode; }
class UI { public NPlayerHand Hand=new(); }
class NCombatRoom { public static NCombatRoom? Instance=new(); public UI Ui=new(); }
class Creature { public bool IsAlive=true; public CombatState? CombatState=new(); }
class Player { public Creature Creature=new(); }
class RunState { public List<Player> Players=new(){new Player()}; }
class CombatRoom {}
class CombatState { public int RoundNumber=1; public object CurrentSide="Player"; public List<Creature> Enemies=new(); }
class CombatManager { public static CombatManager Instance=new(); public bool IsInProgress=true, IsPlayPhase=true, PlayerActionsDisabled, Ready; public CombatState? State=new(); public CombatState? DebugOnlyGetState()=>State; public bool IsPlayerReadyToEndTurn(Player p)=>Ready; public bool AllPlayersReadyToEndTurn()=>Ready; }
class LocalContext { public static Player? GetMe(RunState r)=>r.Players.Count==0?null:r.Players[0]; public static bool IsMe(Player p)=>true; }
class Test {
static Dictionary<string,object?> BuildPlayerState(Player p)=>new();
static Dictionary<string,object?> BuildPlayerStateSummary(Player p)=>new();
static Dictionary<string,object?> BuildEnemyState(Creature c, Dictionary<string,int> d)=>new();
'''+''.join(method(*x) for x in names)+r'''
static int count;
static void Check(bool b,string label){ count++; if(!b)throw new Exception(label); }
static void Main(){
 var run=new RunState();var room=new CombatRoom();var cm=CombatManager.Instance;var p=run.Players[0];var hand=NCombatRoom.Instance!.Ui.Hand;
 void Both(string? reason){
  var sp=BuildBattleState(run,room);var mp=BuildMultiplayerBattleState(run,room);
  foreach(var b in new[]{sp,mp}){Check((bool)b["can_end_turn"]! == (reason==null),"can end");Check((string?)b["end_turn_blocked_reason"]==reason,"reason");Check((bool)b["player_actions_disabled"]! == cm.PlayerActionsDisabled,"disabled");}
 }
 Both(null);cm.IsInProgress=false;Both("NotInCombat");cm.IsInProgress=true;
 cm.IsPlayPhase=false;Both("NotInPlayPhase");cm.IsPlayPhase=true;
 cm.PlayerActionsDisabled=true;Both("PlayerActionsDisabled");cm.PlayerActionsDisabled=false;
 hand.InCardPlay=true;Both("CardInPlay");hand.InCardPlay=false;
 hand.CurrentMode=NPlayerHand.Mode.Select;Both("HandSelectionMode");hand.CurrentMode=NPlayerHand.Mode.Play;
 void MP(string? end,string? undo){var b=BuildMultiplayerBattleState(run,room);Check((string?)b["end_turn_blocked_reason"]==end,"mp end reason");Check((string?)b["undo_end_turn_blocked_reason"]==undo,"mp undo reason");Check((bool)b["can_undo_end_turn"]! == (undo==null),"mp undo");Check((bool)b["local_player_ready_to_end_turn"]! == cm.Ready,"mp ready");}
 MP(null,"NotReady");cm.Ready=true;MP("AlreadyReady",null);cm.Ready=false;
 p.Creature.IsAlive=false;MP("PlayerDead","PlayerDead");p.Creature.IsAlive=true;
 p.Creature.CombatState=null;MP("NoCombatState","NotReady");cm.Ready=true;MP("AlreadyReady","NoCombatState");
 cm.Ready=false;p.Creature.CombatState=new();NCombatRoom.Instance=null;Both(null);
 Check(BuildBattleState(run,room).ContainsKey("player"),"preserve SP player shortcut");
 Check(BuildMultiplayerBattleState(run,room).ContainsKey("players"),"preserve MP players");
 run.Players.Clear();Check(!BuildMultiplayerBattleState(run,room).ContainsKey("can_end_turn"),"no local player has no local readiness");
 cm.State=null;Check(BuildBattleState(run,room).ContainsKey("error"),"missing combat SP");Check(BuildMultiplayerBattleState(run,room).ContainsKey("error"),"missing combat MP");
 Console.WriteLine($"PASS: {count} compiled turn readiness checks (simulated controls)");
}
}
'''
with tempfile.TemporaryDirectory(prefix='sts-turn-readiness-') as tmp:
 root=Path(tmp);src=root/'Test.cs';src.write_text(code);dotnet=shutil.which('dotnet')
 if not dotnet:raise SystemExit('The .NET 9 SDK is required on PATH')
 sdk=Path(dotnet).resolve().parent;compiler=sorted((sdk/'sdk').glob('9.*/Roslyn/bincore/csc.dll'))[-1];refs=sorted((sdk/'packs/Microsoft.NETCore.App.Ref').glob('9.*/ref/net9.0'))[-1];out=root/'Test.dll'
 subprocess.run([dotnet,str(compiler),'-nologo','-nullable:enable','-langversion:12','-target:exe',f'-out:{out}',*[f'-r:{x}' for x in refs.glob('*.dll')],str(src)],check=True)
 (root/'Test.runtimeconfig.json').write_text(json.dumps({'runtimeOptions':{'tfm':'net9.0','framework':{'name':'Microsoft.NETCore.App','version':'9.0.0'}}}))
 subprocess.run([dotnet,str(out)],check=True)
