using System;
using System.Collections.Generic;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using Terraria;
using Terraria.Map;
using TShockAPI;
using TerrariaManagerAgent.Models;
using System.Reflection;

namespace TerrariaManagerAgent.Services.Handlers
{
    /// <summary>处理世界/通关进度和地图相关查询。</summary>
    public class WorldHandler : HandlerBase
    {
        public WorldHandler(WebSocketService wsService) : base(wsService) { }

        private static Type? ResolveDd2EventType()
        {
            // 不要依赖 Type.GetType("..., TerrariaServer")。
            // 改为直接从已加载程序集里解析类型。
            foreach (var asm in AppDomain.CurrentDomain.GetAssemblies())
            {
                var t = asm.GetType("Terraria.GameContent.Events.DD2Event", throwOnError: false, ignoreCase: false);
                if (t != null) return t;
            }
            return null;
        }

        private static bool TryReadStaticBoolField(Type type, string fieldName, out bool value)
        {
            value = false;
            try
            {
                var flags = BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static;
                var field = type.GetField(fieldName, flags);
                if (field == null || field.FieldType != typeof(bool)) return false;
                value = (bool)(field.GetValue(null) ?? false);
                return true;
            }
            catch { return false; }
        }

        private static (bool T1, bool T2, bool T3) ReadDd2Stages()
        {
            var dd2Type = ResolveDd2EventType();
            if (dd2Type == null)
            {
                return (false, false, false);
            }

            // 持久化通关标记（会写入世界文件）。
            _ = TryReadStaticBoolField(dd2Type, "DownedInvasionT1", out var doneT1);
            _ = TryReadStaticBoolField(dd2Type, "DownedInvasionT2", out var doneT2);
            _ = TryReadStaticBoolField(dd2Type, "DownedInvasionT3", out var doneT3);

            // 本次运行期标记（在 StartInvasion 时会重置）。
            _ = TryReadStaticBoolField(dd2Type, "_downedDarkMageT1", out var runT1);
            _ = TryReadStaticBoolField(dd2Type, "_downedOgreT2", out var runT2);
            _ = TryReadStaticBoolField(dd2Type, "_spawnedBetsyT3", out var runT3);

            var t1 = doneT1 || runT1;
            var t2 = doneT2 || runT2;
            var t3 = doneT3 || runT3;
            return (t1, t2, t3);
        }

        // ═══════════════════════════════════════════════════════════
        //  小地图生成
        // ═══════════════════════════════════════════════════════════

        private static bool _mapHelperInited;
        private static readonly object _mapInitLock = new();

        private static void EnsureMapHelperInit()
        {
            if (_mapHelperInited) return;
            lock (_mapInitLock)
            {
                if (_mapHelperInited) return;
                MapHelper.Initialize();
                Main.mapEnabled = true;
                _mapHelperInited = true;
            }
        }

        /// <summary>生成世界小地图（1/4 采样，纯 .NET 编码为 PNG base64）并返回在线玩家位置。</summary>
        public async Task HandleMinimap(PacketEnvelope envelope)
        {
            try
            {
                var (imgBase64, playerList, worldW, worldH) = await Task.Run(() =>
                {
                    int w = Main.maxTilesX;
                    int h = Main.maxTilesY;

                    // 服务端 Main.Map 通常为 null，必须在生成前初始化（BlackEdgeWidth=2）
                    const int MapEdge = 2;
                    MapHelper.Initialize();
                    Main.mapEnabled = true;
                    Main.Map = new WorldMap(w, h) { _tiles = new MapTile[w + MapEdge * 2, h + MapEdge * 2] };

                    // 直接按 1/4 间隔采样 Tile，避免生成全分辨率图再缩放
                    const int scale = 4;
                    int outW = Math.Max(1, w / scale);
                    int outH = Math.Max(1, h / scale);

                    var rgb = new byte[outW * outH * 3];
                    for (int sy = 0; sy < outH; sy++)
                    {
                        for (int sx = 0; sx < outW; sx++)
                        {
                            var tile = MapHelper.CreateMapTile(sx * scale, sy * scale, byte.MaxValue);
                            var col  = MapHelper.GetMapTileXnaColor(tile);
                            int i = (sy * outW + sx) * 3;
                            rgb[i] = col.R; rgb[i + 1] = col.G; rgb[i + 2] = col.B;
                        }
                    }

                    string b64 = Convert.ToBase64String(EncodePng(outW, outH, rgb));

                    var players = TShock.Players
                        .Where(p => p != null && p.Active && p.TPlayer != null && !string.IsNullOrEmpty(p.Name))
                        .Select(p => (object)new
                        {
                            name   = p.Name,
                            tile_x = (int)(p.TPlayer.position.X / 16f),
                            tile_y = (int)(p.TPlayer.position.Y / 16f)
                        })
                        .ToList();

                    return (b64, players, w, h);
                });

                await _wsService.SendAsync(new
                {
                    type      = "minimap_resp",
                    msg_id    = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload   = new
                    {
                        ref_id       = envelope.MsgId,
                        success      = true,
                        img          = imgBase64,
                        players      = playerList,
                        world_width  = worldW,
                        world_height = worldH
                    }
                });
            }
            catch (Exception ex)
            {
                await _wsService.SendAsync(new
                {
                    type      = "minimap_resp",
                    msg_id    = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload   = new { ref_id = envelope.MsgId, success = false, msg = ex.Message }
                });
            }
        }

