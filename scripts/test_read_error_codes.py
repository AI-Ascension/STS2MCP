#!/usr/bin/env python3
"""Compile actual read handlers and SendError against a simulated response sink."""
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
methods = []
for filename, name in [('McpMod.Compendium.cs', 'HandleGetCompendium'), ('McpMod.Wiki.cs', 'HandleGetWiki'), ('McpMod.Helpers.cs', 'SendError'), ('McpMod.Helpers.cs', 'SendReadResultJson')]:
    source = (a.source_root / filename).read_text()
    match = re.search(r'    (?:private|internal) static [^\n]+\b' + name + r'\(', source)
    start = match.start()
    end = re.search(r'\n    (?:private|internal|public) static ', source[start + 10:])
    methods.append(source[start:start + 10 + end.start()])
stubs = r'''
using System; using System.Collections.Generic; using System.Collections.Specialized; using System.Threading.Tasks;
class HttpListenerResponse { public int StatusCode=200; public object? Body; }
class HttpListenerRequest { public NameValueCollection QueryString=new(); }
class Test {
 static bool Fail;
 static Task<object> RunOnMainThread(Func<object> f) => Task.FromResult(f());
 static object BuildCompendiumSnapshot() { if(Fail)throw new Exception("fixture");return new object(); }
 static object BuildCompendiumResponse(object snapshot) => new Dictionary<string,object?> { ["status"]="ok" };
 static object BuildWikiSearch(string q,string t,int limit) { if(Fail)throw new Exception("fixture");return new Dictionary<string,object?> { ["status"]="ok" }; }
 static int ParseWikiLimit(string? limit) => 10;
 static void SendJson(HttpListenerResponse response,object body) => response.Body=body;
 static void Check(bool ok,string message) { if(!ok)throw new Exception(message); }
'''
tests = r'''
 static void Main() {
  int count=0;
  foreach(var kind in new[] {"compendium","wiki"}) {
   foreach(var failure in new[] {false,true}) {
    Fail=failure;var response=new HttpListenerResponse();
    if(kind=="compendium")HandleGetCompendium(response);
    else {var request=new HttpListenerRequest();request.QueryString["query"]="fixture";HandleGetWiki(request,response);}
    var body=(Dictionary<string,object?>)response.Body!;
    Check(response.StatusCode==(failure?500:200),kind+" HTTP status");count++;
    Check((string?)body["status"]==(failure?"error":"ok"),kind+" envelope");count++;
    if(failure) {
     var expected=kind=="compendium"?"compendium_build_failed":"wiki_search_failed";
     Check(body.TryGetValue("error_code",out var code) && (string?)code==expected,kind+" stable error code");count++;
     Check(((string)body["error"]!).Contains("fixture"),kind+" diagnostic");count++;
    }
   }
  }
  Console.WriteLine($"PASS: {count} extracted read-handler error checks (simulated response sink)");
 }
}
'''
with tempfile.TemporaryDirectory(prefix='sts-error-test-') as tmp:
    root = Path(tmp)
    (root / 'Program.cs').write_text(stubs + '\n'.join(methods) + tests)
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
