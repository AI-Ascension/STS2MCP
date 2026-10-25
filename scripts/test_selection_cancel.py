#!/usr/bin/env python3
"""Compile the actual cancellation method with simulated controls (not a game test).

Requires the .NET 9 SDK. Pass --source to test a historical Actions.cs file.
"""
import argparse
import json
import shutil
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser()
p.add_argument('--source', type=Path, default=Path(__file__).resolve().parents[1] / 'McpMod.Actions.cs')
a = p.parse_args()
source = a.source.read_text()
start = source.index('    private static Dictionary<string, object?> ExecuteCancelSelection()')
end = source.index('    private static ', start + 10)
method = source[start:end]
stubs = '''
using System;
using System.Diagnostics.CodeAnalysis;
using System.Collections.Generic;
namespace Godot {
 public class Control {
  public bool Visible = true;
  public Dictionary<string, Control> Nodes = new();
  public T? GetNodeOrNull<T>(string name) where T: Control => Nodes.GetValueOrDefault(name) as T;
 }
}
class NClickableControl : Godot.Control {
 public bool IsEnabled = true;
 public int Clicks;
 public void ForceClick() { Clicks++; }
}
class NBackButton : NClickableControl { }
class NCardGridSelectionScreen : Godot.Control { }
class NChooseACardSelectionScreen : Godot.Control { }
class NOverlayStack {
 public static NOverlayStack Instance = new();
 public Godot.Control? Top;
 public Godot.Control? Peek() => Top;
}
class Test {
 static bool IsControlVisibleOrActionable([NotNullWhen(true)] NClickableControl? b) => b != null && b.Visible && b.IsEnabled;
 static Dictionary<string, object?> Error(string message) => new() { ["status"] = "error", ["message"] = message };
'''
tests = '''
 static void Check(bool ok, string message) { if (!ok) throw new Exception(message); }
 static void Main() {
  int count = 0;
  foreach (var name in new[] { "%UpgradeSinglePreviewContainer", "%UpgradeMultiPreviewContainer", "%PreviewContainer", "%EnchantSinglePreviewContainer", "EnchantSinglePreviewContainer", "%EnchantMultiPreviewContainer", "EnchantMultiPreviewContainer" }) {
   foreach (var cancelName in new[] { "Cancel", "%PreviewCancel" }) {
    var screen = new NCardGridSelectionScreen();
    var container = new Godot.Control();
    var cancel = new NBackButton();
    var close = new NBackButton();
    container.Nodes[cancelName] = cancel;
    screen.Nodes[name] = container;
    screen.Nodes["%Close"] = close;
    NOverlayStack.Instance.Top = screen;
    var result = ExecuteCancelSelection();
    Check((string?)result["status"] == "ok" && cancel.Clicks == 1 && close.Clicks == 0, name + " must cancel preview, not close screen");
    count++;
    cancel.IsEnabled = false; close.IsEnabled = false;
    Check((string?)ExecuteCancelSelection()["status"] == "error" && cancel.Clicks == 1, "disabled buttons must not click");
    count++;
    cancel.IsEnabled = true; container.Visible = false;
    Check((string?)ExecuteCancelSelection()["status"] == "error" && cancel.Clicks == 1, "hidden preview must not click");
    count++;
   }
  }
  var choose = new NChooseACardSelectionScreen();
  var skip = new NClickableControl(); choose.Nodes["SkipButton"] = skip;
  NOverlayStack.Instance.Top = choose;
  Check((string?)ExecuteCancelSelection()["status"] == "ok" && skip.Clicks == 1, "choose-card skip"); count++;
  NOverlayStack.Instance.Top = null;
  Check((string?)ExecuteCancelSelection()["status"] == "error", "no screen"); count++;
  Console.WriteLine($"PASS: {count} extracted cancellation checks (simulated controls)");
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
