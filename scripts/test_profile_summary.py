#!/usr/bin/env python3
"""Compile the actual profile summary method with simulated controls (not a game test).

Requires the .NET 9 SDK. Pass --source to test a historical Profile.cs file.
"""
import argparse
import json
import shutil
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser()
p.add_argument('--source', type=Path, default=Path(__file__).resolve().parents[1] / 'McpMod.Profile.cs')
a = p.parse_args()
source = a.source.read_text()
start = source.index('    private static Dictionary<string, object?> BuildProfilesSummary()')
end = source.index('    private static ', start + 10)
method = source[start:end]
stubs = r'''
using System; using System.Collections.Generic; using System.IO;
class SaveManager { public static SaveManager? Instance = new(); public int CurrentProfileId = 2; }
class ProgressSaveManager { public static string GetProgressPathForProfile(int i) => $"modded/profile{i}/progress.save"; }
class Test {
 static string? GetProfileProgressPath(int i) => ProgressSaveManager.GetProgressPathForProfile(i);
 static string? ResolveProfileProgressPath(int i) => i == 2 ? TestPath : null;
 static string GetProfileRootFromProgressPath(string? p, int i) => $"modded/profile{i}";
 static string? NormalizePathForJson(string? p) => p?.Replace('\\', '/');
 static string GetSaveScope(string p) => p.StartsWith("modded/") ? "modded" : "vanilla";
 static Dictionary<string,object?> Error(string m,string c) => new() { ["status"]="error" };
 static string TestPath = "";
'''
tests = r'''

 static void Check(bool b,string m) { if(!b) throw new Exception(m); }
 static void Main() {
  TestPath=Path.GetTempFileName();
  try {
   var result=BuildProfilesSummary();
   var profiles=(List<Dictionary<string,object?>>)result["profiles"]!;
   Check(profiles.Count==3,"three profiles");
   for(int i=1;i<=3;i++) {
    var p=profiles[i-1];
    Check((string?)p["path"]==$"modded/profile{i}/progress.save","path retained");
    Check((string?)p["profile_root"]==$"modded/profile{i}","modded root retained");
    Check((string?)p["save_scope"]=="modded","scope retained");
    Check((bool)p["has_data"]! == (i==2),"resolved file existence");
    Check((bool)p["is_current"]! == (i==2),"current profile");
   }
   SaveManager.Instance=null;
   Check((string?)BuildProfilesSummary()["status"]=="error","missing save manager");
   Console.WriteLine("PASS: 17 extracted profile summary checks (simulated saves)");
  } finally { File.Delete(TestPath); }
 }
}
'''
with tempfile.TemporaryDirectory(prefix='sts-selection-test-') as tmp:
    root = Path(tmp)
    (root / 'Test.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net9.0</TargetFramework><Nullable>enable</Nullable><LangVersion>12</LangVersion></PropertyGroup></Project>')
    (root / 'Program.cs').write_text(stubs + method + tests)
    dotnet = shutil.which('dotnet')
    if not dotnet:
        raise SystemExit('The .NET 9 SDK is required on PATH')
    sdk_root = Path(dotnet).resolve().parent
    compiler = sorted((sdk_root / 'sdk').glob('9.*/Roslyn/bincore/csc.dll'))[-1]
    references = sorted((sdk_root / 'packs/Microsoft.NETCore.App.Ref').glob('9.*/ref/net9.0'))[-1]
    output = root / 'Test.dll'
    subprocess.run([dotnet, str(compiler), '-nologo', '-nullable:enable', '-langversion:12',
                    '-target:exe', f'-out:{output}',
                    *[f'-r:{p}' for p in references.glob('*.dll')], str(root / 'Program.cs')], check=True)
    (root / 'Test.runtimeconfig.json').write_text(json.dumps({'runtimeOptions': {
        'tfm': 'net9.0', 'framework': {'name': 'Microsoft.NETCore.App', 'version': '9.0.0'}}}))
    subprocess.run([dotnet, str(output)], check=True)
