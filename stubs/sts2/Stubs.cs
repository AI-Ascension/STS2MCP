// Stub assembly for sts2.dll — all MegaCrit.Sts2.Core.* types needed by STS2_MCP.
#pragma warning disable CS8618, CS8625, CS8603, CS0067
using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using Godot;

// =============================================================================
// MegaCrit.Sts2.Core.Localization
// =============================================================================
namespace MegaCrit.Sts2.Core.Localization
{
    public class LocString
    {
        public string GetFormattedText() => string.Empty;
        public override string ToString() => string.Empty;
        public static implicit operator string(LocString? l) => l?.GetFormattedText() ?? string.Empty;
    }

    public class SmartDescription : LocString
    {
        public SmartDescription Add(string key, object? value) => this;
    }
}

// =============================================================================
// MegaCrit.Sts2.Core.Models
// =============================================================================
namespace MegaCrit.Sts2.Core.Models
{
    using MegaCrit.Sts2.Core.HoverTips;
    using MegaCrit.Sts2.Core.Localization;

    public struct ModelId
    {
        public string Entry { get; }
        public ModelId(string entry) { Entry = entry; }
        public override string ToString() => Entry;
    }

    public enum Rarity { Starter, Common, Uncommon, Rare, Special, Basic }
    public enum PowerType { Buff, Debuff, Neutral }

    public class RelicModel
    {
        public ModelId Id { get; }
        public LocString Title { get; } = new LocString();
        public LocString DynamicDescription { get; } = new LocString();
        public bool ShowCounter { get; }
        public int DisplayAmount { get; }
        public Rarity Rarity { get; }
        public IEnumerable<IHoverTip> HoverTipsExcludingRelic { get; } = Array.Empty<IHoverTip>();
    }

    public class OrbModel
    {
        public ModelId Id { get; }
        public LocString Title { get; } = new LocString();
        public SmartDescription SmartDescription { get; } = new SmartDescription();
        public int PassiveVal { get; }
        public int EvokeVal { get; }
        public IEnumerable<IHoverTip> HoverTips { get; } = Array.Empty<IHoverTip>();
        public MegaCrit.Sts2.Core.Entities.Players.Player Owner { get; } = default!;
    }

    public class OrbQueue
    {
        public int Capacity { get; }
        public IList<OrbModel> Orbs { get; } = new List<OrbModel>();
    }

    public class CardPoolModel
    {
        public LocString Title { get; } = new LocString();
    }
}

// =============================================================================
// MegaCrit.Sts2.Core.HoverTips
// =============================================================================
namespace MegaCrit.Sts2.Core.HoverTips
{
    using MegaCrit.Sts2.Core.Entities.Cards;

    public interface IHoverTip
    {
        string Id { get; }
        static IEnumerable<IHoverTip> RemoveDupes(IEnumerable<IHoverTip> tips) => tips;
    }

    public class HoverTip : IHoverTip
    {
        public string Id { get; } = string.Empty;
        public string? Title { get; }
        public string Description { get; } = string.Empty;
    }

    public class CardHoverTip : IHoverTip
    {
        public string Id { get; } = string.Empty;
        public CardModel Card { get; } = default!;
    }
}

// =============================================================================
// MegaCrit.Sts2.Core.Modding
// =============================================================================
namespace MegaCrit.Sts2.Core.Modding
{
    [AttributeUsage(AttributeTargets.Class)]
    public class ModInitializer : Attribute
    {
        public ModInitializer(string methodName) { }
    }
}

// =============================================================================
// MegaCrit.Sts2.Core.Entities.Cards
// =============================================================================
namespace MegaCrit.Sts2.Core.Entities.Cards
{
    using MegaCrit.Sts2.Core.HoverTips;
    using MegaCrit.Sts2.Core.Localization;
    using MegaCrit.Sts2.Core.Models;

