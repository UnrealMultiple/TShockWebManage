using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using Newtonsoft.Json.Linq;
using Terraria;
using TShockAPI;
using TerrariaManagerAgent.Models;

namespace TerrariaManagerAgent.Services.Handlers
{
    public class FileHandler : HandlerBase
    {
        private static readonly HashSet<string> _editableFileTypes =
            new HashSet<string>(StringComparer.OrdinalIgnoreCase)
            {
                ".json", ".txt", ".log", ".cfg", ".conf", ".ini",
                ".yml", ".yaml", ".xml", ".md", ".cs", ".ps1", ".bat", ".cmd"
            };

        private static readonly Dictionary<string, long> _editSizeLimitByExt =
            new Dictionary<string, long>(StringComparer.OrdinalIgnoreCase)
            {
                [".json"] = 2 * 1024 * 1024,
                [".txt"] = 2 * 1024 * 1024,
                [".log"] = 4 * 1024 * 1024,
                [".cfg"] = 1 * 1024 * 1024,
                [".conf"] = 1 * 1024 * 1024,
                [".ini"] = 1 * 1024 * 1024,
                [".yml"] = 1 * 1024 * 1024,
                [".yaml"] = 1 * 1024 * 1024,
                [".xml"] = 1 * 1024 * 1024,
                [".md"] = 1 * 1024 * 1024,
                [".cs"] = 1 * 1024 * 1024,
                [".ps1"] = 512 * 1024,
                [".bat"] = 512 * 1024,
                [".cmd"] = 512 * 1024,
            };

        private static readonly Dictionary<string, long> _uploadSizeLimitByExt =
            new Dictionary<string, long>(StringComparer.OrdinalIgnoreCase)
            {
                [".dll"] = 64 * 1024 * 1024,
                [".zip"] = 64 * 1024 * 1024,
                [".rar"] = 64 * 1024 * 1024,
                [".7z"] = 64 * 1024 * 1024,
                [".wld"] = 256 * 1024 * 1024,
                [".json"] = 4 * 1024 * 1024,
                [".txt"] = 4 * 1024 * 1024,
                [".log"] = 8 * 1024 * 1024,
                [".cfg"] = 2 * 1024 * 1024,
                [".conf"] = 2 * 1024 * 1024,
                [".ini"] = 2 * 1024 * 1024,
                [".yml"] = 2 * 1024 * 1024,
                [".yaml"] = 2 * 1024 * 1024,
                [".xml"] = 2 * 1024 * 1024,
                [".md"] = 2 * 1024 * 1024,
            };

        public FileHandler(WebSocketService wsService) : base(wsService) { }