        /// <summary>轻量级：仅返回在线玩家的 Tile 坐标，不重新生成图片。</summary>
        public async Task HandlePlayerPositions(PacketEnvelope envelope)
        {
            try
            {
                var players = TShock.Players
                    .Where(p => p != null && p.Active && !string.IsNullOrEmpty(p.Name))
                    .Select(p => new
                    {
                        name   = p.Name,
                        tile_x = (int)(p.TPlayer.position.X / 16f),
                        tile_y = (int)(p.TPlayer.position.Y / 16f)
                    })
                    .ToList();

                await _wsService.SendAsync(new
                {
                    type      = "player_positions_resp",
                    msg_id    = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload   = new
                    {
                        ref_id       = envelope.MsgId,
                        success      = true,
                        players,
                        world_width  = Main.maxTilesX,
                        world_height = Main.maxTilesY
                    }
                });
            }
            catch (Exception ex)
            {
                await _wsService.SendAsync(new
                {
                    type      = "player_positions_resp",
                    msg_id    = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload   = new { ref_id = envelope.MsgId, success = false, msg = ex.Message }
                });
            }
        }

        // ═══════════════════════════════════════════════════════════
        //  纯 .NET PNG 编码器（无外部依赖，使用 ZLibStream + CRC32）
        // ═══════════════════════════════════════════════════════════

        private static readonly uint[] _crcTable = BuildCrcTable();

        private static uint[] BuildCrcTable()
        {
            var t = new uint[256];
            for (uint i = 0; i < 256; i++)
            {
                uint c = i;
                for (int k = 0; k < 8; k++) c = (c & 1) != 0 ? 0xedb88320u ^ (c >> 1) : c >> 1;
                t[i] = c;
            }
            return t;
        }

        private static uint Crc32(byte[] a, byte[] b)
        {
            uint c = 0xffffffff;
            foreach (byte x in a) c = _crcTable[(c ^ x) & 0xff] ^ (c >> 8);
            foreach (byte x in b) c = _crcTable[(c ^ x) & 0xff] ^ (c >> 8);
            return c ^ 0xffffffff;
        }

        private static void WritePngChunk(Stream s, string tag, byte[] data)
        {
            var t = Encoding.ASCII.GetBytes(tag);
            s.Write(new byte[] { (byte)(data.Length >> 24), (byte)(data.Length >> 16), (byte)(data.Length >> 8), (byte)data.Length });
            s.Write(t);
            s.Write(data);
            uint crc = Crc32(t, data);
            s.Write(new byte[] { (byte)(crc >> 24), (byte)(crc >> 16), (byte)(crc >> 8), (byte)crc });
        }