    public enum UnplayableReason { None, NotEnoughEnergy, NotEnoughStars, CantTarget, CantPlayInPile, Unplayable, Other }
    public enum PileType { None, Hand, Draw, Discard, Exhaust }
    public enum CardType { Attack, Skill, Power, Status, Curse }
    public enum TargetType { None, AnyEnemy, AnyAlly, AnyPlayer, Self, AllEnemies, AllAllies }

    public class EnergyCost
    {
        public bool CostsX { get; }
        public int GetAmountToSpend() => 0;
    }

    public class CardModel
    {
        public ModelId Id { get; }
        public LocString Title { get; } = new LocString();
        public LocString Description { get; } = new LocString();
        public CardType Type { get; }
        public EnergyCost EnergyCost { get; } = new EnergyCost();
        public TargetType TargetType { get; }
        public Rarity Rarity { get; }
        public bool IsUpgraded { get; }
        public bool HasStarCostX { get; }
        public int CurrentStarCost { get; }
        public IEnumerable<IHoverTip> HoverTips { get; } = Array.Empty<IHoverTip>();

        public int GetStarCostWithModifiers() => 0;
        public LocString GetDescriptionForPile(PileType pile) => new LocString();
        public bool CanPlay(out UnplayableReason reason, out object? extra)
        {
            reason = UnplayableReason.None;
            extra = null;
            return true;
        }
    }

    public class CardPile
    {
        public IList<CardModel> Cards { get; } = new List<CardModel>();
    }
}

// =============================================================================
// MegaCrit.Sts2.Core.Entities.Creatures
// =============================================================================
namespace MegaCrit.Sts2.Core.Entities.Creatures
{
    using MegaCrit.Sts2.Core.HoverTips;
    using MegaCrit.Sts2.Core.Localization;
    using MegaCrit.Sts2.Core.Models;
    using MegaCrit.Sts2.Core.MonsterMoves.MonsterMoveStateMachine;

    public class PowerModel
    {
        public ModelId Id { get; }
        public LocString Title { get; } = new LocString();
        public int DisplayAmount { get; }
        public int Amount { get; }
        public PowerType Type { get; }
        public bool IsVisible { get; }
        public SmartDescription SmartDescription { get; } = new SmartDescription();
        public IEnumerable<IHoverTip> HoverTips { get; } = Array.Empty<IHoverTip>();
        public Creature Owner { get; } = default!;
    }

    public class MonsterModel
    {
        public ModelId Id { get; }
        public LocString Title { get; } = new LocString();
        public MoveState? NextMove { get; }
    }

    public class Creature
    {
        public bool IsAlive { get; }
        public bool IsDead => !IsAlive;
        public int CurrentHp { get; }
        public int MaxHp { get; }
        public int Block { get; }
        public uint CombatId { get; }
        public MonsterModel? Monster { get; }
        public IEnumerable<PowerModel> Powers { get; } = Array.Empty<PowerModel>();
        public MegaCrit.Sts2.Core.Combat.CombatState? CombatState { get; }
    }
}

// =============================================================================
// MegaCrit.Sts2.Core.Entities.Players
// =============================================================================
namespace MegaCrit.Sts2.Core.Entities.Players
{
    using MegaCrit.Sts2.Core.Entities.Cards;
    using MegaCrit.Sts2.Core.Entities.Creatures;
    using MegaCrit.Sts2.Core.Entities.Potions;
    using MegaCrit.Sts2.Core.Localization;
    using MegaCrit.Sts2.Core.Models;

    public class CharacterModel
    {
        public LocString Title { get; } = new LocString();
        public bool ShouldAlwaysShowStarCounter { get; }
        public CardPoolModel CardPool { get; } = new CardPoolModel();
    }

