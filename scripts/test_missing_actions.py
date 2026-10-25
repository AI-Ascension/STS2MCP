#!/usr/bin/env python3
"""Focused source-contract and extracted-C# tests; not a game integration build.

Run: python3 scripts/test_missing_actions.py --dotnet /path/to/dotnet
Optional --source tests another Actions.cs (e.g. the pre-fix revision).
No MSBuild, package restore, proprietary DLLs, or filesystem permission changes.
"""
import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def method(source, name):
    # All target methods are class-level members with four-space indentation.
    match = re.search(r'^    (?:private|internal) static [^\n]*\b' + name + r'\(', source, re.M)
    assert match, f'missing method: {name}'
    end = re.search(r'^    }$', source[match.start():], re.M)
    assert end, f'unclosed method: {name}'
    return source[match.start():match.start() + end.end()]


def contracts(source):
    menu = method(source, 'ExecuteMenuSelect')
    discard = method(source, 'ExecuteDiscardPotion')
    assert '"discard_potion" => ExecuteDiscardPotion(player, data)' in method(source, 'ExecuteAction')
    assert menu.index('option = option.Trim()') < menu.index('Engine.GetMainLoop()')
    assert '"missing_menu_option"' in menu and '"unknown_menu_option"' in menu
    assert menu.index('FindVisibleGenericFtue') < menu.index('FindFirst<NCharacterSelectScreen>')
    assert menu.index('FindFirst<NCharacterSelectScreen>') < menu.index('FindFirst<NMainMenu>')
    assert 'ExecuteCharacterSelectMenuOption(charSelect, option, seed)' in menu
    assert 'TryRevealVisibleTimelineEpoch' in menu
    # All menu closure methods must remain present; these are not stubbed successes.
    names = ['TryRevealVisibleTimelineEpoch', 'TimelineUnlocksNeedManualRevealFromOpenTimeline',
             'TimelineUnlocksNeedManualReveal', 'ExecutePopupOption', 'ExecuteProfileSelectMenuOption',
             'ExecuteJoinScreenMenuOption', 'ExecuteLoadLobbyMenuOption', 'ExecuteCharacterSelectMenuOption',
             'TryHandleQueuedTimelineUnlock', 'TryPeekQueuedTimelineScreen', 'IsTimelineScreenBusy',
             'GetQueuedTimelineEpochIds', 'AddEpochIdsFromObject', 'GetProgressEpochState',
             'GetProgressEpochIdsByState', 'ClickMenuButtonField']
    for name in names:
        method(source, name)
    reveal = method(source, 'TryRevealVisibleTimelineEpoch')
    for guard in ['EpochSlotState.Obtained', 'pendingSet.Contains(epochId)', 'slot.HasSpawned', 'IsNodeVisible(slot)']:
        assert guard in reveal, f'missing Timeline guard: {guard}'
    assert discard.index('potion.IsQueued') < discard.index('PotionCmd.Discard(potion)')
    assert discard.index('slot < 0 || slot >= player.PotionSlots.Count') < discard.index('GetPotionAtSlotIndex(slot)')
    click = method(source, 'ClickMenuButtonField')
    assert click.index('!clickable.Visible || !clickable.IsVisibleInTree()') < click.index('clickable.ForceClick()')
    assert click.index('!clickable.IsEnabled') < click.index('clickable.ForceClick()')


