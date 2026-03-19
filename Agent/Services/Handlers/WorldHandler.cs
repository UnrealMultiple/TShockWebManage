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

namespace TerrariaManagerAgent.Services.Handlers
{
    /// <summary>处理世界/通关进度和地图相关查询。</summary>
    public class WorldHandler : HandlerBase
    {
        public WorldHandler(WebSocketService wsService) : base(wsService) { }

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
            // PNG 文件签名
            ms.Write(new byte[] { 137, 80, 78, 71, 13, 10, 26, 10 });
            // IHDR
            var ihdr = new byte[13];
            ihdr[0] = (byte)(w >> 24); ihdr[1] = (byte)(w >> 16); ihdr[2] = (byte)(w >> 8); ihdr[3] = (byte)w;
            ihdr[4] = (byte)(h >> 24); ihdr[5] = (byte)(h >> 16); ihdr[6] = (byte)(h >> 8); ihdr[7] = (byte)h;
            ihdr[8] = 8; ihdr[9] = 2; // 8-bit RGB truecolor
            WritePngChunk(ms, "IHDR", ihdr);
            // IDAT：每行前插入 filter=0(None)，然后 zlib 压缩
            using var raw = new MemoryStream(h * (1 + w * 3));
            for (int y = 0; y < h; y++)
            {
                raw.WriteByte(0); // filter: None
                raw.Write(rgb, y * w * 3, w * 3);
            }
            using var comp = new MemoryStream();
            using (var zlib = new ZLibStream(comp, CompressionLevel.Fastest, leaveOpen: true))
                raw.WriteTo(zlib);
            WritePngChunk(ms, "IDAT", comp.ToArray());
            // IEND
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
                var progress = new
                {
                    // ── 前期 Boss ──────────────────────────────
                    king_slime      = NPC.downedSlimeKing,
                    eye_of_cthulhu  = NPC.downedBoss1,
                    eow_or_boc      = NPC.downedBoss2,   // 腐化世界:食界虫  猩红世界:克苏鲁大脑
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
                    duke_fishron    = NPC.downedFishron,

                    // ── 终局 ───────────────────────────────────
                    ancient_cultist = NPC.downedAncientCultist,
                    moon_lord       = NPC.downedMoonlord,

                    // ── 世界属性 ───────────────────────────────
                    world_name      = Main.worldName ?? "",
                    world_id        = Main.worldID,
                    is_crimson      = WorldGen.crimson,  // true=猩红, false=腐化
                    is_expert       = Main.expertMode,
                    is_master       = Main.masterMode,
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