        public async Task HandleFileList(PacketEnvelope envelope)
        {
            string serverDir = GetServerDir();
            var rawSave  = TShock.SavePath ?? "tshock";
            var savePath = Path.IsPathRooted(rawSave) ? rawSave : Path.Combine(serverDir, rawSave);

            var tree = BuildDirTree(serverDir, 0, 4);

            // 世界存档（多路径扫描）
            var worldFiles = new List<object>();
            var worldDirs  = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
            {
                serverDir,
                Directory.GetCurrentDirectory()
            };
            if (!string.IsNullOrEmpty(Main.worldPathName))
            {
                var d = Path.GetDirectoryName(Main.worldPathName);
                if (!string.IsNullOrEmpty(d)) worldDirs.Add(d);
            }
            var seenWld = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach (var wdir in worldDirs.Where(Directory.Exists))
            {
                foreach (var f in Directory.GetFiles(wdir, "*.wld"))
                {
                    if (!seenWld.Add(f)) continue;
                    var info = new FileInfo(f);
                    worldFiles.Add(new
                    {
                        name      = info.Name,
                        size      = info.Length,
                        modified  = info.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss"),
                        dir       = info.DirectoryName,
                        full_path = info.FullName
                    });
                }
            }

            // 配置文件
            var configFiles = new List<object>();
            if (Directory.Exists(savePath))
            {
                foreach (var pattern in new[] { "*.json", "*.txt" })
                foreach (var f in Directory.GetFiles(savePath, pattern))
                {
                    var info = new FileInfo(f);
                    configFiles.Add(new { name = info.Name, size = info.Length,
                        modified = info.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss"),
                        dir = info.DirectoryName, full_path = info.FullName });
                }
            }

            // 日志文件（最近 20）
            var logFiles = new List<object>();
            var logsDir  = Path.Combine(savePath, "logs");
            if (Directory.Exists(logsDir))
            {
                foreach (var f in Directory.GetFiles(logsDir)
                    .OrderByDescending(x => new FileInfo(x).LastWriteTime).Take(20))
                {
                    var info = new FileInfo(f);
                    logFiles.Add(new { name = info.Name, size = info.Length,
                        modified = info.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss"),
                        dir = info.DirectoryName, full_path = info.FullName });
                }
            }

            // 插件列表
            var pluginFiles = new List<object>();
            var pluginsDir  = Path.Combine(serverDir, "ServerPlugins");
            if (!Directory.Exists(pluginsDir))
                pluginsDir = Path.Combine(Directory.GetCurrentDirectory(), "ServerPlugins");
            if (Directory.Exists(pluginsDir))
            {
                foreach (var f in Directory.GetFiles(pluginsDir, "*.dll"))
                {
                    var info = new FileInfo(f);
                    pluginFiles.Add(new { name = info.Name, size = info.Length,
                        modified = info.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss"),
                        dir = info.DirectoryName, full_path = info.FullName });
                }
            }

            // 数据库文件
            var dbFiles = new List<object>();
            if (Directory.Exists(savePath))
            {
                foreach (var pattern in new[] { "*.sqlite", "*.db", "*.db3" })
                foreach (var f in Directory.GetFiles(savePath, pattern))
                {
                    var info = new FileInfo(f);
                    dbFiles.Add(new { name = info.Name, size = info.Length,
                        modified = info.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss"),
                        dir = info.DirectoryName, full_path = info.FullName, binary = true });
                }
            }

            var categories = new[]
            {
                new { name = "世界存档", key = "worlds",    files = (object)worldFiles  },
                new { name = "配置文件", key = "configs",   files = (object)configFiles },
                new { name = "日志文件", key = "logs",      files = (object)logFiles    },
                new { name = "插件列表", key = "plugins",   files = (object)pluginFiles },
                new { name = "数据库",   key = "databases", files = (object)dbFiles     },
            };

            AgentLog.Debug("File", "list_completed",
                ("msg_id", envelope.MsgId),
                ("server_dir", serverDir),
                ("worlds", worldFiles.Count),
                ("configs", configFiles.Count),
                ("logs", logFiles.Count),
                ("plugins", pluginFiles.Count),
                ("databases", dbFiles.Count));

            await _wsService.SendAsync(new
            {
                type      = "file_list_resp",
                msg_id    = Guid.NewGuid().ToString("N"),
                timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                payload   = new { ref_id = envelope.MsgId, server_dir = serverDir, tree, categories }
            });
        }

        /// <summary>递归构建目录树（最深 maxDepth 层）</summary>
        private object BuildDirTree(string dirPath, int depth, int maxDepth)
        {
            DirectoryInfo dir;
            try { dir = new DirectoryInfo(dirPath); }
            catch { return null; }
            if (!dir.Exists) return null;

            var children = new List<object>();
            if (depth < maxDepth)
            {
                try
                {
                    foreach (var sub in dir.GetDirectories().OrderBy(d => d.Name))
                    {
                        if (_skipDirNames.Contains(sub.Name)) continue;
                        var child = BuildDirTree(sub.FullName, depth + 1, maxDepth);
                        if (child != null) children.Add(child);
                    }
                }
                catch { }

                try
                {
                    int fc = 0;
                    foreach (var f in dir.GetFiles().OrderBy(f => f.Name))
                    {
                        if (fc++ >= 200) break;
                        children.Add(new
                        {
                            type     = "file",
                            name     = f.Name,
                            path     = f.FullName,
                            size     = f.Length,
                            modified = f.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss")
                        });
                    }
                }
                catch { }
            }

            return new { type = "dir", name = dir.Name, path = dir.FullName, children };
        }