    public class PlayerCombatState
    {
        public int Energy { get; }
        public int MaxEnergy { get; }
        public int Stars { get; }
        public CardPile Hand { get; } = new CardPile();
        public CardPile DrawPile { get; } = new CardPile();
        public CardPile DiscardPile { get; } = new CardPile();
        public CardPile ExhaustPile { get; } = new CardPile();
        public OrbQueue OrbQueue { get; } = new OrbQueue();
    }

    public class Player
    {
        public Creature Creature { get; } = new Creature();
        public CharacterModel Character { get; } = new CharacterModel();
        public PlayerCombatState? PlayerCombatState { get; }
        public int Gold { get; }
        public IEnumerable<RelicModel> Relics { get; } = Array.Empty<RelicModel>();
        public IList<PotionModel?> PotionSlots { get; } = new List<PotionModel?>();
        public PotionModel? GetPotionAtSlotIndex(int index) => null;
        public MegaCrit.Sts2.Core.Runs.RunState RunState { get; } = default!;
    }
}

// =============================================================================
// MegaCrit.Sts2.Core.Entities.Potions
// =============================================================================
namespace MegaCrit.Sts2.Core.Entities.Potions
{
    using MegaCrit.Sts2.Core.Entities.Cards;
    using MegaCrit.Sts2.Core.Entities.Creatures;
    using MegaCrit.Sts2.Core.Entities.Players;
    using MegaCrit.Sts2.Core.HoverTips;
    using MegaCrit.Sts2.Core.Localization;
    using MegaCrit.Sts2.Core.Models;

    public enum PotionUsage { AnyTime, CombatOnly, AnyTimeExceptBoss, Automatic }

    public class PotionModel
    {
        public ModelId Id { get; }
        public LocString Title { get; } = new LocString();
        public LocString DynamicDescription { get; } = new LocString();
        public bool IsQueued { get; }
        public PotionUsage Usage { get; }
        public TargetType TargetType { get; }
        public bool PassesCustomUsabilityCheck { get; }
        public Player Owner { get; } = default!;
        public IEnumerable<IHoverTip> ExtraHoverTips { get; } = Array.Empty<IHoverTip>();
        public void EnqueueManualUse(Creature? target) { }
    }
}

// =============================================================================
// MegaCrit.Sts2.Core.Entities.Merchant
// =============================================================================
namespace MegaCrit.Sts2.Core.Entities.Merchant
{
    using MegaCrit.Sts2.Core.Entities.Cards;
    using MegaCrit.Sts2.Core.Entities.Potions;
    using MegaCrit.Sts2.Core.Models;

    public class CardCreationResult
    {
        public CardModel? Card { get; }
    }

    public interface IMerchantEntry
    {
        int Cost { get; }
        bool IsStocked { get; }
        bool EnoughGold { get; }
        Task OnTryPurchaseWrapper(MerchantInventory inventory);
    }

    public abstract class MerchantEntryBase : IMerchantEntry
    {
        public int Cost { get; }
        public bool IsStocked { get; }
        public bool EnoughGold { get; }
        public bool IsOnSale { get; }
        public Task OnTryPurchaseWrapper(MerchantInventory inventory) => Task.CompletedTask;
    }

    public class CardMerchantEntry : MerchantEntryBase
    {
        public CardCreationResult? CreationResult { get; }
    }

    public class RelicMerchantEntry : MerchantEntryBase
    {
        public RelicModel? Model { get; }
    }

    public class PotionMerchantEntry : MerchantEntryBase
    {
        public PotionModel? Model { get; }
    }

    public class CardRemovalEntry : MerchantEntryBase { }

    public class MerchantInventory
    {
        public IEnumerable<CardMerchantEntry> CardEntries { get; } = Array.Empty<CardMerchantEntry>();
        public IEnumerable<RelicMerchantEntry> RelicEntries { get; } = Array.Empty<RelicMerchantEntry>();
        public IEnumerable<PotionMerchantEntry> PotionEntries { get; } = Array.Empty<PotionMerchantEntry>();
        public CardRemovalEntry? CardRemovalEntry { get; }
        public IEnumerable<IMerchantEntry> AllEntries { get; } = Array.Empty<IMerchantEntry>();
    }
}