def compiled_tests(source, dotnet):
    sdk_root = Path(dotnet).resolve().parent
    csc = sorted((sdk_root / 'sdk').glob('*/Roslyn/bincore/csc.dll'))[-1]
    refs = sorted((sdk_root / 'packs/Microsoft.NETCore.App.Ref').glob('*/ref/net9.0'))[-1]
    runtime = sorted((sdk_root / 'shared/Microsoft.NETCore.App').iterdir())[-1].name
    members = '\n'.join(method(source, name) for name in
                        ['ExecuteDiscardPotion', 'ClickMenuButtonField', 'ExecutePopupOption'])
    harness = r'''
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
class Potion { public bool IsQueued; public string Title = "Test"; }
class Player {
    public List<Potion?> PotionSlots = new() { new Potion(), null };
    public Potion? GetPotionAtSlotIndex(int slot) => PotionSlots[slot];
}
static class PotionCmd { public static int Calls; public static Potion? Last;
    public static object Discard(Potion potion) { Calls++; Last = potion; return new object(); }
}
class NClickableControl { public bool Visible = true, InTree = true, IsEnabled = true; public int Clicks;
    public bool IsVisibleInTree() => InTree; public void ForceClick() => Clicks++;
}
class Owner { public NClickableControl Button = new(); }
static class Test {
    static Dictionary<string, object?> Error(string message) => new() { ["status"] = "error", ["error"] = message };
    static string? SafeGetText(Func<string> f) => f();
    static object? GetInstanceFieldValue(object o, string field) => o.GetType().GetField(field)?.GetValue(o);
    static bool IsPopupButtonActionable(NClickableControl b) => b.Visible && b.InTree && b.IsEnabled;
    static int Checks;
    static void Check(bool ok, string label) { Checks++; if (!ok) throw new Exception(label); }
    static bool Ok(Dictionary<string, object?> result) => (string?)result["status"] == "ok";
    static Dictionary<string, JsonElement> Slot(int slot) => new() { ["slot"] = JsonSerializer.SerializeToElement(slot) };
    public static void Main() {
        var p = new Player();
        Check(!Ok(ExecuteDiscardPotion(p, new())), "missing slot");
        Check(!Ok(ExecuteDiscardPotion(p, Slot(-1))), "negative slot");
        Check(!Ok(ExecuteDiscardPotion(p, Slot(2))), "upper bound slot");
        Check(!Ok(ExecuteDiscardPotion(p, Slot(1))), "empty slot");
        p.PotionSlots[0]!.IsQueued = true;
        Check(!Ok(ExecuteDiscardPotion(p, Slot(0))), "queued potion");
        Check(PotionCmd.Calls == 0, "no invalid discard side effects");
        p.PotionSlots[0]!.IsQueued = false;
        Check(Ok(ExecuteDiscardPotion(p, Slot(0))), "valid discard");
        Check(PotionCmd.Calls == 1 && PotionCmd.Last == p.PotionSlots[0], "correct potion dispatched once");
        var o = new Owner();
        Check(!Ok(ClickMenuButtonField(o, "Missing", "ok")), "missing button");
        o.Button.Visible = false;
        Check(!Ok(ClickMenuButtonField(o, "Button", "ok")), "hidden button");
        o.Button.Visible = true; o.Button.InTree = false;
        Check(!Ok(ClickMenuButtonField(o, "Button", "ok")), "detached button");
        o.Button.InTree = true; o.Button.IsEnabled = false;
        Check(!Ok(ClickMenuButtonField(o, "Button", "ok")), "disabled button");
        Check(o.Button.Clicks == 0, "invalid menu requests do not click");
        o.Button.IsEnabled = true;
        Check(Ok(ClickMenuButtonField(o, "Button", "ok")) && o.Button.Clicks == 1, "valid menu click");
        var options = new List<(string Name, NClickableControl Button)> { ("ignore", o.Button) };
        Check(!Ok(ExecutePopupOption(options, "unknown")) && o.Button.Clicks == 1, "unknown popup option");
        o.Button.IsEnabled = false;
        Check(!Ok(ExecutePopupOption(options, "ignore")) && o.Button.Clicks == 1, "disabled popup");
        o.Button.IsEnabled = true;
        Check(Ok(ExecutePopupOption(options, "IGNORE")) && o.Button.Clicks == 2, "case insensitive popup");
        Console.WriteLine($"PASS: {Checks} extracted-C# behavior assertions");
    }
'''
    with tempfile.TemporaryDirectory(prefix='sts-missing-actions-') as temp:
        folder = Path(temp)
        (folder / 'Test.cs').write_text(harness + members + '\n}\n')
        output = folder / 'Test.dll'
        command = [str(dotnet), str(csc), '-nologo', '-nullable:enable', '-target:exe', f'-out:{output}']
        command += [f'-r:{p}' for p in refs.glob('*.dll')]
        command += [str(folder / 'Test.cs')]
        subprocess.run(command, check=True)
        (folder / 'Test.runtimeconfig.json').write_text(json.dumps({'runtimeOptions': {
            'tfm': 'net9.0', 'framework': {'name': 'Microsoft.NETCore.App', 'version': runtime}}}))
        subprocess.run([str(dotnet), str(output)], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'McpMod.Actions.cs')
    parser.add_argument('--dotnet', type=Path, required=True)
    parser.add_argument('--verify-origin', action='store_true',
                        help='Verify restored methods against ancestor, except the reviewed embark-readiness refinement')
    args = parser.parse_args()
    source = args.source.read_text()
    if args.verify_origin:
        origin = '4431b1e5a5c2e34fcc7dbcf5617236602e334f49'
        subprocess.run(['git', 'merge-base', '--is-ancestor', origin, 'HEAD'], cwd=ROOT, check=True)
        baseline = subprocess.check_output(['git', 'show', f'{origin}:McpMod.Actions.cs'], cwd=ROOT, text=True)
        tail = baseline[baseline.index('    internal static Dictionary<string, object?> ExecuteMenuSelect('):]
        names = ['ExecuteDiscardPotion'] + re.findall(r'^    (?:private|internal) static [^\n]*\b(\w+)\(', tail, re.M)
        for name in names:
            if name == 'ExecuteCharacterSelectMenuOption':
                body = method(source, name)
                guard = 'embarkBtn is not NClickableControl embarkClickable || !IsControlVisibleOrActionable(embarkClickable)'
                assert guard in body and body.index(guard) < body.index('charSelect.Lobby.SetSeed(seed)'), 'embark guard must precede seed mutation'
            else:
                assert method(source, name) == method(baseline, name), f'changed from ancestor: {name}'
        print(f'PASS: {len(names)-1} methods exactly match ancestor {origin}; reviewed embark refinement checked separately', flush=True)
    contracts(source)
    print('PASS: menu/discard dispatch, closure, ordering and readiness contracts', flush=True)
    mutants = [source.replace('ExecuteMenuSelect(string', 'DeletedMenuSelect(string'),
               source.replace('ExecuteDiscardPotion(Player', 'DeletedDiscardPotion(Player'),
               source.replace('"discard_potion" => ExecuteDiscardPotion(player, data),', ''),
               source.replace('slot.HasSpawned', 'true'),
               source.replace('potion.IsQueued', 'false'),
               source.replace('!clickable.Visible || !clickable.IsVisibleInTree()', 'false')]
    for mutant in mutants:
        try:
            contracts(mutant)
        except (AssertionError, ValueError):
            continue
        raise AssertionError('contract checks survived a regression mutation')
    print(f'PASS: {len(mutants)} removal/readiness regression mutants rejected', flush=True)
    compiled_tests(source, args.dotnet)


if __name__ == '__main__':
    main()