        /// <summary>将 RGB 裸数据（行优先，每像素3字节）编码为 PNG 字节数组。</summary>
        private static byte[] EncodePng(int w, int h, byte[] rgb)
        {
            using var ms = new MemoryStream();
            // PNG 文件头签名
            ms.Write(new byte[] { 137, 80, 78, 71, 13, 10, 26, 10 });
            // IHDR 块
            var ihdr = new byte[13];
            ihdr[0] = (byte)(w >> 24); ihdr[1] = (byte)(w >> 16); ihdr[2] = (byte)(w >> 8); ihdr[3] = (byte)w;
            ihdr[4] = (byte)(h >> 24); ihdr[5] = (byte)(h >> 16); ihdr[6] = (byte)(h >> 8); ihdr[7] = (byte)h;
            ihdr[8] = 8; ihdr[9] = 2; // 8-bit RGB truecolor
            WritePngChunk(ms, "IHDR", ihdr);
            // IDAT：每行前插入过滤器=0（无过滤），再进行 zlib 压缩
            using var raw = new MemoryStream(h * (1 + w * 3));
            for (int y = 0; y < h; y++)
            {
                raw.WriteByte(0); // 过滤器：无
                raw.Write(rgb, y * w * 3, w * 3);
            }
            using var comp = new MemoryStream();
            using (var zlib = new ZLibStream(comp, CompressionLevel.Fastest, leaveOpen: true))
                raw.WriteTo(zlib);
            WritePngChunk(ms, "IDAT", comp.ToArray());
            // IEND 结束块
            WritePngChunk(ms, "IEND", Array.Empty<byte>());
            return ms.ToArray();
        }

        // ═══════════════════════════════════════════════════════════
        //  世界进度
        // ═══════════════════════════════════════════════════════════