// =============================================================================
// MegaCrit.Sts2.Core.Entities.RestSite
// =============================================================================
namespace MegaCrit.Sts2.Core.Entities.RestSite
{
    using MegaCrit.Sts2.Core.Localization;

    public class RestSiteOption
    {
        public string OptionId { get; } = string.Empty;
        public LocString Title { get; } = new LocString();
        public LocString Description { get; } = new LocString();
        public bool IsEnabled { get; }
    }
}

// =============================================================================
// MegaCrit.Sts2.Core.Events
// =============================================================================
namespace MegaCrit.Sts2.Core.Events
{
    using MegaCrit.Sts2.Core.HoverTips;
    using MegaCrit.Sts2.Core.Localization;
    using MegaCrit.Sts2.Core.Models;

    public class EventOption
    {
        public LocString Title { get; } = new LocString();
        public LocString Description { get; } = new LocString();
        public bool IsLocked { get; }
        public bool IsProceed { get; }
        public bool WasChosen { get; }
        public RelicModel? Relic { get; }
        public IEnumerable<IHoverTip> HoverTips { get; } = Array.Empty<IHoverTip>();
    }

    public class EventModel
    {
        public ModelId Id { get; }
        public LocString Title { get; } = new LocString();
        public LocString Description { get; } = new LocString();
    }

    public class AncientEventModel : EventModel { }
}

// =============================================================================
// MegaCrit.Sts2.Core.Map
// =============================================================================
namespace MegaCrit.Sts2.Core.Map
{
    public enum MapPointType { Start, Monster, Elite, Boss, Event, Shop, Rest, Treasure, Unknown }

    public struct MapCoord
    {
        public int col;
        public int row;
    }

    public class MapPoint
    {
        public MapCoord coord { get; }
        public MapPointType PointType { get; }
        public IList<MapPoint> Children { get; } = new List<MapPoint>();
    }

    public class MapModel
    {
        public MapPoint StartingMapPoint { get; } = new MapPoint();
        public MapPoint BossMapPoint { get; } = new MapPoint();
        public MapPoint? SecondBossMapPoint { get; }
        public IEnumerable<MapPoint> GetAllMapPoints() => Array.Empty<MapPoint>();
        public MapPoint? GetPoint(MapCoord coord) => null;
    }
}

// =============================================================================
// MegaCrit.Sts2.Core.MonsterMoves.Intents
// =============================================================================
namespace MegaCrit.Sts2.Core.MonsterMoves.Intents
{
    using MegaCrit.Sts2.Core.Entities.Creatures;
    using MegaCrit.Sts2.Core.Localization;

    public enum IntentType { Attack, Buff, Debuff, Escape, Sleep, Unknown, Magic, Block, StrongAttack }

    public interface IIntent
    {
        IntentType IntentType { get; }
        LocString GetIntentLabel(IEnumerable<Creature> targets, Creature source);
    }
}

// =============================================================================
// MegaCrit.Sts2.Core.MonsterMoves.MonsterMoveStateMachine
// =============================================================================
namespace MegaCrit.Sts2.Core.MonsterMoves.MonsterMoveStateMachine
{
    using MegaCrit.Sts2.Core.MonsterMoves.Intents;

    public class MoveState
    {
        public IEnumerable<IIntent> Intents { get; } = Array.Empty<IIntent>();
    }
}

// =============================================================================
// MegaCrit.Sts2.Core.Rooms
// =============================================================================
namespace MegaCrit.Sts2.Core.Rooms
{
    using MegaCrit.Sts2.Core.Entities.Merchant;
    using MegaCrit.Sts2.Core.Entities.RestSite;
    using MegaCrit.Sts2.Core.Events;

    public enum RoomType { Monster, Elite, Boss, Event, Shop, Rest, Treasure, Map }

