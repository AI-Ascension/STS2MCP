// Stub assembly for GodotSharp — provides just enough for STS2_MCP to compile.
#pragma warning disable CS8618, CS0067
using System;
using System.Collections.Generic;

namespace Godot
{
    // -------------------------------------------------------------------------
    // Variant (simplified)
    // -------------------------------------------------------------------------
    public struct Variant
    {
        public enum Type { Nil, Bool, Int, Float, String, Object }

        public Type VariantType { get; }

        public string AsString() => string.Empty;
        public bool AsBool() => false;
        public int AsInt32() => 0;

        public static implicit operator Variant(string _) => default;
        public static implicit operator Variant(int _) => default;
        public static implicit operator Variant(bool _) => default;
        public static implicit operator Variant(GodotObject? _) => default;
    }

    // -------------------------------------------------------------------------
    // StringName
    // -------------------------------------------------------------------------
    public class StringName
    {
        private readonly string _value;
        public StringName(string value) { _value = value; }
        public StringName() { _value = string.Empty; }
        public static implicit operator StringName(string s) => new StringName(s);
        public static implicit operator string(StringName s) => s._value;
        public override string ToString() => _value;
    }

    // -------------------------------------------------------------------------
    // NodePath
    // -------------------------------------------------------------------------
    public class NodePath
    {
        private readonly string _path;
        public NodePath(string path) { _path = path; }
        public NodePath() { _path = string.Empty; }
        public static implicit operator NodePath(string s) => new NodePath(s);
        public override string ToString() => _path;
    }

    // -------------------------------------------------------------------------
    // Vector2
    // -------------------------------------------------------------------------
    public struct Vector2
    {
        public float X;
        public float Y;
        public Vector2(float x, float y) { X = x; Y = y; }
        public int CompareTo(Vector2 other)
        {
            int xComparison = X.CompareTo(other.X);
            return xComparison != 0 ? xComparison : Y.CompareTo(other.Y);
        }
    }

    // -------------------------------------------------------------------------
    // Callable
    // -------------------------------------------------------------------------
    public struct Callable
    {
        public static Callable From(Action action) => default;
        public static Callable From(Func<Variant> func) => default;
    }

    // -------------------------------------------------------------------------
    // GodotObject
    // -------------------------------------------------------------------------
    public class GodotObject
    {
        public static bool IsInstanceValid(GodotObject? obj) => obj != null;

        public virtual Variant Get(StringName property) => default;
        public virtual Variant Get(string property) => default;

        public virtual void EmitSignal(StringName signal, params Variant[] args) { }
        public virtual void EmitSignal(StringName signal, GodotObject arg) { }
    }

    // -------------------------------------------------------------------------
    // Node
    // -------------------------------------------------------------------------
    public class Node : GodotObject
    {
        public string Name { get; set; } = string.Empty;

        public virtual Godot.Collections.Array<Node> GetChildren(bool includeInternal = false)
            => new Godot.Collections.Array<Node>();

        public virtual T? GetNodeOrNull<T>(string path) where T : Node => null;
        public virtual T? GetNodeOrNull<T>(NodePath path) where T : Node => null;
        public virtual T GetNode<T>(NodePath path) where T : Node => default!;
        public virtual Node? GetNodeOrNull(string path) => null;
        public virtual void AddChild(Node node, bool forceReadableName = false) { }
    }

    // -------------------------------------------------------------------------
    // Control (UI node base)
    // -------------------------------------------------------------------------
    public class Control : Node
    {
        public virtual Vector2 GlobalPosition { get; set; }
        public virtual bool Visible { get; set; } = true;
        public virtual bool IsEnabled { get; protected set; } = true;
    }

    // -------------------------------------------------------------------------
    // Window (SceneTree.Root type)
    // -------------------------------------------------------------------------
    public class Window : Node { }

    // -------------------------------------------------------------------------
    // SceneTree
    // -------------------------------------------------------------------------
    public class SceneTree : Node
    {
        public static new class SignalName
        {
            public static readonly StringName ProcessFrame = new StringName("process_frame");
        }

        public Window Root { get; } = new Window();

        public Error Connect(StringName signal, Callable callable, uint flags = 0) => Error.Ok;
    }

    public enum Error { Ok = 0 }

    // -------------------------------------------------------------------------
    // Engine
    // -------------------------------------------------------------------------
    public static class Engine
    {
        public static GodotObject GetMainLoop() => new SceneTree();
    }

    // -------------------------------------------------------------------------
    // GD (logging helpers)
    // -------------------------------------------------------------------------
    public static class GD
    {
        public static void Print(params object?[] args) { }
        public static void PrintErr(params object?[] args) { }
        public static void PushWarning(params object?[] args) { }
        public static void PushError(params object?[] args) { }
    }
}

// Godot.Collections — Array<T> needed for GetChildren
namespace Godot.Collections
{
    using System.Collections;
    using System.Collections.Generic;

    public class Array<T> : IEnumerable<T>
    {
        private readonly List<T> _items = new();
        public int Count => _items.Count;
        public T this[int i] => _items[i];
        public void Add(T item) => _items.Add(item);
        public IEnumerator<T> GetEnumerator() => _items.GetEnumerator();
        IEnumerator IEnumerable.GetEnumerator() => _items.GetEnumerator();
    }
}
