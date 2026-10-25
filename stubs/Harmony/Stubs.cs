// Minimal HarmonyLib stub — STS2_MCP does not directly use Harmony types,
// but the project references 0Harmony.dll so a valid assembly is required.
namespace HarmonyLib
{
    public class Harmony
    {
        public Harmony(string id) { }
        public void PatchAll() { }
    }

    [System.AttributeUsage(System.AttributeTargets.Class)]
    public class HarmonyPatch : System.Attribute
    {
        public HarmonyPatch(System.Type type, string method) { }
        public HarmonyPatch(System.Type type) { }
    }

    [System.AttributeUsage(System.AttributeTargets.Method)]
    public class HarmonyPostfix : System.Attribute { }

    [System.AttributeUsage(System.AttributeTargets.Method)]
    public class HarmonyPrefix : System.Attribute { }
}