    public abstract class Room { }

    public class CombatRoom : Room
    {
        public RoomType RoomType { get; }
    }

    public class EventRoom : Room
    {
        public EventModel CanonicalEvent { get; } = new EventModel();
    }

    public class MapRoom : Room { }

    public class MerchantRoom : Room
    {
        public MerchantInventory Inventory { get; } = new MerchantInventory();
    }

    public class RestSiteRoom : Room
    {
        public IEnumerable<RestSiteOption> Options { get; } = Array.Empty<RestSiteOption>();
    }

    public class TreasureRoom : Room { }
}

// =============================================================================
// MegaCrit.Sts2.Core.Combat
// =============================================================================
namespace MegaCrit.Sts2.Core.Combat
{
    using MegaCrit.Sts2.Core.Entities.Creatures;
    using MegaCrit.Sts2.Core.Entities.Players;

    public enum Side { Player, Enemy }

    public class CombatState
    {
        public int RoundNumber { get; }
        public Side CurrentSide { get; }
        public IEnumerable<Creature> Enemies { get; } = Array.Empty<Creature>();
        public IEnumerable<Creature> PlayerCreatures { get; } = Array.Empty<Creature>();
        public Creature? GetCreature(uint combatId) => null;
    }

    public class CombatManager
    {
        public static CombatManager Instance { get; } = new CombatManager();
        public bool IsInProgress { get; }
        public bool IsPlayPhase { get; }
        public bool PlayerActionsDisabled { get; }
        public CombatState? DebugOnlyGetState() => null;
        public bool AllPlayersReadyToEndTurn() => false;
        public bool IsPlayerReadyToEndTurn(Player player) => false;
    }
}

// =============================================================================
// MegaCrit.Sts2.Core.Context
// =============================================================================
namespace MegaCrit.Sts2.Core.Context
{
    using MegaCrit.Sts2.Core.Entities.Players;
    using MegaCrit.Sts2.Core.Runs;

    public static class LocalContext
    {
        public static Player? GetMe(RunState runState) => null;
        public static bool IsMe(Player player) => false;
    }
}

// =============================================================================
// MegaCrit.Sts2.Core.Multiplayer.Game
// =============================================================================
namespace MegaCrit.Sts2.Core.Multiplayer.Game
{
    public class NetServiceType
    {
        public bool IsMultiplayer() => false;
        public override string ToString() => "Singleplayer";
    }

    public class NetService
    {
        public NetServiceType Type { get; } = new NetServiceType();
    }
}

// =============================================================================
// MegaCrit.Sts2.Core.Runs
// =============================================================================
namespace MegaCrit.Sts2.Core.Runs
{
    using MegaCrit.Sts2.Core.Entities.Players;
    using MegaCrit.Sts2.Core.Map;
    using MegaCrit.Sts2.Core.Multiplayer.Game;
    using MegaCrit.Sts2.Core.Rooms;

    public class MapSelectionSynchronizer
    {
        public MapPoint? GetVote(Player player) => null;
    }

    public class EventSynchronizer
    {
        public bool IsShared { get; }
        public int? GetPlayerVote(Player player) => null;
    }

    public class TreasureRoomRelicSynchronizer
    {
        public object? CurrentRelics { get; }
        public int? GetPlayerVote(Player player) => null;
    }

    public class ActionQueueSynchronizer
    {
        public void RequestEnqueue(MegaCrit.Sts2.Core.GameActions.IGameAction action) { }
    }

    public class RunState
    {
        public Room? CurrentRoom { get; }
        public int CurrentActIndex { get; }
        public int TotalFloor { get; }
        public int AscensionLevel { get; }
        public MapModel Map { get; } = new MapModel();
        public IList<MapCoord> VisitedMapCoords { get; } = new List<MapCoord>();
        public IList<Player> Players { get; } = new List<Player>();
    }

