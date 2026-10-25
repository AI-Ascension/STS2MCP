#!/usr/bin/env python3
"""Compile actual save-root enumeration/resolution against temporary filesystem fixtures.
Uses simulated Steam identity and explicit fixture roots, never real user saves.
Requires the .NET 9 SDK on PATH. --source permits red/green historical regression checks.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=Path, default=Path(__file__).resolve().parents[1] / 'McpMod.Compendium.cs')
args = parser.parse_args()
source = args.source.read_text()
def region(start, end):
    return source[source.index(start):source.index(end, source.index(start))]
snapshots = (args.source.parent / 'McpMod.Snapshots.cs').read_text()
def snap_region(start, end):
    return snapshots[snapshots.index(start):snapshots.index(end, snapshots.index(start))]
methods = '\n'.join([
    region('    private static IEnumerable<string> EnumerateSaveRoots()', '    private static IEnumerable<string> EnumerateSteamDataRoots()'),
    region('    private static string GetProfileRootFromProgressPath', '    private static IEnumerable<string> EnumerateSaveRoots()'),
    region('    private static string? ResolveProfileProgressPath', '    private static object? ToJsonSafe'),
    region('    private static string? FindRunHistoryDirectory', '    private static string GetProfileRootFromProgressPath'),
    snap_region('    private static string? ResolveRunSavePath(', '    private static bool AreSnapshotsEnabled()'),
])
fixture = r'''
using System; using System.IO; using System.Linq; using System.Collections.Generic;
class SaveManager { public static SaveManager? Instance = new(); public int CurrentProfileId=2; }
class CompendiumSnapshot { public string? ProgressPath; public string ProfileRoot="profile2"; }
class Program {
 const string SnapshotRootEnvVar="STS2_TEST_SNAPSHOT_ROOT";
 const string SnapshotDirectoryName="sts2_mcp_snapshots";
 static string[] Roots=Array.Empty<string>(); static string? Active; static string? Progress; static int Checks;
 static IEnumerable<string> EnumerateSteamDataRoots()=>Roots;
 static string? GetActiveSteamId()=>Active;
 static string? GetProfileProgressPath(int id)=>Progress;
 static void Check(bool value,string name) {Checks++;if(!value)throw new Exception(name);}
 static string Dir(params string[] parts){var p=Path.Combine(parts);Directory.CreateDirectory(p);return p;}
 static string Saves(string account,string profile="profile2") {
   var p=Dir(account,profile,"saves");File.WriteAllText(Path.Combine(p,"progress.save"),"{}");
   File.WriteAllText(Path.Combine(p,"current_run.save"),"{}");Dir(p,"history");return p;
 }
 static void NoFallback(string name) {
   Check(ResolveCurrentRunPath(Progress,"profile2")==null,name+" current run");
   Check(FindRunHistoryDirectory(new(){ProgressPath=Progress})==null,name+" history");
   Check(ResolveRunSavePath(2,"profile2","current_run.save",true)==null,name+" snapshot create source");
   Check(ResolveRunSavePath(2,"profile2","current_run.save",false)==null,name+" snapshot restore destination");
 }
 static void Main(string[] args) {
  Environment.SetEnvironmentVariable(SnapshotRootEnvVar,null);
  var root=args[0];var steam=Dir(root,"steam");var steam2=Dir(root,"steam2");
  var a=Dir(steam,"A");var b=Dir(steam,"B");var bs=Saves(b);var as2=Saves(Dir(steam2,"A"));
  Roots=new[]{steam};Active="A";Progress="profile2/saves/progress.save";
  Check(EnumerateSaveRoots().SequenceEqual(new[]{a}),"known A never yields B");
  Check(ResolveProfileProgressPath(2)==Progress,"A missing progress does not resolve B");
  NoFallback("A missing files");
  Directory.Delete(a);
  Check(!EnumerateSaveRoots().Any(),"known missing A directory never yields B");
  NoFallback("A missing directory");
  try {GetSnapshotRoot();Check(false,"missing account snapshot archive fails closed");}catch(InvalidOperationException){Check(true,"missing account archive rejected");}
  Active=null;
  Check(EnumerateSaveRoots().SequenceEqual(new[]{b}),"unknown sole B permitted");
  Check(ResolveRunSavePath(2,"profile2","current_run.save",true)==Path.Combine(bs,"current_run.save"),"sole B read");
  Check(GetSnapshotRoot()==Path.Combine(b,SnapshotDirectoryName),"sole B archive");
  a=Dir(steam,"A");
  Check(!EnumerateSaveRoots().Any(),"unknown A+B ambiguous");NoFallback("unknown A+B");
  Check(ResolveProfileProgressPath(2)==Progress,"ambiguous progress unresolved");
  try {GetSnapshotRoot();Check(false,"ambiguous archive fails closed");}catch(InvalidOperationException){Check(true,"ambiguous archive rejected");}
  Active="A";Roots=new[]{steam,steam2,steam};
  Check(EnumerateSaveRoots().SequenceEqual(new[]{a,Path.Combine(steam2,"A")}),"same A across roots deduplicated");
  Check(ResolveRunSavePath(2,"profile2","current_run.save",false)==Path.Combine(as2,"current_run.save"),"same A second root used");
  var aps=Saves(a);Check(ResolveCurrentRunPath(Progress,"profile2")==Path.Combine(aps,"current_run.save"),"A beats B same slot");
  Check(ResolveRunSavePath(2,"profile2","current_run.save",false)==Path.Combine(aps,"current_run.save"),"A restore same slot");
  Progress=Path.Combine(root,"missingA","profile2","saves","progress.save");Active=null;Roots=new[]{Dir(root,"steamB")};Saves(Dir(Roots[0],"B"));
  NoFallback("absolute missing A authoritative");
  Check(ResolveProfileProgressPath(2)==Progress,"absolute progress preserved");
  Check(GetSnapshotRoot()==Path.Combine(root,"missingA",SnapshotDirectoryName),"absolute A archive never sole other account");
  Progress=Path.Combine(a,"modded","profile2","saves","progress.save");
  Check(GetSnapshotRoot()==Path.Combine(a,SnapshotDirectoryName),"modded absolute archive same account");
  Progress=Path.Combine(Path.GetPathRoot(root)!,"profile2","saves","progress.save");
  Check(Path.IsPathRooted(GetSnapshotRoot()),"filesystem-root account archive stays absolute");
  Check(GetSnapshotRoot()==Path.Combine(Path.GetPathRoot(root)!,SnapshotDirectoryName),"filesystem-root archive path preserved");
  Progress=Path.Combine(Path.GetPathRoot(root)!,"modded","profile2","saves","progress.save");
  Check(Path.IsPathFullyQualified(GetSnapshotRoot()),"modded filesystem-root archive stays fully qualified");
  Check(GetSnapshotRoot()==Path.Combine(Path.GetPathRoot(root)!,SnapshotDirectoryName),"modded filesystem-root archive preserved");
  Progress=Path.Combine(aps,"progress.save");File.Delete(Path.Combine(aps,"current_run.save"));Directory.Delete(Path.Combine(aps,"history"));
  Check(ResolveCurrentRunPath(Progress,"profile2")==null,"absolute missing file does not use second A root");
  Check(FindRunHistoryDirectory(new(){ProgressPath=Progress})==null,"absolute missing history does not use second root");
  Check(ResolveRunSavePath(2,"profile2","current_run.save",true)==null,"absolute missing snapshot source no fallback");
  Check(ResolveRunSavePath(2,"profile2","current_run.save",false)==Path.Combine(aps,"current_run.save"),"absolute restore stays exact directory");
  Roots=new[]{steam2,steam2};Active=null;Progress="profile2/saves/progress.save";
  Check(EnumerateSaveRoots().Count()==1,"unknown duplicated sole identity accepted");
  Directory.Delete(b,true);Roots=new[]{steam,steam2};Check(EnumerateSaveRoots().Count()==2,"unknown sole identity across OS roots allowed");
  Roots=new[]{steam2,Path.Combine(root,"disappeared")};Check(!EnumerateSaveRoots().Any(),"unknown enumeration error fails closed");
  Console.WriteLine($"PASS: {Checks} extracted account-isolation assertions (synthetic saves only)");
 }
'''
dotnet = shutil.which('dotnet')
if not dotnet:
    raise SystemExit('The .NET 9 SDK is required on PATH')
sdk_root = Path(dotnet).resolve().parent
compiler = sorted((sdk_root / 'sdk').glob('9.*/Roslyn/bincore/csc.dll'))[-1]
references = sorted((sdk_root / 'packs/Microsoft.NETCore.App.Ref').glob('9.*/ref/net9.0'))[-1]
with tempfile.TemporaryDirectory(prefix='sts-save-roots-') as tmp:
    root = Path(tmp)
    program = root / 'Program.cs'
    program.write_text(fixture + methods + '\n}\n')
    output = root / 'Test.dll'
    subprocess.run([dotnet, str(compiler), '-nologo', '-nullable:enable', '-langversion:12',
                    '-target:exe', f'-out:{output}',
                    *[f'-r:{p}' for p in references.glob('*.dll')], str(program)], check=True)
    (root / 'Test.runtimeconfig.json').write_text(json.dumps({'runtimeOptions': {
        'tfm': 'net9.0', 'framework': {'name': 'Microsoft.NETCore.App', 'version': '9.0.0'}}}))
    subprocess.run([dotnet, str(output), str(root / 'fixtures')], check=True)