        public async Task HandleFileRead(PacketEnvelope envelope)
        {
            var jobj = JObject.Parse(envelope.Payload?.ToString() ?? "{}");
            var path = jobj["path"]?.ToString() ?? "";
            if (!IsPathSafe(path))
            {
                await SendFileError("file_read_resp", envelope.MsgId, "路径不合法");
                return;
            }
            try
            {
                if (!File.Exists(path)) throw new FileNotFoundException("文件不存在");

                var ext = Path.GetExtension(path) ?? "";
                if (!_editableFileTypes.Contains(ext))
                {
                    await SendFileError("file_read_resp", envelope.MsgId,
                        $"该类型文件不允许在线编辑：{ext}");
                    return;
                }

                var fi = new FileInfo(path);
                var editLimit = GetEditSizeLimit(ext);
                if (fi.Length > editLimit)
                {
                    await SendFileError("file_read_resp", envelope.MsgId,
                        $"文件过大，{ext} 最大允许 {FormatSize(editLimit)} 在线编辑");
                    return;
                }

                // 检测 SQLite 魔数（前 16 字节以 "SQLite format 3" 开头）
                var headerBytes = new byte[16];
                using (var fs = File.OpenRead(path))
                    fs.Read(headerBytes, 0, headerBytes.Length);
                var header = System.Text.Encoding.ASCII.GetString(headerBytes);
                if (header.StartsWith("SQLite format 3"))
                {
                    await _wsService.SendAsync(new {
                        type = "file_read_resp", msg_id = Guid.NewGuid().ToString("N"),
                        timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                        payload = new { ref_id = envelope.MsgId, success = false, binary = true,
                            msg = "SQLite 二进制数据库文件，不支持文本编辑。" }
                    });
                    return;
                }

                var content = File.ReadAllText(path, System.Text.Encoding.UTF8);
                await _wsService.SendAsync(new {
                    type = "file_read_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = true, path, content }
                });
            }
            catch (Exception ex)
            {
                await _wsService.SendAsync(new {
                    type = "file_read_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = false, msg = ex.Message }
                });
            }
        }

        public async Task HandleFileWrite(PacketEnvelope envelope)
        {
            var jobj    = JObject.Parse(envelope.Payload?.ToString() ?? "{}");
            var path    = jobj["path"]?.ToString()    ?? "";
            var content = jobj["content"]?.ToString() ?? "";
            if (!IsPathSafe(path))
            {
                await SendFileError("file_write_resp", envelope.MsgId, "路径不合法");
                return;
            }
            try
            {
                var ext = Path.GetExtension(path) ?? "";
                if (!_editableFileTypes.Contains(ext))
                {
                    await SendFileError("file_write_resp", envelope.MsgId,
                        $"该类型文件不允许在线编辑：{ext}");
                    return;
                }

                var bytes = System.Text.Encoding.UTF8.GetByteCount(content ?? string.Empty);
                var limit = GetEditSizeLimit(ext);
                if (bytes > limit)
                {
                    await SendFileError("file_write_resp", envelope.MsgId,
                        $"内容超过大小限制，{ext} 最大允许 {FormatSize(limit)}");
                    return;
                }

                File.WriteAllText(path, content, System.Text.Encoding.UTF8);
                await _wsService.SendAsync(new {
                    type = "file_write_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = true, path }
                });
            }
            catch (Exception ex)
            {
                await _wsService.SendAsync(new {
                    type = "file_write_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = false, msg = ex.Message }
                });
            }
        }

        public async Task HandleFileCreate(PacketEnvelope envelope)
        {
            var jobj = JObject.Parse(envelope.Payload?.ToString() ?? "{}");
            var path = jobj["path"]?.ToString() ?? "";
            var content = jobj["content"]?.ToString() ?? string.Empty;
            if (!IsPathSafe(path))
            {
                await SendFileError("file_create_resp", envelope.MsgId, "路径不合法");
                return;
            }

            try
            {
                var ext = Path.GetExtension(path) ?? "";
                if (!_editableFileTypes.Contains(ext))
                {
                    await SendFileError("file_create_resp", envelope.MsgId,
                        $"仅允许创建可编辑类型文件：{ext}");
                    return;
                }

                var parent = Path.GetDirectoryName(path);
                if (string.IsNullOrWhiteSpace(parent) || !Directory.Exists(parent))
                {
                    await SendFileError("file_create_resp", envelope.MsgId, "目标目录不存在");
                    return;
                }

                if (File.Exists(path))
                {
                    await SendFileError("file_create_resp", envelope.MsgId, "文件已存在");
                    return;
                }

                var bytes = System.Text.Encoding.UTF8.GetByteCount(content ?? string.Empty);
                var limit = GetEditSizeLimit(ext);
                if (bytes > limit)
                {
                    await SendFileError("file_create_resp", envelope.MsgId,
                        $"内容超过大小限制，{ext} 最大允许 {FormatSize(limit)}");
                    return;
                }

                File.WriteAllText(path, content, System.Text.Encoding.UTF8);
                await _wsService.SendAsync(new
                {
                    type = "file_create_resp",
                    msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = true, path }
                });
            }
            catch (Exception ex)
            {
                await SendFileError("file_create_resp", envelope.MsgId, ex.Message);
            }
        }