    public class RunManager
    {
        public static RunManager Instance { get; } = new RunManager();
        public bool IsInProgress { get; }
        public NetService NetService { get; } = new NetService();
        public MapSelectionSynchronizer MapSelectionSynchronizer { get; } = new MapSelectionSynchronizer();
        public EventSynchronizer EventSynchronizer { get; } = new EventSynchronizer();
        public TreasureRoomRelicSynchronizer TreasureRoomRelicSynchronizer { get; } = new TreasureRoomRelicSynchronizer();
        public ActionQueueSynchronizer ActionQueueSynchronizer { get; } = new ActionQueueSynchronizer();
        public RunState? DebugOnlyGetState() => null;
    }
}

// =============================================================================
// MegaCrit.Sts2.Core.Rewards
// =============================================================================
namespace MegaCrit.Sts2.Core.Rewards
{
    using MegaCrit.Sts2.Core.Entities.Potions;
    using MegaCrit.Sts2.Core.Localization;

    public abstract class Reward
    {
        public LocString Description { get; } = new LocString();
    }

    public class GoldReward : Reward
    {
        public int Amount { get; }
    }

    public class PotionReward : Reward
    {
        public PotionModel? Potion { get; }
    }

    public class RelicReward : Reward { }
    public class CardReward : Reward { }
    public class SpecialCardReward : Reward { }
    public class CardRemovalReward : Reward { }
}

// =============================================================================
// MegaCrit.Sts2.Core.GameActions
// =============================================================================
namespace MegaCrit.Sts2.Core.GameActions
{
    using MegaCrit.Sts2.Core.Entities.Cards;
    using MegaCrit.Sts2.Core.Entities.Creatures;
    using MegaCrit.Sts2.Core.Entities.Players;

    public interface IGameAction { }

    public class PlayCardAction : IGameAction
    {
        public PlayCardAction(CardModel card, Creature? target) { }
    }

    public class EndPlayerTurnAction : IGameAction
    {
        public EndPlayerTurnAction(Player player, int roundNumber) { }
    }

    public class UndoEndPlayerTurnAction : IGameAction
    {
        public UndoEndPlayerTurnAction(Player player, int roundNumber) { }
    }
}

// =============================================================================
// MegaCrit.Sts2.Core.Commands
// =============================================================================
namespace MegaCrit.Sts2.Core.Commands
{
    using MegaCrit.Sts2.Core.Entities.Players;

    public static class PlayerCmd
    {
        public static void EndTurn(Player player, bool canBackOut = false) { }
    }
}

// =============================================================================
// MegaCrit.Sts2.Core.Nodes.GodotExtensions
// =============================================================================
namespace MegaCrit.Sts2.Core.Nodes.GodotExtensions
{
    public class NClickableControl : Godot.Control
    {
        public virtual new bool IsEnabled { get; protected set; } = true;
        public virtual void ForceClick() { }
    }
}

// =============================================================================
// MegaCrit.Sts2.Core.Nodes.CommonUi
// =============================================================================
namespace MegaCrit.Sts2.Core.Nodes.CommonUi
{
    using MegaCrit.Sts2.Core.Nodes.GodotExtensions;

    public class NConfirmButton : NClickableControl { }
    public class NBackButton : NClickableControl { }
    public class NProceedButton : NClickableControl { }
}

// =============================================================================
// MegaCrit.Sts2.Core.Nodes.Cards
// =============================================================================
namespace MegaCrit.Sts2.Core.Nodes.Cards
{
    using MegaCrit.Sts2.Core.Entities.Cards;
    using MegaCrit.Sts2.Core.Nodes.GodotExtensions;

    public class NCardHolder : NClickableControl
    {
        public static new class SignalName
        {
            public static readonly Godot.StringName Pressed = new Godot.StringName("pressed");
        }

        public virtual CardModel? CardModel { get; }
    }

