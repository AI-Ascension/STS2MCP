#!/usr/bin/env python3
"""Compile real read response/HTTP methods against simulated profile/model services."""
import argparse,json,re,shutil,subprocess,tempfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,default=Path(__file__).resolve().parents[1]);a=p.parse_args()
def extract(filename,name):
 s=(a.source_root/filename).read_text(); m=re.search(r'    (?:private|internal) static [^\n]+\b'+name+r'\(',s); start=m.start(); end=re.search(r'\n    (?:private|internal|public) (?:static |sealed )',s[start+10:]); return s[start:start+10+end.start()]
comp=(a.source_root/'McpMod.Compendium.cs').read_text();cl=comp[comp.index('    private sealed class CompendiumSnapshot'):comp.index('    private static List<Dictionary',comp.index('    private sealed class CompendiumSnapshot'))]
# Preserve the actual missing-profile initializer; all success-path snapshot gathering is a service seam.
missing=re.search(r'return (new CompendiumSnapshot \{ Error = "No profile data available\."[^\n]+);',comp).group(1)
methods=[extract(f,n) for f,names in [('McpMod.Compendium.cs',['HandleGetCompendium','BuildCompendiumResponse']),('McpMod.Wiki.cs',['HandleGetWiki','SearchWiki','BuildWikiSearch','NormalizeWikiItemType','ParseWikiLimit','NormalizeWikiLimit']),('McpMod.Helpers.cs',['SendError','SendReadResultJson','Error'])] for n in names]
stubs=r'''
using System;using System.Collections.Generic;using System.Collections.Specialized;using System.Linq;using System.Threading.Tasks;using System.Runtime.CompilerServices;
class HttpListenerResponse { public int StatusCode=200; public object? Body; }
class HttpListenerRequest { public NameValueCollection QueryString=new(); }
class ModelId { public string Entry="fixture"; }
class Progress { public List<ModelId> DiscoveredCards=new();public List<ModelId> DiscoveredRelics=new(); }
class SaveManager { public static SaveManager? Instance;public Progress? Progress;public int CurrentProfileId=2; }
class Test {
const int DefaultWikiSearchLimit=10,MaxWikiSearchLimit=50;
static bool Fail; static Task<T> RunOnMainThread<T>(Func<T> f) { if(Fail)throw new Exception("fixture");return Task.FromResult(f()); }
static CompendiumSnapshot BuildCompendiumSnapshot() { if(SaveManager.Instance?.Progress==null)return MISSING;return new CompendiumSnapshot(); }
static object? BuildRunHistorySection(CompendiumSnapshot s)=>null;static string? NormalizePathForJson(string? p)=>p;static object? BuildCurrentRunContext(CompendiumSnapshot s)=>null;
record WikiCandidate(string Name);
static IEnumerable<WikiCandidate> BuildCardWikiCandidates(HashSet<string> ids)=>Array.Empty<WikiCandidate>();static IEnumerable<WikiCandidate> BuildRelicWikiCandidates(HashSet<string> ids)=>Array.Empty<WikiCandidate>();static int ScoreWikiCandidate(string q,WikiCandidate c)=>1;static object BuildWikiResult(WikiCandidate c,int score)=>c;
static void SendJson(HttpListenerResponse r,object data)=>r.Body=data;
static int Checks;static void Check(bool ok,string m){Checks++;if(!ok)throw new Exception(m);}
static void Expect(HttpListenerResponse r,int status,string? code){Check(r.StatusCode==status,"HTTP status "+status);var d=(Dictionary<string,object?>)r.Body!;Check((string?)d["status"]==(code==null?"ok":"error"),"envelope");if(code!=null){Check(d.TryGetValue("error_code",out var c)&&(string?)c==code,"error_code "+code);Check(d.ContainsKey("error"),"diagnostic");}}
static HttpListenerResponse Wiki(string? query,string? type=null){var r=new HttpListenerResponse();var q=new HttpListenerRequest();q.QueryString["query"]=query;q.QueryString["type"]=type;HandleGetWiki(q,r);return r;}
'''.replace('MISSING',missing)
tests=r'''
static void Main(){
 foreach(bool managerAbsent in new[]{true,false}){SaveManager.Instance=managerAbsent?null:new SaveManager();var r=new HttpListenerResponse();HandleGetCompendium(r);Expect(r,503,"profile_data_unavailable");Expect(Wiki("strike"),503,"profile_data_unavailable");}
 Expect(Wiki(null),400,"missing_query");Expect(Wiki("  "),400,"missing_query");Expect(Wiki("strike","bogus"),400,"invalid_item_type");
 var direct=(Dictionary<string,object?>)SearchWiki(" ");Check((string?)direct["error_code"]=="missing_query","direct validation");
 SaveManager.Instance=new SaveManager{Progress=new Progress()};var ok=new HttpListenerResponse();HandleGetCompendium(ok);Expect(ok,200,null);Expect(Wiki("no matches"),200,null);Expect(Wiki("strike","bogus"),400,"invalid_item_type");
 Fail=true;var cr=new HttpListenerResponse();HandleGetCompendium(cr);Expect(cr,500,"compendium_build_failed");Expect(Wiki("strike"),500,"wiki_search_failed");
 Console.WriteLine($"PASS: {Checks} real read-envelope/HTTP checks with simulated profile services");}}
'''
with tempfile.TemporaryDirectory(prefix='sts-read-availability-') as tmp:
 root=Path(tmp);(root/'Program.cs').write_text(stubs+cl+'\n'.join(methods)+tests);dotnet=shutil.which('dotnet');sdk=Path(dotnet).resolve().parent;compiler=sorted(sdk.glob('sdk/9.*/Roslyn/bincore/csc.dll'))[-1];refs=sorted(sdk.glob('packs/Microsoft.NETCore.App.Ref/9.*/ref/net9.0'))[-1];out=root/'Test.dll';subprocess.run([dotnet,str(compiler),'-nologo','-nullable:enable','-langversion:12','-target:exe',f'-out:{out}',*[f'-r:{p}' for p in refs.glob('*.dll')],str(root/'Program.cs')],check=True);(root/'Test.runtimeconfig.json').write_text(json.dumps({'runtimeOptions':{'tfm':'net9.0','framework':{'name':'Microsoft.NETCore.App','version':'9.0.0'}}}));subprocess.run([dotnet,str(out)],check=True)
