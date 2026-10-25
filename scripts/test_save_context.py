#!/usr/bin/env python3
"""Compile source-extracted save context with controlled game stubs and workspace fixtures.
No game installation, network, or real save roots are used. Requires --dotnet-root.
"""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile

REPO = Path(__file__).resolve().parents[1]

def region(source, start, end):
    return source[source.index(start):source.index(end, source.index(start))]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, help='Optional historical Compendium source for red/green checks')
    parser.add_argument('--dotnet-root', type=Path, required=True)
    args = parser.parse_args()
    source = (args.source or REPO / 'McpMod.Compendium.cs').read_text()
    helpers = (REPO / 'McpMod.Helpers.cs').read_text()
    extracted = '\n'.join([
        region(source, '    private sealed class CompendiumSnapshot', '    private static List<Dictionary<string, object?>> BuildEncounterStats'),
        region(source, '    private static Dictionary<string, object?>? BuildCurrentRunContext(CompendiumSnapshot snapshot)', '    private static int CountMapPoints'),
        region(source, '    private static void CopyJsonScalar', '    private static string? FindRunHistoryDirectory'),
        region(source, '    private static string GetProfileRootFromProgressPath', '    private static IEnumerable<string> EnumerateSaveRoots'),
        region(source, '    private static string? ResolveProfileProgressPath', '    private static object? ToJsonSafe'),
        region(source, '    private static List<Dictionary<string, object?>> SortDictionaryListByStringField', '    private static Dictionary<string, object?> BuildRunHistoryProgressMembers'),
        region(helpers, '    private static string? NormalizePathForJson', '    private static object? GetInstanceFieldValue'),
    ])
    extracted += region((REPO / 'McpMod.Snapshots.cs').read_text(), '    private static string TryGetActiveRunSaveFileName()', '    private static RunSnapshotMetadata? FindSnapshot')
    # Actual response/state callsite checks complement runtime tests of the extracted closure.
    response = region(source, '    private static object BuildCompendiumResponse', '    private sealed class CompendiumSnapshot')
    for field, expr in [('progress_path', 'snapshot.ProgressPath'), ('resolved_progress_path', 'snapshot.ResolvedProgressPath'), ('profile_root', 'snapshot.ProfileRoot')]:
        assert f'["{field}"] = NormalizePathForJson({expr})' in response
    assert '["history_path"] = NormalizePathForJson(historyDirectory)' in source
    assert 'ResolvedProgressPath = ResolveProfileProgressPath(profileId)' in source
    for file in ['McpMod.StateBuilder.cs', 'McpMod.MultiplayerState.cs']:
        state = (REPO / file).read_text()
        assert 'result["current_run"] = BuildActiveRunContext();' in state
        assert 'result["player"] = BuildPlayerState(' in state
    fixture = r'''
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
class SaveManager { public static SaveManager? Instance; public int CurrentProfileId = 2; }
class RunManager { public static RunManager? Instance; public bool IsInProgress; public NetService NetService = new(); }
class NetService { public NetType Type; }
enum NetType { Singleplayer, Multiplayer }
static class NetExtensions { public static bool IsMultiplayer(this NetType t) => t == NetType.Multiplayer; }
class Program {
const string SingleplayerRunSaveFileName="current_run.save", MultiplayerRunSaveFileName="current_run_mp.save";
static string? ProgressPath;
static string[] Roots = Array.Empty<string>();
static string? GetProfileProgressPath(int profileId) => ProgressPath;
static IEnumerable<string> EnumerateSaveRoots() => Roots;
static void Check(bool value, string name) { if (!value) throw new Exception(name); }
static void Main(string[] args) {
Check(BuildActiveRunContext() == null, "no manager");
SaveManager.Instance = new SaveManager();
Check(BuildActiveRunContext() == null, "no run manager");
RunManager.Instance = new RunManager { IsInProgress = true };
ProgressPath = @"modded\profile2\saves\progress.save";
var missing = BuildActiveRunContext()!;
Check((string)missing["progress_path"]! == "modded/profile2/saves/progress.save", "normalize progress");
Check((string)missing["profile_root"]! == "modded/profile2", "profile scope");
Check((string)missing["save_scope"]! == "modded", "save scope");
Check(missing.ContainsKey("limitation") && !missing.ContainsKey("run_id"), "unsaved identity unavailable");
Check(BuildCurrentRunContext(false, 2, "modded", ProgressPath, "modded/profile2") == null, "inactive run");
var first = Path.Combine(args[0], "first"); var second = Path.Combine(args[0], "second");
Roots = new[] { first, second };
var saves = Path.Combine(second, "modded/profile2/saves"); Directory.CreateDirectory(saves);
var save = Path.Combine(saves, "current_run.save");
File.WriteAllText(Path.Combine(saves, "progress.save"), "{}");
File.WriteAllText(save, "{\"start_time\":123,\"save_time\":456,\"run_time\":99,\"game_mode\":\"standard\",\"ascension\":3,\"current_act_index\":1,\"schema_version\":9,\"platform_type\":\"Steam\",\"rng\":{\"seed\":\"abc\"}}");
var live = BuildActiveRunContext()!;
var snapshot = new CompendiumSnapshot { IsRunInProgress = true, ProfileId = 2, SaveScope = "modded", ProgressPath = ProgressPath, ProfileRoot = "modded/profile2" };
Check((string)BuildCurrentRunContext(snapshot)!["run_id"]! == (string)live["run_id"]!, "snapshot wrapper identity parity");
Check(ResolveCurrentRunPath(snapshot) == save, "snapshot path wrapper parity");
Check((string)live["run_id"]! == "modded:profile2:123", "stable identity");
Check((string)live["seed"]! == "abc" && (long)live["ascension"]! == 3, "save metadata");
Check((string)live["resolved_progress_path"]! == Path.Combine(saves, "progress.save"), "resolved fallback");
Check((string)live["save_path"]! == save, "fallback probes later roots");
// Live context follows the same mode decision as snapshot operations. SP compendium
// context intentionally remains on its documented current_run.save file.
RunManager.Instance.NetService.Type = NetType.Multiplayer;
var mpSave = Path.Combine(saves, "current_run_mp.save");
File.WriteAllText(mpSave, "{\"start_time\":999,\"rng\":{\"seed\":\"active-mp\"}}");
Check(TryGetActiveRunSaveFileName() == "current_run_mp.save", "snapshot mode is multiplayer");
var mp = BuildActiveRunContext()!;
Check((string)mp["seed"]! == "active-mp", "multiplayer seed, not stale singleplayer seed");
Check((string)mp["run_id"]! == "modded:profile2:999", "multiplayer attempt identity");
Check((string)mp["save_path"]! == mpSave, "multiplayer path");
Check((string)BuildCurrentRunContext(snapshot)!["seed"]! == "abc", "compendium keeps documented SP scope");
File.Delete(mpSave);
var missingMp = BuildActiveRunContext()!;
Check(!missingMp.ContainsKey("seed") && !missingMp.ContainsKey("run_id") && !missingMp.ContainsKey("save_path"), "missing multiplayer never falls back to SP");
Check(((string)missingMp["limitation"]!).Contains("current_run_mp.save"), "missing MP limitation names correct file");
RunManager.Instance.NetService.Type = NetType.Singleplayer;
Check((string)BuildActiveRunContext()!["seed"]! == "abc", "switch back to SP");

// Absolute active profile location must win over fallback roots.
var active = Path.Combine(args[0], "active/saves"); Directory.CreateDirectory(active);
var activeSave = Path.Combine(active, "current_run.save"); File.WriteAllText(activeSave, "{\"start_time\":789}");
ProgressPath = Path.Combine(active, "progress.save");
Check(ResolveCurrentRunPath(ProgressPath, "modded/profile2") == activeSave, "absolute active priority");
Check((string)BuildActiveRunContext()!["run_id"]! == "vanilla:profile2:789", "active identity");
RunManager.Instance.NetService.Type = NetType.Multiplayer;
var rootedMp = Path.Combine(active, "current_run_mp.save"); File.WriteAllText(rootedMp, "{\"start_time\":1001}");
Check((string)BuildActiveRunContext()!["save_path"]! == rootedMp, "rooted multiplayer location is authoritative");
Check((string)BuildActiveRunContext()!["run_id"]! == "vanilla:profile2:1001", "rooted multiplayer identity");
File.Delete(rootedMp);
Check(!BuildActiveRunContext()!.ContainsKey("run_id"), "missing rooted MP cannot use rooted SP or fallback roots");
RunManager.Instance.NetService.Type = NetType.Singleplayer;
File.WriteAllText(activeSave, "broken json");
var broken = BuildActiveRunContext()!;
Check(broken.ContainsKey("parse_error") && !broken.ContainsKey("run_id"), "parse failure isolated");
File.WriteAllText(activeSave, "{\"rng\":null}");
var noStart = BuildActiveRunContext()!;
Check(!noStart.ContainsKey("run_id") && !noStart.ContainsKey("seed"), "missing identity not invented");
Check(NormalizePathForJson(null) == null && NormalizePathForJson(" ") == " ", "optional paths");
var items = new List<Dictionary<string, object?>> { new() { ["id"]="z" }, new() { ["id"]="A" }, new() };
var sorted = SortDictionaryListByStringField(items, "id");
Check(!sorted[0].ContainsKey("id") && (string)sorted[1]["id"]! == "A", "ordinal missing-first ordering");
Check((string)items[0]["id"]! == "z", "sorting does not mutate input");
Console.WriteLine("save context runtime checks passed");
}
'''
    sdk = args.dotnet_root / 'sdk/9.0.319/Roslyn/bincore/csc.dll'
    refs = sorted((args.dotnet_root / 'packs/Microsoft.NETCore.App.Ref/9.0.21/ref/net9.0').glob('*.dll'))
    assert sdk.exists() and refs
    mutations = {
        'baseline': extracted,
        'mode_forced_singleplayer': extracted.replace('TryGetActiveRunSaveFileName());', 'SingleplayerRunSaveFileName);'),
        'resolver_forced_singleplayer': extracted.replace('ResolveCurrentRunPath(progressPath, profileRoot, runSaveFileName)', 'ResolveCurrentRunPath(progressPath, profileRoot)'),
        'unnormalized_progress': extracted.replace('["progress_path"] = NormalizePathForJson(progressPath)', '["progress_path"] = progressPath'),
        'wrong_run_identity': extracted.replace('{saveScope}:profile{profileId}:{startTime}', '{saveScope}:profile0:{startTime}'),
        'inactive_gate_removed': extracted.replace('if (!isRunInProgress)', 'if (false)'),
        'sort_reversed': extracted.replace('.OrderBy(item =>', '.OrderByDescending(item =>'),
        'active_path_priority_removed': extracted.replace('if (saveDirectory != null)', 'if (false)'),
    }
    with tempfile.TemporaryDirectory(prefix='.save-context-test-', dir=REPO) as directory:
        temp = Path(directory)
        for name, methods in mutations.items():
            cs = temp / f'{name}.cs'; dll = temp / f'{name}.dll'
            cs.write_text(fixture + methods + '\n}')
            result = subprocess.run([str(args.dotnet_root/'dotnet'), str(sdk), '-nologo', '-nullable:enable', '-target:exe', f'-out:{dll}', *[f'-r:{r}' for r in refs], str(cs)], capture_output=True, text=True)
            assert result.returncode == 0, result.stdout + result.stderr
            dll.with_suffix('.runtimeconfig.json').write_text(json.dumps({'runtimeOptions': {'tfm':'net9.0','framework':{'name':'Microsoft.NETCore.App','version':'9.0.21'}}}))
            case = temp/name; case.mkdir()
            result = subprocess.run([str(args.dotnet_root/'dotnet'), str(dll), str(case)], capture_output=True, text=True)
            if name == 'baseline':
                assert result.returncode == 0, result.stdout + result.stderr
                print(result.stdout.strip())
            else:
                assert result.returncode != 0, f'mutation survived: {name}'
                print(f'mutation killed: {name}')
    print(f'source callsite checks passed; {len(mutations) - 1} behavioral mutations killed')

if __name__ == '__main__':
    main()