    public class NCardGrid : Godot.Node
    {
        public static new class SignalName
        {
            public static readonly Godot.StringName HolderPressed = new Godot.StringName("holder_pressed");
        }
    }
}

// =============================================================================
// MegaCrit.Sts2.Core.Nodes.Cards.Holders
// =============================================================================
namespace MegaCrit.Sts2.Core.Nodes.Cards.Holders
{
    using MegaCrit.Sts2.Core.Nodes.Cards;

    public class NGridCardHolder : NCardHolder { }
    public class NSelectedHandCardHolder : NCardHolder { }
}

// =============================================================================
// MegaCrit.Sts2.Core.Nodes.Combat
// =============================================================================
namespace MegaCrit.Sts2.Core.Nodes.Combat
{
    using MegaCrit.Sts2.Core.Nodes.Cards;
    using MegaCrit.Sts2.Core.Nodes.Cards.Holders;

    public class NPlayerHand : Godot.Control
    {
        public static NPlayerHand? Instance { get; }

        public enum Mode { Play, SimpleSelect, UpgradeSelect }

        public bool IsInCardSelection { get; }
        public bool InCardPlay { get; }
        public Mode CurrentMode { get; }
        public IList<NCardHolder> ActiveHolders { get; } = new System.Collections.Generic.List<NCardHolder>();
    }

    public class CombatUi : Godot.Node
    {
        public NPlayerHand? Hand { get; }
    }

    public class NCombatRoom : Godot.Node
    {
        public static NCombatRoom? Instance { get; }
        public CombatUi? Ui { get; }
    }
}

// =============================================================================
// MegaCrit.Sts2.Core.Nodes.Events
// =============================================================================
namespace MegaCrit.Sts2.Core.Nodes.Events
{
    using MegaCrit.Sts2.Core.Events;
    using MegaCrit.Sts2.Core.Nodes.GodotExtensions;

    public class NEventOptionButton : NClickableControl
    {
        public EventOption Option { get; } = new EventOption();
    }

    public class NAncientEventLayout : Godot.Node { }

    public class NEventRoom : Godot.Node
    {
        public static NEventRoom? Instance { get; }
    }
}

// =============================================================================
// MegaCrit.Sts2.Core.Nodes.Rewards
// =============================================================================
namespace MegaCrit.Sts2.Core.Nodes.Rewards
{
    using MegaCrit.Sts2.Core.Nodes.GodotExtensions;
    using MegaCrit.Sts2.Core.Rewards;

    public class NRewardButton : NClickableControl
    {
        public Reward? Reward { get; }
    }

    public class NCardRewardAlternativeButton : NClickableControl { }
}

// =============================================================================
// MegaCrit.Sts2.Core.Nodes.Screens.Overlays
// =============================================================================
namespace MegaCrit.Sts2.Core.Nodes.Screens.Overlays
{
    public interface IOverlayScreen { }

    public class NChooseARelicSelection : Godot.Node, IOverlayScreen { }
    public class NRewardsScreen : Godot.Node, IOverlayScreen { }
}

// =============================================================================
// MegaCrit.Sts2.Core.Nodes.Screens.CardSelection
// =============================================================================
namespace MegaCrit.Sts2.Core.Nodes.Screens.CardSelection
{
    using MegaCrit.Sts2.Core.Nodes.Screens.Overlays;

    public class NCardGridSelectionScreen : Godot.Node, IOverlayScreen { }
    public class NDeckTransformSelectScreen : NCardGridSelectionScreen { }
    public class NDeckUpgradeSelectScreen : NCardGridSelectionScreen { }
    public class NDeckCardSelectScreen : NCardGridSelectionScreen { }
    public class NSimpleCardSelectScreen : NCardGridSelectionScreen { }
    public class NChooseACardSelectionScreen : Godot.Node, IOverlayScreen { }
    public class NCardRewardSelectionScreen : Godot.Node, IOverlayScreen { }
}