        public async Task HandleFileMkdir(PacketEnvelope envelope)
        {
            var jobj = JObject.Parse(envelope.Payload?.ToString() ?? "{}");
            var path = jobj["path"]?.ToString() ?? "";
            if (!IsPathSafe(path))
            {
                await SendFileError("file_mkdir_resp", envelope.MsgId, "路径不合法");
                return;
            }

            try
            {
                if (File.Exists(path))
                {
                    await SendFileError("file_mkdir_resp", envelope.MsgId, "同名文件已存在");
                    return;
                }
                Directory.CreateDirectory(path);
                await _wsService.SendAsync(new
                {
                    type = "file_mkdir_resp",
                    msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = true, path }
                });
            }
            catch (Exception ex)
            {
                await SendFileError("file_mkdir_resp", envelope.MsgId, ex.Message);
            }
        }

        public async Task HandleFileMove(PacketEnvelope envelope)
        {
            var jobj = JObject.Parse(envelope.Payload?.ToString() ?? "{}");
            var srcPath = jobj["src_path"]?.ToString() ?? "";
            var dstPath = jobj["dst_path"]?.ToString() ?? "";
            if (!IsPathSafe(srcPath) || !IsPathSafe(dstPath))
            {
                await SendFileError("file_move_resp", envelope.MsgId, "路径不合法");
                return;
            }

            try
            {
                if (string.Equals(srcPath, dstPath, StringComparison.OrdinalIgnoreCase))
                {
                    await SendFileError("file_move_resp", envelope.MsgId, "源路径与目标路径相同");
                    return;
                }

                if (File.Exists(srcPath))
                {
                    var parent = Path.GetDirectoryName(dstPath);
                    if (string.IsNullOrWhiteSpace(parent) || !Directory.Exists(parent))
                    {
                        await SendFileError("file_move_resp", envelope.MsgId, "目标目录不存在");
                        return;
                    }
                    if (File.Exists(dstPath) || Directory.Exists(dstPath))
                    {
                        await SendFileError("file_move_resp", envelope.MsgId, "目标路径已存在");
                        return;
                    }
                    File.Move(srcPath, dstPath);
                }
                else if (Directory.Exists(srcPath))
                {
                    if (File.Exists(dstPath) || Directory.Exists(dstPath))
                    {
                        await SendFileError("file_move_resp", envelope.MsgId, "目标路径已存在");
                        return;
                    }
                    var parent = Path.GetDirectoryName(dstPath);
                    if (string.IsNullOrWhiteSpace(parent) || !Directory.Exists(parent))
                    {
                        await SendFileError("file_move_resp", envelope.MsgId, "目标目录不存在");
                        return;
                    }
                    Directory.Move(srcPath, dstPath);
                }
                else
                {
                    await SendFileError("file_move_resp", envelope.MsgId, "源路径不存在");
                    return;
                }

                await _wsService.SendAsync(new
                {
                    type = "file_move_resp",
                    msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = true, src_path = srcPath, dst_path = dstPath }
                });
            }
            catch (Exception ex)
            {
                await SendFileError("file_move_resp", envelope.MsgId, ex.Message);
            }
        }

        public async Task HandleFileCopy(PacketEnvelope envelope)
        {
            var jobj = JObject.Parse(envelope.Payload?.ToString() ?? "{}");
            var srcPath = jobj["src_path"]?.ToString() ?? "";
            var dstPath = jobj["dst_path"]?.ToString() ?? "";
            if (!IsPathSafe(srcPath) || !IsPathSafe(dstPath))
            {
                await SendFileError("file_copy_resp", envelope.MsgId, "路径不合法");
                return;
            }

            try
            {
                if (string.Equals(srcPath, dstPath, StringComparison.OrdinalIgnoreCase))
                {
                    await SendFileError("file_copy_resp", envelope.MsgId, "源路径与目标路径相同");
                    return;
                }

                if (!File.Exists(srcPath))
                {
                    await SendFileError("file_copy_resp", envelope.MsgId, "仅支持复制文件");
                    return;
                }

                var parent = Path.GetDirectoryName(dstPath);
                if (string.IsNullOrWhiteSpace(parent) || !Directory.Exists(parent))
                {
                    await SendFileError("file_copy_resp", envelope.MsgId, "目标目录不存在");
                    return;
                }

                if (File.Exists(dstPath) || Directory.Exists(dstPath))
                {
                    await SendFileError("file_copy_resp", envelope.MsgId, "目标路径已存在");
                    return;
                }

                File.Copy(srcPath, dstPath, false);
                await _wsService.SendAsync(new
                {
                    type = "file_copy_resp",
                    msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = true, src_path = srcPath, dst_path = dstPath }
                });
            }
            catch (Exception ex)
            {
                await SendFileError("file_copy_resp", envelope.MsgId, ex.Message);
            }
        }

        public async Task HandleFileUpload(PacketEnvelope envelope)
        {
            var jobj = JObject.Parse(envelope.Payload?.ToString() ?? "{}");
            var path = jobj["path"]?.ToString() ?? "";
            var contentBase64 = jobj["content_base64"]?.ToString() ?? "";
            if (!IsPathSafe(path))
            {
                await SendFileError("file_upload_resp", envelope.MsgId, "路径不合法");
                return;
            }

            try
            {
                var parent = Path.GetDirectoryName(path);
                if (string.IsNullOrWhiteSpace(parent) || !Directory.Exists(parent))
                {
                    await SendFileError("file_upload_resp", envelope.MsgId, "目标目录不存在");
                    return;
                }

                byte[] raw;
                try
                {
                    raw = Convert.FromBase64String(contentBase64);
                }
                catch
                {
                    await SendFileError("file_upload_resp", envelope.MsgId, "上传内容编码无效");
                    return;
                }

                var ext = Path.GetExtension(path) ?? "";
                var uploadLimit = GetUploadSizeLimit(ext);
                if (raw.LongLength > uploadLimit)
                {
                    await SendFileError("file_upload_resp", envelope.MsgId,
                        $"文件超出上传限制，{(string.IsNullOrEmpty(ext) ? "此类型" : ext)} 最大允许 {FormatSize(uploadLimit)}");
                    return;
                }

                File.WriteAllBytes(path, raw);
                await _wsService.SendAsync(new
                {
                    type = "file_upload_resp",
                    msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = true, path, size = raw.LongLength }
                });
            }
            catch (Exception ex)
            {
                await SendFileError("file_upload_resp", envelope.MsgId, ex.Message);
            }
        }

        public async Task HandleFileDelete(PacketEnvelope envelope)
        {
            var jobj = JObject.Parse(envelope.Payload?.ToString() ?? "{}");
            var path = jobj["path"]?.ToString() ?? "";
            if (!IsPathSafe(path))
            {
                await _wsService.SendAsync(new {
                    type = "file_delete_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = false, msg = "路径不合法" }
                });
                return;
            }
            try
            {
                if (!File.Exists(path)) throw new FileNotFoundException("文件不存在");
                File.Delete(path);
                await _wsService.SendAsync(new {
                    type = "file_delete_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = true, path }
                });
            }
            catch (Exception ex)
            {
                await _wsService.SendAsync(new {
                    type = "file_delete_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = false, msg = ex.Message }
                });
            }
        }

        private static long GetEditSizeLimit(string ext)
        {
            return _editSizeLimitByExt.TryGetValue(ext, out var limit) ? limit : 512 * 1024;
        }

        private static long GetUploadSizeLimit(string ext)
        {
            return _uploadSizeLimitByExt.TryGetValue(ext, out var limit) ? limit : 16 * 1024 * 1024;
        }

        private static string FormatSize(long bytes)
        {
            if (bytes < 1024) return $"{bytes} B";
            if (bytes < 1024 * 1024) return $"{bytes / 1024.0:F1} KB";
            return $"{bytes / 1024.0 / 1024.0:F1} MB";
        }

        private async Task SendFileError(string type, string refId, string msg)
        {
            await _wsService.SendAsync(new
            {
                type,
                msg_id = Guid.NewGuid().ToString("N"),
                timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                payload = new { ref_id = refId, success = false, msg }
            });
        }
    }
}