        public async Task HandleWorldProgress(PacketEnvelope envelope)
        {
            try
            {
                var isCrimson = WorldGen.crimson;

                // 对齐参考实现：后端直接给出有序进度列表（名称 + 完成状态）
                var dd2Read = ReadDd2Stages();
                var dd2T1 = dd2Read.T1;
                var dd2T2 = dd2Read.T2;
                var dd2T3 = dd2Read.T3;
                var dd2Done = dd2T1 || dd2T2 || dd2T3;

                var isJourney = Main.GameMode == 3;
                var isLegendary = Main.masterMode && Main.getGoodWorld;
                var worldDifficulty = isLegendary
                    ? "传奇"
                    : isJourney
                        ? "旅途"
                        : Main.masterMode
                            ? "大师"
                            : Main.expertMode
                                ? "专家"
                                : "普通";

                var progressDefs = new (string Key, string Name, bool Done)[]
                {
                    ("king_slime", "史莱姆王", NPC.downedSlimeKing),
                    ("eye_of_cthulhu", "克苏鲁之眼", NPC.downedBoss1),
                    ("goblins", "哥布林入侵", NPC.downedGoblins),
                    ("eater_of_worlds", "世界吞噬怪", !isCrimson && NPC.downedBoss2),
                    ("brain_of_cthulhu", "克苏鲁之脑", isCrimson && NPC.downedBoss2),
                    ("queen_bee", "蜂王", NPC.downedQueenBee),
                    ("deerclops", "独眼巨鹿", NPC.downedDeerclops),
                    ("skeletron", "骷髅王", NPC.downedBoss3),
                    ("wall_of_flesh", "血肉墙", Main.hardMode),
                    ("frost", "雪人军团", NPC.downedFrost),
                    ("pirates", "海盗入侵", NPC.downedPirates),
                    ("queen_slime", "史莱姆皇后", NPC.downedQueenSlime),
                    ("the_twins", "双子魔眼", NPC.downedMechBoss2),
                    ("the_destroyer", "毁灭者", NPC.downedMechBoss1),
                    ("skeletron_prime", "机械骷髅王", NPC.downedMechBoss3),
                    ("plantera", "世纪之花", NPC.downedPlantBoss),
                    ("halloween_king", "南瓜月", NPC.downedHalloweenKing),
                    ("christmas_ice_queen", "冰霜月", NPC.downedChristmasIceQueen),
                    ("golem", "石巨人", NPC.downedGolemBoss),
                    ("old_ones_army_t1", "撒旦军队T1（黑暗魔法师）", dd2T1),
                    ("old_ones_army_t2", "撒旦军队T2（食人魔）", dd2T2),
                    ("old_ones_army_t3", "撒旦军队T3（双足翼龙）", dd2T3),
                    ("martians", "火星暴乱", NPC.downedMartians),
                    ("duke_fishron", "猪龙鱼公爵", NPC.downedFishron),
                    ("empress_of_light", "光之女皇", NPC.downedEmpressOfLight),
                    ("lunatic_cultist", "拜月教邪教徒", NPC.downedAncientCultist),
                    ("tower_solar", "日耀柱", NPC.downedTowerSolar),
                    ("tower_vortex", "星旋柱", NPC.downedTowerVortex),
                    ("tower_nebula", "星云柱", NPC.downedTowerNebula),
                    ("tower_stardust", "星尘柱", NPC.downedTowerStardust),
                    ("moon_lord", "月亮领主", NPC.downedMoonlord),
                };

                var progressItems = progressDefs
                    .Select(x => (object)new { key = x.Key, name = x.Name, done = x.Done })
                    .ToList();

                var progressCompleted = progressDefs.Count(x => x.Done);
                var progressTotal = progressDefs.Length;

                var progress = new
                {
                    progress_items   = progressItems,
                    progress_done    = progressCompleted,
                    progress_total   = progressTotal,
                    progress_percent = progressTotal > 0
                        ? Math.Round(progressCompleted * 100.0 / progressTotal, 1)
                        : 0,

                    // ── 前期 Boss ──────────────────────────────
                    king_slime      = NPC.downedSlimeKing,
                    eye_of_cthulhu  = NPC.downedBoss1,
                    eow_or_boc      = NPC.downedBoss2,   // 腐化世界:食界虫  猩红世界:克苏鲁大脑
                    evil_boss       = NPC.downedBoss2,
                    skeletron       = NPC.downedBoss3,
                    queen_bee       = NPC.downedQueenBee,
                    deerclops       = NPC.downedDeerclops,

                    // ── 硬模式入口 ─────────────────────────────
                    wall_of_flesh   = Main.hardMode,     // 打倒肉山即进入硬模式
                    is_hardmode     = Main.hardMode,

                    // ── 硬模式 Boss ────────────────────────────
                    queen_slime     = NPC.downedQueenSlime,
                    the_destroyer   = NPC.downedMechBoss1,
                    the_twins       = NPC.downedMechBoss2,
                    skeletron_prime = NPC.downedMechBoss3,
                    any_mech_boss   = NPC.downedMechBossAny,
                    plantera        = NPC.downedPlantBoss,
                    golem           = NPC.downedGolemBoss,
                    empress         = NPC.downedEmpressOfLight,
                    empress_of_light= NPC.downedEmpressOfLight,
                    duke_fishron    = NPC.downedFishron,

                    // ── 终局 ───────────────────────────────────
                    ancient_cultist = NPC.downedAncientCultist,
                    lunatic_cultist = NPC.downedAncientCultist,
                    moon_lord       = NPC.downedMoonlord,

                    // ── 事件/天界柱 ───────────────────────────
                    halloween_king  = NPC.downedHalloweenKing,
                    martians        = NPC.downedMartians,
                    tower_solar     = NPC.downedTowerSolar,
                    tower_vortex    = NPC.downedTowerVortex,
                    tower_nebula    = NPC.downedTowerNebula,
                    tower_stardust  = NPC.downedTowerStardust,
                    goblins         = NPC.downedGoblins,
                    pirates         = NPC.downedPirates,
                    frost           = NPC.downedFrost,
                    christmas_ice_queen = NPC.downedChristmasIceQueen,
                    old_ones_army = dd2Done,
                    old_ones_army_t1 = dd2T1,
                    old_ones_army_t2 = dd2T2,
                    old_ones_army_t3 = dd2T3,

                    // ── 世界属性 ───────────────────────────────
                    world_name      = Main.worldName ?? "",
                    world_id        = Main.worldID,
                    is_crimson      = isCrimson,  // true=猩红，false=腐化
                    is_expert       = Main.expertMode,
                    is_master       = Main.masterMode,
                    is_journey      = isJourney,
                    is_legendary    = isLegendary,
                    world_difficulty = worldDifficulty,
                    world_width     = Main.maxTilesX,
                    world_height    = Main.maxTilesY,
                };

                await _wsService.SendAsync(new
                {
                    type      = "world_progress_resp",
                    msg_id    = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload   = new { ref_id = envelope.MsgId, success = true, progress }
                });
            }
            catch (Exception ex)
            {
                await _wsService.SendAsync(new
                {
                    type      = "world_progress_resp",
                    msg_id    = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload   = new { ref_id = envelope.MsgId, success = false, msg = ex.Message }
                });
            }
        }
    }
}