// =============================================================================
// MegaCrit.Sts2.Core.Nodes.Screens.Map
// =============================================================================
namespace MegaCrit.Sts2.Core.Nodes.Screens.Map
{
    using MegaCrit.Sts2.Core.Map;

    public enum MapPointState { Unreachable, Reachable, Travelable, Current, Visited }

    public class NMapPoint : Godot.Control
    {
        public MapPointState State { get; }
        public MapPoint Point { get; } = new MapPoint();
    }
}

// =============================================================================
// MegaCrit.Sts2.Core.Nodes.Screens
// =============================================================================
namespace MegaCrit.Sts2.Core.Nodes.Screens
{
    using MegaCrit.Sts2.Core.Nodes.Screens.Map;

    public class NMapScreen : Godot.Node
    {
        public static NMapScreen? Instance { get; }
        public bool IsOpen { get; }
        public void OnMapPointSelectedLocally(NMapPoint point) { }
    }

    public class NOverlayStack : Godot.Node
    {
        public static NOverlayStack? Instance { get; }
        public Godot.Node? Peek() => null;
    }
}

// =============================================================================
// MegaCrit.Sts2.Core.Nodes.Relics
// =============================================================================
namespace MegaCrit.Sts2.Core.Nodes.Relics
{
    using MegaCrit.Sts2.Core.Models;
    using MegaCrit.Sts2.Core.Nodes.GodotExtensions;

    public class NRelicDisplay : Godot.Node
    {
        public RelicModel? Model { get; }
    }

    public class NRelicBasicHolder : NClickableControl
    {
        public NRelicDisplay? Relic { get; }
    }
}

// =============================================================================
// MegaCrit.Sts2.Core.Nodes.Screens.TreasureRoomRelic
// =============================================================================
namespace MegaCrit.Sts2.Core.Nodes.Screens.TreasureRoomRelic
{
    using MegaCrit.Sts2.Core.Nodes.CommonUi;
    using MegaCrit.Sts2.Core.Nodes.GodotExtensions;
    using MegaCrit.Sts2.Core.Nodes.Relics;

    public class NTreasureRoomRelicHolder : NClickableControl
    {
        public NRelicDisplay? Relic { get; }
    }

    public class NTreasureRoomRelicCollection : Godot.Control { }

    public class NTreasureRoom : Godot.Node
    {
        public NProceedButton? ProceedButton { get; }
    }
}

// =============================================================================
// MegaCrit.Sts2.Core.Nodes.RestSite
// =============================================================================
namespace MegaCrit.Sts2.Core.Nodes.RestSite
{
    using MegaCrit.Sts2.Core.Entities.RestSite;
    using MegaCrit.Sts2.Core.Nodes.GodotExtensions;

    public class NRestSiteButton : NClickableControl
    {
        public RestSiteOption Option { get; } = new RestSiteOption();
    }
}

// =============================================================================
// MegaCrit.Sts2.Core.Nodes.Rooms
// =============================================================================
namespace MegaCrit.Sts2.Core.Nodes.Rooms
{
    using MegaCrit.Sts2.Core.Entities.Merchant;
    using MegaCrit.Sts2.Core.Nodes.CommonUi;
    using MegaCrit.Sts2.Core.Nodes.GodotExtensions;

    public class NMerchantInventoryUi : Godot.Node
    {
        public bool IsOpen { get; }
    }

    public class NMerchantRoom : Godot.Node
    {
        public static NMerchantRoom? Instance { get; }
        public NMerchantInventoryUi Inventory { get; } = new NMerchantInventoryUi();
        public NProceedButton ProceedButton { get; } = new NProceedButton();
        public void OpenInventory() { }
    }

    public class NRestSiteRoom : Godot.Node
    {
        public static NRestSiteRoom? Instance { get; }
        public NProceedButton ProceedButton { get; } = new NProceedButton();
    }
}
