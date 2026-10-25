#!/usr/bin/env python3
"""Compile restored menu state with simulated scene/lobby APIs and real formatter.
Not a real-game API or integration test. No network or game saves are accessed.
"""
import argparse,json,re,shutil,subprocess,tempfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--mutations',action='store_true');a=p.parse_args()
s=(a.repo/'McpMod.StateBuilder.cs').read_text(); f=(a.repo/'McpMod.Formatting.cs').read_text()
def method(src,name):
 m=re.search(r'^    private static [^\n]*\b'+name+r'\(',src,re.M); assert m,name
 end=re.search(r'^    }$',src[m.start():],re.M);return src[m.start():m.start()+end.end()]
state=method(s,'BuildGameState');prefix=state[:state.index('        // Card selection overlays')]+ '        return result;\n    }'
names=['AddCharacterSelectMenuState','BuildStartRunLobbyState','SafeIsAboutToBeginGame','SafeGetPlayerName','AddMultiplayerJoinMenuState','AddMultiplayerLoadLobbyMenuState']
helpers='\n'.join(method(s,n) for n in names)
# Compile the full real formatting file, including the actual early-message dispatch.
stubs=r'''
using System; using System.Collections.Generic; using System.Linq; using System.Text;
namespace Godot { public static class Engine { public static object? Loop; public static object? GetMainLoop()=>Loop; } }
namespace STS2_MCP {
class Node { public List<Node> Children=new(); public Dictionary<string,object?> Fields=new(); public bool Visible=true; public IEnumerable<Node> GetChildren()=>Children; public bool IsVisibleInTree()=>Visible; }
class Control:Node {} class SceneTree { public Node? Root; }
class NClickableControl:Control { public bool IsEnabled {get;set;}=true; }
class NBackButton:NClickableControl {} class NSingleplayerSubmenu:Control {} class NMultiplayerHostSubmenu:Control {} class NMultiplayerSubmenu:Control {} class NMainMenu:Control {} class NTimelineScreen:Control {} class NCompendiumSubmenu:Control {} class NSettingsScreen:Control {} class NProfileScreen:Control {} class NJoinFriendScreen:Control {} class NMultiplayerLoadGameScreen:Control {}
class NJoinFriendButton:NClickableControl { public ulong PlayerId; }
class NCharacterSelectScreen:Control { public StartRunLobby? Lobby; }
class NCharacterSelectButton:Control { public Character? Character; public bool IsLocked; }
class Id { public string Entry="IRONCLAD"; }
class Item { public string Title="Item",DynamicDescription="Description"; }
class Pool { public List<Item> AllCards=new(), AllRelics=new(), AllPotions=new(); }
class Character { public Id Id=new(); public string Title="Ironclad",CardsModifierDescription="Modifier"; public int StartingHp=80,StartingGold=99,MaxEnergy=3; public List<Item> StartingRelics=new(),StartingDeck=new(); public Pool? CardPool,RelicPool,PotionPool; }
enum NetGameType { Singleplayer,Host,Client } static class NetExtensions { public static bool IsMultiplayer(this NetGameType t)=>t!=NetGameType.Singleplayer; }
enum PlatformType { Steam } enum GameMode { Standard }
class NetService { public NetGameType Type=NetGameType.Host; public PlatformType Platform; public ulong NetId=1; }
class LobbyPlayer { public ulong id; public int slotId; public bool isReady; public Character? character; }
class StartRunLobby { public NetService NetService=new(); public GameMode GameMode; public int MaxPlayers=4,Ascension=2,MaxAscension=10; public List<LobbyPlayer> Players=new(); public LobbyPlayer LocalPlayer=>Players.First(); public string? Seed; public bool Throw; public bool IsAboutToBeginGame(){if(Throw)throw new Exception();return Players.Count>0&&Players.All(p=>p.isReady);} }
class SavedPlayer { public ulong NetId; public Id? CharacterId=new(); public int CurrentHp=40,MaxHp=80,Gold=10; }
class SavedRun { public int Ascension=2,CurrentActIndex=1; public List<int> VisitedMapCoords=new(){1,2}; public List<SavedPlayer> Players=new(); }
class LoadRunLobby { public NetService NetService=new(); public GameMode GameMode; public SavedRun? Run; public List<ulong>? ConnectedPlayerIds=new(); public HashSet<ulong> Ready=new(); public bool IsPlayerReady(ulong id)=>Ready.Contains(id); public bool IsAboutToBeginGame()=>ConnectedPlayerIds?.Count>0&&ConnectedPlayerIds.All(Ready.Contains); }
static class PlatformUtil { public static PlatformType PrimaryPlatform; public static bool Throw; public static string GetPlayerName(PlatformType p,ulong id){if(Throw)throw new Exception();return "User"+id;} }
static class SteamInitializer { public static bool Initialized=true; } static class CommandLineHelper { public static bool Fast; public static bool HasArg(string name)=>Fast; }
enum EpochState { Revealed,Obtained,ObtainedNoSlot,NotObtained,NoSlot }
class Epoch { public string Id="Epoch1"; public EpochState State; public string ObtainDate="today"; }
class Progress { public List<Epoch> Epochs=new(); }
class SaveManager { public static SaveManager Instance=new(); public Progress Progress=new(); public int CurrentProfileId; }
class RunManager { public static RunManager Instance=new(); public bool IsInProgress; public object? State; public object? DebugOnlyGetState()=>State; }
public static partial class McpMod {
 static Dictionary<string,object?>? Ftue;
 static Dictionary<string,object?>? BuildVisibleFtueState(Node root)=>Ftue;
 static Dictionary<string,object?> WithStateEnvelope(Dictionary<string,object?> state,string kind){state["status"]="ok";state["kind"]=kind;return state;}
 static IEnumerable<T> FindAll<T>(Node n) where T:Node => n.Children.SelectMany(c=>(c is T t?new[]{t}:Array.Empty<T>()).Concat(FindAll<T>(c)));
 static T? FindFirst<T>(Node n) where T:Node=>FindAll<T>(n).FirstOrDefault();
 static bool IsNodeVisible(Node n)=>n.Visible&&n.IsVisibleInTree();
 static object? GetInstanceFieldValue(object n,string name)=>(n as Node)?.Fields.GetValueOrDefault(name);
 static string? SafeGetText(Func<string?> f){try{return f();}catch{return null;}}
 static List<string> GetProgressEpochIdsByState(params string[] states)=>SaveManager.Instance.Progress.Epochs.Where(e=>states.Contains(e.State.ToString())).Select(e=>e.Id).ToList();
 static void AddMenuOptionIfVisible(List<Dictionary<string,object?>> list,Node n,string field,string option){if(GetInstanceFieldValue(n,field) is NClickableControl b&&IsNodeVisible(b))list.Add(new(){["name"]=option,["enabled"]=b.IsEnabled});}
'''
tests=r'''
 static int checks; static void Check(bool b,string name){checks++;if(!b)throw new Exception(name);}
 static Dictionary<string,object?> State(Node? menu=null){var root=new Node();if(menu!=null)root.Children.Add(menu);Godot.Engine.Loop=new SceneTree{Root=root};return BuildGameState();}
 static List<Dictionary<string,object?>> Options(Dictionary<string,object?> s)=>(List<Dictionary<string,object?>>)s["options"]!;
 static void Envelope(Dictionary<string,object?> s){Check((string?)s["status"]=="ok","status");Check((string?)s["kind"]=="singleplayer_state","kind");}
 static void Main(){
 var main=new NMainMenu(); main.Fields["_singleplayerButton"]=new NClickableControl();main.Fields["_quitButton"]=new NClickableControl{IsEnabled=false};
 var s=State(main);Envelope(s);Check((string?)s["menu_screen"]=="main","main detected");Check(((List<string>)s["options"]!).SequenceEqual(new[]{"singleplayer"}),"enabled main options");Check(FormatAsMarkdown(s).Contains("`singleplayer`"),"message does not hide options");
 var single=new NSingleplayerSubmenu();single.Fields["_standardButton"]=new NClickableControl();single.Fields["_dailyButton"]=new NClickableControl{Visible=false};single.Fields["_customButton"]=new NClickableControl{IsEnabled=false};
 s=State(single);Check(Options(s).Count==2,"hidden modes excluded");Check(FormatAsMarkdown(s).Contains("`custom` (disabled)"),"disabled mode rendered");
 var ch=new NCharacterSelectScreen();ch.Children.Add(new NCharacterSelectButton{Character=new Character()});ch.Children.Add(new NCharacterSelectButton{Character=new Character(),IsLocked=true});ch.Fields["_embarkButton"]=new NClickableControl();ch.Fields["_unreadyButton"]=new NClickableControl();
 s=State(ch);Check(Options(s).All(o=>(string?)o["name"]!="unready"),"SP unready absent");Check(FormatAsMarkdown(s).Contains("LOCKED"),"locked character rendered");
 var lobby=new StartRunLobby();lobby.Players.Add(new LobbyPlayer{id=1,isReady=true,character=new Character()});lobby.Players.Add(new LobbyPlayer{id=2,isReady=false});ch.Lobby=lobby;
 s=State(ch);Check(Options(s).Any(o=>(string?)o["name"]=="unready"),"MP unready exposed");var l=(Dictionary<string,object?>)s["lobby"]!;Check(l["all_ready"] is false,"partial readiness");Check(l["is_local_ready"] is true,"local ready");Check(FormatAsMarkdown(s).Contains("User1 (you) [host]"),"roster formatted");
 lobby.Players[1].isReady=true;l=BuildStartRunLobbyState(lobby);Check(l["all_ready"] is true&&l["is_about_to_begin"] is true,"all ready");lobby.Throw=true;Check(SafeIsAboutToBeginGame(lobby)==false,"lobby exception safe");PlatformUtil.Throw=true;Check(SafeGetPlayerName(PlatformType.Steam,1)==null,"name exception safe");PlatformUtil.Throw=false;
 var join=new NJoinFriendScreen();var container=new Control();container.Children.Add(new NJoinFriendButton{PlayerId=7,IsEnabled=false});join.Fields["_buttonContainer"]=container;join.Fields["_refreshButton"]=new NClickableControl();join.Fields["_loadingOverlay"]=new Control();
 s=State(join);Check(s["loading"] is true,"loading exposed");Check(Options(s).Single(o=>(string?)o["name"]=="refresh")["enabled"] is false,"no refresh during load");Check(FormatAsMarkdown(s).Contains("join_0"),"friend option rendered");
 var load=new NMultiplayerLoadGameScreen();var ll=new LoadRunLobby{Run=new SavedRun()};ll.Run.Players.Add(new SavedPlayer{NetId=1});ll.ConnectedPlayerIds!.Add(1);ll.Ready.Add(1);load.Fields["_runLobby"]=ll;load.Fields["_confirmButton"]=new NClickableControl{IsEnabled=false};
 s=State(load);l=(Dictionary<string,object?>)s["lobby"]!;Check(l["all_ready"] is true,"load readiness");Check(FormatAsMarkdown(s).Contains("Connected: 1/1"),"load counts rendered");Check(FormatAsMarkdown(s).Contains("`confirm` (disabled)"),"disabled confirm");
 Ftue=new(){["state_type"]="menu",["menu_screen"]="tutorial"};s=State(main);Envelope(s);Check((string?)s["menu_screen"]=="tutorial","FTUE precedence");Ftue=null;
 RunManager.Instance.IsInProgress=true;s=State(ch);Envelope(s);Check((string?)s["menu_screen"]=="character_select","null-run character screen");
 var over=new Dictionary<string,object?>{["state_type"]="game_over",["message"]="generic",["game_over"]=new Dictionary<string,object?>{["message"]="Run ended.",["options"]=new List<string>{"main_menu"}}};Check(FormatAsMarkdown(over).Contains("`main_menu`"),"game over precedes generic message");
 Console.WriteLine($"PASS: {checks} compiled menu/lobby/formatter checks (simulated controls)");
 }
}}
'''
dotnet=shutil.which('dotnet');assert dotnet,'dotnet required';sdk=Path(dotnet).resolve().parent;csc=sorted((sdk/'sdk').glob('9.*/Roslyn/bincore/csc.dll'))[-1];refs=sorted((sdk/'packs/Microsoft.NETCore.App.Ref').glob('9.*/ref/net9.0'))[-1]
def run(statecode,formatcode,expected=0):
 with tempfile.TemporaryDirectory(prefix='menu-closure-') as tmp:
  t=Path(tmp);(t/'State.cs').write_text(stubs+statecode+helpers+tests);(t/'Formatting.cs').write_text(formatcode);out=t/'Tests.dll'
  subprocess.run([dotnet,str(csc),'-nologo','-nullable:enable','-langversion:12','-target:exe',f'-out:{out}',*[f'-r:{r}' for r in refs.glob('*.dll')],str(t/'State.cs'),str(t/'Formatting.cs')],check=True)
  (t/'Tests.runtimeconfig.json').write_text(json.dumps({'runtimeOptions':{'tfm':'net9.0','framework':{'name':'Microsoft.NETCore.App','version':'9.0.0'}}}))
  r=subprocess.run([dotnet,str(out)],capture_output=True,text=True);print(r.stdout or r.stderr);assert (r.returncode==0)==(expected==0),r.returncode
run(prefix,f)
if a.mutations:
 for old,new in [('FormatMenuMarkdown(sb, state);','sb.AppendLine("menu");'),('FormatGameOverMarkdown(sb, state);','sb.AppendLine("game over");')]:
  assert old in f;run(prefix,f.replace(old,new),1)
