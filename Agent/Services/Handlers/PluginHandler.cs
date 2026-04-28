using System;
using System.Collections.Generic;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Reflection;
using System.Threading.Tasks;
using Newtonsoft.Json.Linq;
using Terraria;
using TerrariaApi.Server;
using TShockAPI;
using TerrariaManagerAgent.Models;
using TerrariaManagerAgent.Services.ApmCompat;

namespace TerrariaManagerAgent.Services.Handlers
{
    public class PluginHandler : HandlerBase
    {
        private static readonly System.Net.Http.HttpClient _httpClient =
            new System.Net.Http.HttpClient { Timeout = TimeSpan.FromSeconds(30) };

        private static readonly HashSet<string> _updateBlacklist = new(StringComparer.OrdinalIgnoreCase);
        private static bool _blacklistLoaded;

        public PluginHandler(WebSocketService wsService) : base(wsService) { }

        // ── 黑名单管理 ─────────────────────────────────────────────────────────

        private string GetApmConfigPath()
        {
            return Path.Combine(GetServerDir(), "tshock", "AutoPluginManager.json");
        }

        private void EnsureBlacklistLoaded()
        {
            if (_blacklistLoaded) return;
            _blacklistLoaded = true;
            try
            {
                var path = GetApmConfigPath();
                if (!File.Exists(path)) return;
                var jobj = JObject.Parse(File.ReadAllText(path));
                var arr  = jobj["插件排除列表"] as JArray;
                if (arr != null)
                    foreach (var t in arr) _updateBlacklist.Add(t.ToString());
            }
            catch { }
        }

        private void SaveBlacklist()
        {
            try
            {
                var path = GetApmConfigPath();
                JObject jobj;
                if (File.Exists(path))
                    jobj = JObject.Parse(File.ReadAllText(path));
                else
                    jobj = new JObject();

                jobj["插件排除列表"] = new JArray(_updateBlacklist.OrderBy(x => x).ToArray());
                File.WriteAllText(path, jobj.ToString(Newtonsoft.Json.Formatting.Indented));
            }
            catch { }
        }

        // ── 获取插件目录 ───────────────────────────────────────────────────────

        private string GetPluginsDir()
        {
            var serverDir  = GetServerDir();
            var pluginsDir = Path.Combine(serverDir, "ServerPlugins");
            if (!Directory.Exists(pluginsDir))
                pluginsDir = Path.Combine(Directory.GetCurrentDirectory(), "ServerPlugins");
            return pluginsDir;
        }

        private string? GetPluginDocPath(string assemblyName)
        {
            if (string.IsNullOrWhiteSpace(assemblyName)) return null;
            var path = Path.Combine(GetPluginsDir(), assemblyName + ".md");
            return File.Exists(path) ? Path.GetFullPath(path) : null;
        }

        // ── 热重载单个 DLL（公共逻辑，install/update/enable 共用）──────────────

        private async Task HotLoadAssembly(
            string asmName,
            string pluginsDir,
            Dictionary<string, Assembly> loadedAsms,
            Main gameObj,
            List<PluginContainer> pluginList,
            List<string> reloaded,
            List<string> failed)
        {
            try
            {
                // 卸载旧版本（如存在）
                if (loadedAsms.TryGetValue(asmName, out var oldAsm))
                {
                    var toRm = pluginList.Where(p => p.Plugin.GetType().Assembly == oldAsm).ToList();
                    foreach (var op in toRm)
                    {
                        try { op.Plugin.Dispose(); op.DeInitialize(); } catch { }
                        pluginList.Remove(op);
                    }
                    loadedAsms.Remove(asmName);
                }

                var dllPath  = Path.Combine(pluginsDir, asmName + ".dll");
                var pdbPath  = Path.ChangeExtension(dllPath, ".pdb");
                var dllBytes = await File.ReadAllBytesAsync(dllPath);
                var pdbBytes = File.Exists(pdbPath) ? await File.ReadAllBytesAsync(pdbPath) : null;
                var assembly = Assembly.Load(dllBytes, pdbBytes);
                loadedAsms[asmName] = assembly;

                bool found = false;
                foreach (var t in assembly.GetExportedTypes())
                {
                    if (!t.IsSubclassOf(typeof(TerrariaPlugin)) || !t.IsPublic || t.IsAbstract) continue;
                    var apiAttrs = t.GetCustomAttributes(typeof(ApiVersionAttribute), false);
                    if (apiAttrs.Length == 0) continue;
                    if (!ServerApi.IgnoreVersion)
                    {
                        var av = (ApiVersionAttribute)apiAttrs[0];
                        if (av.ApiVersion.Major != ServerApi.ApiVersion.Major ||
                            av.ApiVersion.Minor != ServerApi.ApiVersion.Minor) continue;
                    }
                    if (Activator.CreateInstance(t, gameObj) is TerrariaPlugin pi)
                    {
                        var pc = new PluginContainer(pi);
                        pluginList.Add(pc);
                        pc.Initialize();
                        reloaded.Add($"{asmName} v{pi.Version}");
                        found = true;
                        TShock.Log.ConsoleInfo($"[Agent] 热重载 {asmName} v{pi.Version} 成功");
                    }
                }
                if (!found) reloaded.Add($"{asmName}（依赖库）");
            }
            catch (Exception ex)
            {
                failed.Add($"{asmName}: {ex.Message}");
                TShock.Log.Error($"[Agent] 热重载 {asmName} 失败: {ex.Message}");
            }
        }

        // ── 解压 ZIP 到 fileMap ────────────────────────────────────────────────

        private static async Task<Dictionary<string, byte[]>> ExtractZip(byte[] zipBytes)
        {
            var fileMap = new Dictionary<string, byte[]>(StringComparer.OrdinalIgnoreCase);
            using var ms  = new MemoryStream(zipBytes);
            using var zip = new ZipArchive(ms, ZipArchiveMode.Read);
            foreach (var entry in zip.Entries)
            {
                if (string.IsNullOrEmpty(entry.Name)) continue;
                using var stream = entry.Open();
                using var buf    = new MemoryStream();
                await stream.CopyToAsync(buf);
                fileMap[entry.Name] = buf.ToArray();
            }
            return fileMap;
        }

        // ── 将 fileMap 写入 pluginsDir，返回写入的 DLL 基名列表 ───────────────

        private static async Task<List<string>> WriteFilesToPluginsDir(
            Dictionary<string, byte[]> fileMap, string pluginsDir)
        {
            var written     = new List<string>();
            var fullPlugins = Path.GetFullPath(pluginsDir);
            foreach (var (fname, fdata) in fileMap)
            {
                var dest = Path.GetFullPath(Path.Combine(pluginsDir, fname));
                if (!dest.StartsWith(fullPlugins, StringComparison.OrdinalIgnoreCase)) continue;
                await File.WriteAllBytesAsync(dest, fdata);
                if (fname.EndsWith(".dll", StringComparison.OrdinalIgnoreCase))
                    written.Add(Path.GetFileNameWithoutExtension(fname));
            }
            return written;
        }

        // ── 从 ServerApi 反射获取内部字段 ─────────────────────────────────────

        private static readonly BindingFlags _rflag =
            BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Static;

        private static (Dictionary<string, Assembly> loadedAsms, Main gameObj, List<PluginContainer> pluginList)
            GetServerApiInternals()
        {
            var loadedAsms = typeof(ServerApi).GetField("loadedAssemblies", _rflag)?.GetValue(null) as Dictionary<string, Assembly>;
            var gameObj    = typeof(ServerApi).GetField("game",             _rflag)?.GetValue(null) as Main;
            var pluginList = typeof(ServerApi).GetField("plugins",          _rflag)?.GetValue(null) as List<PluginContainer>;
            return (loadedAsms, gameObj, pluginList);
        }

        // ═══════════════════════════════════════════════════════════════════════
        // 具体指令处理
        // ═══════════════════════════════════════════════════════════════════════

        public async Task HandlePluginCloudList(PacketEnvelope envelope)
        {
            try
            {
                var tshockVer = Uri.EscapeDataString(TShock.VersionNum.ToString());
                var json = await _httpClient.GetStringAsync(
                    $"http://api.terraria.ink:11434/plugin/get_plugin_list?tshock_version={tshockVer}");
                await _wsService.SendAsync(new {
                    type      = "plugin_cloud_list_resp",
                    msg_id    = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload   = new { ref_id = envelope.MsgId, success = true, data = JToken.Parse(json) }
                });
            }
            catch (System.Net.Http.HttpRequestException ex)
            {
                await _wsService.SendAsync(new {
                    type      = "plugin_cloud_list_resp",
                    msg_id    = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload   = new { ref_id = envelope.MsgId, success = false, msg = FormatCloudPluginError(ex) }
                });
            }
            catch (Exception ex)
            {
                await _wsService.SendAsync(new {
                    type      = "plugin_cloud_list_resp",
                    msg_id    = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload   = new { ref_id = envelope.MsgId, success = false, msg = ex.Message }
                });
            }
        }

        private static string FormatCloudPluginError(System.Net.Http.HttpRequestException ex)
        {
            var code = ex.StatusCode.HasValue ? (int)ex.StatusCode.Value : 0;
            if (code == 0)
                code = DetectCloudGatewayStatusCode(ex.Message);
            if (code is 502 or 503 or 504)
                return $"云端插件服务暂不可用，请稍后重试（HTTP {code}）";
            if (code > 0)
                return $"云端插件服务请求失败（HTTP {code}）";
            return "无法连接云端插件服务，请检查网络后重试";
        }

        private static int DetectCloudGatewayStatusCode(string message)
        {
            if (string.IsNullOrWhiteSpace(message)) return 0;
            if (message.Contains("502") || message.Contains("Bad Gateway", StringComparison.OrdinalIgnoreCase)) return 502;
            if (message.Contains("503") || message.Contains("Service Unavailable", StringComparison.OrdinalIgnoreCase)) return 503;
            if (message.Contains("504") || message.Contains("Gateway Timeout", StringComparison.OrdinalIgnoreCase)) return 504;
            return 0;
        }

        public async Task HandlePluginLocalList(PacketEnvelope envelope)
        {
            EnsureBlacklistLoaded();
            var plugins     = new List<object>();
            var runningAsms = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            var pluginsDir  = GetPluginsDir();

            try
            {
                var pluginList = typeof(ServerApi).GetField("plugins", _rflag)?.GetValue(null) as List<PluginContainer>;
                if (pluginList != null)
                {
                    foreach (var pc in pluginList
                        .GroupBy(p => p.Plugin.GetType().Assembly.GetName().Name ?? "")
                        .Select(g => g.First()))
                    {
                        var asmName = pc.Plugin.GetType().Assembly.GetName().Name ?? "";
                        runningAsms.Add(asmName);
                        plugins.Add(new {
                            assembly_name = asmName,
                            name          = pc.Plugin.Name,
                            author        = pc.Plugin.Author,
                            version       = pc.Plugin.Version.ToString(),
                            description   = pc.Plugin.Description,
                            initialized   = pc.Initialized,
                            enabled       = true,
                            blacklisted   = _updateBlacklist.Contains(asmName),
                            md_path       = (object?)GetPluginDocPath(asmName),
                        });
                    }
                }
            }
            catch (Exception ex)
            {
                TShock.Log.Error($"[Agent] plugin_local_list 失败: {ex.Message}");
            }

            // 补充伴生程序集（无 TerrariaPlugin 类的 DLL，如 xx.zh-CN.dll）
            try
            {
                var loadedAsmDict = typeof(ServerApi).GetField("loadedAssemblies", _rflag)?.GetValue(null)
                                     as Dictionary<string, Assembly>;
                if (loadedAsmDict != null && Directory.Exists(pluginsDir))
                {
                    foreach (var kv in loadedAsmDict)
                    {
                        if (string.IsNullOrEmpty(kv.Key) || runningAsms.Contains(kv.Key)) continue;
                        if (!File.Exists(Path.Combine(pluginsDir, kv.Key + ".dll"))) continue;
                        var ver = kv.Value.GetName().Version?.ToString() ?? "";
                        runningAsms.Add(kv.Key);
                        plugins.Add(new {
                            assembly_name = kv.Key,
                            name          = kv.Key,
                            author        = "",
                            version       = ver,
                            description   = "",
                            initialized   = true,
                            enabled       = true,
                            blacklisted   = _updateBlacklist.Contains(kv.Key),
                            md_path       = (object?)GetPluginDocPath(kv.Key),
                        });
                    }
                }
            }
            catch { }

            // 已禁用插件 (.dll.disabled)
            if (Directory.Exists(pluginsDir))
            {
                foreach (var f in Directory.GetFiles(pluginsDir, "*.dll.disabled"))
                {
                    var asmName = Path.GetFileNameWithoutExtension(Path.GetFileNameWithoutExtension(f));
                    if (string.IsNullOrEmpty(asmName) || runningAsms.Contains(asmName)) continue;
                    plugins.Add(new {
                        assembly_name = asmName,
                        name          = asmName,
                        author        = "",
                        version       = "",
                        description   = "",
                        initialized   = false,
                        enabled       = false,
                        blacklisted   = _updateBlacklist.Contains(asmName),
                        md_path       = (object?)GetPluginDocPath(asmName),
                    });
                }
            }

            await _wsService.SendAsync(new {
                type      = "plugin_local_list_resp",
                msg_id    = Guid.NewGuid().ToString("N"),
                timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                payload   = new { ref_id = envelope.MsgId, success = true, plugins }
            });
        }

        public async Task HandlePluginListConfigs(PacketEnvelope envelope)
        {
            var serverDir  = GetServerDir();
            var rawSave    = TShock.SavePath ?? "tshock";
            var savePath   = Path.IsPathRooted(rawSave) ? rawSave : Path.Combine(serverDir, rawSave);
            var pluginsDir = GetPluginsDir();

            var excluded = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
            {
                "config.json", "sscconfig.json", "motd.txt",
                "rules.txt", "whitelist.txt", "tshock.pid", "auth.lck"
            };

            var files = new List<object>();
            var seen  = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

            bool IsConfigLike(string path)
            {
                return path.EndsWith(".json", StringComparison.OrdinalIgnoreCase);
            }

            void AddConfigFile(string path)
            {
                if (!IsConfigLike(path)) return;

                var info = new FileInfo(path);
                if (excluded.Contains(info.Name)) return;
                if (!seen.Add(info.FullName)) return;

                string? mdPath  = null;
                var baseName    = Path.GetFileNameWithoutExtension(info.Name);
                var strippedBase = System.Text.RegularExpressions.Regex.Replace(baseName,
                    @"\.[a-z]{2,3}(-[A-Za-z]{2,4})?$", "",
                    System.Text.RegularExpressions.RegexOptions.IgnoreCase);

                var candidates = new List<string> { baseName };
                if (!string.Equals(strippedBase, baseName, StringComparison.OrdinalIgnoreCase))
                    candidates.Add(strippedBase);

                string? matchedAssembly = null;
                foreach (var c in candidates.Distinct(StringComparer.OrdinalIgnoreCase))
                {
                    if (File.Exists(Path.Combine(pluginsDir, c + ".dll")) ||
                        File.Exists(Path.Combine(pluginsDir, c + ".dll.disabled")))
                    {
                        matchedAssembly = c;
                        break;
                    }
                }

                var exactMd     = Path.Combine(pluginsDir, baseName + ".md");
                if (File.Exists(exactMd))
                {
                    mdPath = exactMd;
                }
                else
                {
                    if (strippedBase != baseName)
                    {
                        var strippedMd = Path.Combine(pluginsDir, strippedBase + ".md");
                        if (File.Exists(strippedMd)) mdPath = strippedMd;
                    }
                }

                var isPluginLibrary = matchedAssembly != null || mdPath != null;

                files.Add(new
                {
                    name      = info.Name,
                    full_path = info.FullName,
                    size      = info.Length,
                    modified  = info.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss"),
                    assembly_name = (object?)matchedAssembly,
                    is_plugin_library = isPluginLibrary,
                    md_path   = (object?)mdPath,
                });
            }

            try
            {
                if (Directory.Exists(savePath))
                {
                    foreach (var f in Directory.GetFiles(savePath, "*.json", SearchOption.TopDirectoryOnly).OrderBy(x => x))
                        AddConfigFile(f);
                }
            }
            catch (Exception ex)
            {
                TShock.Log.Error($"[Agent] plugin_list_configs 扫描失败: {ex.Message}");
            }

            await _wsService.SendAsync(new {
                type      = "plugin_list_configs_resp",
                msg_id    = Guid.NewGuid().ToString("N"),
                timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                payload   = new { ref_id = envelope.MsgId, success = true, files }
            });
        }

        public async Task HandlePluginLocalDocRead(PacketEnvelope envelope)
        {
            var jobj = JObject.Parse(envelope.Payload?.ToString() ?? "{}");
            var path = jobj["path"]?.ToString() ?? "";

            try
            {
                if (string.IsNullOrWhiteSpace(path))
                    throw new InvalidOperationException("未指定文档路径");

                var pluginsDir = Path.GetFullPath(GetPluginsDir());
                var fullPath = Path.GetFullPath(path);
                var pluginsRoot = pluginsDir.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar)
                    + Path.DirectorySeparatorChar;

                if (!fullPath.StartsWith(pluginsRoot, StringComparison.OrdinalIgnoreCase))
                    throw new InvalidOperationException("文档路径不合法");

                if (!string.Equals(Path.GetExtension(fullPath), ".md", StringComparison.OrdinalIgnoreCase))
                    throw new InvalidOperationException("仅支持读取 Markdown 文档");

                if (!File.Exists(fullPath))
                    throw new FileNotFoundException("文档不存在");

                var info = new FileInfo(fullPath);
                if (info.Length > 1024 * 1024)
                    throw new InvalidOperationException("文档过大，无法在线预览");

                var content = await File.ReadAllTextAsync(fullPath, System.Text.Encoding.UTF8);
                await _wsService.SendAsync(new {
                    type      = "plugin_local_doc_read_resp",
                    msg_id    = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload   = new { ref_id = envelope.MsgId, success = true, path = fullPath, content }
                });
            }
            catch (Exception ex)
            {
                await _wsService.SendAsync(new {
                    type      = "plugin_local_doc_read_resp",
                    msg_id    = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload   = new { ref_id = envelope.MsgId, success = false, path, msg = ex.Message }
                });
            }
        }

        public async Task HandlePluginInstall(PacketEnvelope envelope)
        {
            var jobj         = JObject.Parse(envelope.Payload?.ToString() ?? "{}");
            var assemblyName = ApmDependencyResolver.NormalizeAssemblyName(jobj["assembly_name"]?.ToString() ?? "");
            if (string.IsNullOrWhiteSpace(assemblyName))
            {
                await _wsService.SendAsync(new {
                    type = "plugin_install_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = false, msg = "未指定 assembly_name" }
                });
                return;
            }

            var pluginsDir = GetPluginsDir();
            Directory.CreateDirectory(pluginsDir);
            var tshockVer = Uri.EscapeDataString(TShock.VersionNum.ToString());

            try
            {
                var resolver = new ApmDependencyResolver(_httpClient);
                var (dependencyOrder, unresolvedDeps) = await resolver.ResolveDependencyOrderAsync(assemblyName, TShock.VersionNum.ToString());

                var installOrder = dependencyOrder
                    .Append(assemblyName)
                    .Distinct(StringComparer.OrdinalIgnoreCase)
                    .ToList();

                var allWrittenDlls = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
                var installedPackages = new List<string>();
                var skippedDependencies = new List<string>();
                var fallbackInstalledDependencies = new List<string>();
                Dictionary<string, byte[]>? allPluginsMap = null;

                async Task<bool> TryInstallFromAllPluginsAsync(string asmToInstall)
                {
                    try
                    {
                        allPluginsMap ??= await ExtractZip(await _httpClient.GetByteArrayAsync(
                            $"http://api.terraria.ink:11434/plugin/get_all_plugins?tshock_version={tshockVer}"));

                        var dllFile = asmToInstall + ".dll";
                        var pdbFile = asmToInstall + ".pdb";
                        var mdFile = asmToInstall + ".md";

                        var subset = new Dictionary<string, byte[]>(StringComparer.OrdinalIgnoreCase);
                        foreach (var (fname, fdata) in allPluginsMap)
                        {
                            var onlyName = Path.GetFileName(fname);
                            if (string.Equals(onlyName, dllFile, StringComparison.OrdinalIgnoreCase) ||
                                string.Equals(onlyName, pdbFile, StringComparison.OrdinalIgnoreCase) ||
                                string.Equals(onlyName, mdFile, StringComparison.OrdinalIgnoreCase))
                            {
                                subset[onlyName] = fdata;
                            }
                        }

                        if (!subset.ContainsKey(dllFile)) return false;

                        var written = await WriteFilesToPluginsDir(subset, pluginsDir);
                        foreach (var w in written) allWrittenDlls.Add(w);
                        installedPackages.Add(asmToInstall);
                        return true;
                    }
                    catch
                    {
                        return false;
                    }
                }

                foreach (var asmToInstall in installOrder)
                {
                    byte[] zipBytes;
                    try
                    {
                        zipBytes = await _httpClient.GetByteArrayAsync(
                            $"http://api.terraria.ink:11434/plugin/get_plugin_zip?assembly_name={Uri.EscapeDataString(asmToInstall)}&tshock_version={tshockVer}");
                    }
                    catch (System.Net.Http.HttpRequestException hex)
                    {
                        var isRoot = string.Equals(asmToInstall, assemblyName, StringComparison.OrdinalIgnoreCase);
                        if (hex.StatusCode != System.Net.HttpStatusCode.NotFound)
                            throw;

                        // APM 式回退：尝试从 /plugin/get_all_plugins 缓存包中解析并安装。
                        if (await TryInstallFromAllPluginsAsync(asmToInstall))
                        {
                            fallbackInstalledDependencies.Add(asmToInstall);
                            TShock.Log.ConsoleInfo($"[Agent] {asmToInstall} 从 get_all_plugins 回退安装成功");
                            continue;
                        }

                        if (isRoot) throw;

                        skippedDependencies.Add($"{asmToInstall}(404)");
                        TShock.Log.ConsoleInfo($"[Agent] 依赖 {asmToInstall} 下载 404，已跳过");
                        continue;
                    }

                    var fileMap = await ExtractZip(zipBytes);
                    if (fileMap.Count == 0) throw new Exception($"插件 {asmToInstall} 压缩包为空或无法读取");

                    var written = await WriteFilesToPluginsDir(fileMap, pluginsDir);
                    foreach (var w in written) allWrittenDlls.Add(w);
                    installedPackages.Add(asmToInstall);
                }

                var (loadedAsms, gameObj, pluginList) = GetServerApiInternals();
                var hotReloaded = new List<string>();
                var hotFailed   = new List<string>();

                if (loadedAsms != null && gameObj != null && pluginList != null)
                {
                    foreach (var asmName in allWrittenDlls)
                        await HotLoadAssembly(asmName, pluginsDir, loadedAsms, gameObj, pluginList, hotReloaded, hotFailed);
                }

                var hotMsg = hotReloaded.Any() ? $"热重载: {string.Join("、", hotReloaded)}" : "已写入，重启后生效";
                if (hotFailed.Any()) hotMsg += $"；失败: {string.Join("、", hotFailed)}";
                var depMsg = dependencyOrder.Count > 0
                    ? $"；依赖: {string.Join("、", dependencyOrder)}"
                    : "";
                var unresolvedMsg = unresolvedDeps.Count > 0
                    ? $"；未在云端找到的依赖: {string.Join("、", unresolvedDeps)}"
                    : "";
                var skippedMsg = skippedDependencies.Count > 0
                    ? $"；跳过依赖下载: {string.Join("、", skippedDependencies)}"
                    : "";
                var fallbackMsg = fallbackInstalledDependencies.Count > 0
                    ? $"；全量包回退安装: {string.Join("、", fallbackInstalledDependencies)}"
                    : "";

                await _wsService.SendAsync(new {
                    type = "plugin_install_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = true,
                        assembly_name = assemblyName,
                        dependencies = dependencyOrder,
                        downloadable_dependencies = dependencyOrder,
                        unresolved_dependencies = unresolvedDeps,
                        skipped_dependencies = skippedDependencies,
                        fallback_installed_dependencies = fallbackInstalledDependencies,
                        install_order = installOrder,
                        installed_packages = installedPackages,
                        written = allWrittenDlls.ToList(),
                        hot_reloaded = hotReloaded,
                        msg = $"已安装 {assemblyName}{depMsg}{unresolvedMsg}{skippedMsg}{fallbackMsg}。{hotMsg}" }
                });
            }
            catch (Exception ex)
            {
                await _wsService.SendAsync(new {
                    type = "plugin_install_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = false, assembly_name = assemblyName, msg = ex.Message }
                });
            }
        }

        public async Task HandlePluginUninstall(PacketEnvelope envelope)
        {
            var jobj         = JObject.Parse(envelope.Payload?.ToString() ?? "{}");
            var assemblyName = jobj["assembly_name"]?.ToString() ?? "";
            if (string.IsNullOrWhiteSpace(assemblyName))
            {
                await _wsService.SendAsync(new {
                    type = "plugin_uninstall_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = false, msg = "未指定插件名" }
                });
                return;
            }

            var pluginsDir = GetPluginsDir();

            try
            {
                var (loadedAsms, _, pluginList) = GetServerApiInternals();

                bool unloaded = false;
                if (loadedAsms != null && pluginList != null && loadedAsms.TryGetValue(assemblyName, out var oldAsm))
                {
                    var toRm = pluginList.Where(p => p.Plugin.GetType().Assembly == oldAsm).ToList();
                    foreach (var p in toRm)
                    {
                        try { p.Plugin.Dispose(); p.DeInitialize(); } catch { }
                        pluginList.Remove(p);
                    }
                    loadedAsms.Remove(assemblyName);
                    unloaded = true;
                    TShock.Log.ConsoleInfo($"[Agent] 卸载 {assemblyName} 成功");
                }

                var dllPath = Path.Combine(pluginsDir, assemblyName + ".dll");
                var pdbPath = Path.ChangeExtension(dllPath, ".pdb");
                bool deleted = false;
                if (File.Exists(dllPath)) { File.Delete(dllPath); deleted = true; }
                if (File.Exists(pdbPath)) { try { File.Delete(pdbPath); } catch { } }

                var msg = unloaded ? $"{assemblyName} 已热卸载并从磁盘删除" :
                          deleted  ? $"{assemblyName} 文件已删除（程序集仍在内存，重启后完全移除）" :
                                     $"{assemblyName} 在 ServerPlugins/ 中不存在";

                await _wsService.SendAsync(new {
                    type = "plugin_uninstall_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = deleted || unloaded,
                        unloaded, deleted, assembly_name = assemblyName, msg }
                });
            }
            catch (Exception ex)
            {
                await _wsService.SendAsync(new {
                    type = "plugin_uninstall_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = false, assembly_name = assemblyName, msg = ex.Message }
                });
            }
        }

        public async Task HandlePluginCheckUpdates(PacketEnvelope envelope)
        {
            try
            {
                var pluginList = typeof(ServerApi).GetField("plugins", _rflag)?.GetValue(null) as List<PluginContainer>;
                if (pluginList == null)
                {
                    await _wsService.SendAsync(new {
                        type = "plugin_check_updates_resp", msg_id = Guid.NewGuid().ToString("N"),
                        timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                        payload = new { ref_id = envelope.MsgId, success = false, msg = "无法读取插件列表" }
                    });
                    return;
                }

                var localVersions = pluginList
                    .GroupBy(p => p.Plugin.GetType().Assembly.GetName().Name ?? "")
                    .ToDictionary(g => g.Key, g => g.First().Plugin.Version.ToString(), StringComparer.OrdinalIgnoreCase);

                // 补充伴生程序集
                try
                {
                    var pluginsDir    = GetPluginsDir();
                    var loadedAsmDict = typeof(ServerApi).GetField("loadedAssemblies", _rflag)?.GetValue(null)
                                         as Dictionary<string, Assembly>;
                    if (loadedAsmDict != null && Directory.Exists(pluginsDir))
                    {
                        foreach (var kv in loadedAsmDict)
                        {
                            if (string.IsNullOrEmpty(kv.Key) || localVersions.ContainsKey(kv.Key)) continue;
                            if (!File.Exists(Path.Combine(pluginsDir, kv.Key + ".dll"))) continue;
                            localVersions[kv.Key] = kv.Value.GetName().Version?.ToString() ?? "0.0.0.0";
                        }
                    }
                }
                catch { }

                var tshockVer = Uri.EscapeDataString(TShock.VersionNum.ToString());
                var json      = await _httpClient.GetStringAsync(
                    $"http://api.terraria.ink:11434/plugin/get_plugin_list?tshock_version={tshockVer}");
                var token    = JToken.Parse(json);
                var cloudArr = token is JArray ja ? ja :
                               token is JObject jo ? jo["data"] as JArray ?? new JArray() :
                               new JArray();

                var updates = new List<object>();
                foreach (var item in cloudArr)
                {
                    var asmName = item["AssemblyName"]?.ToString() ?? "";
                    if (!localVersions.TryGetValue(asmName, out var localVer)) continue;
                    var cloudVer  = item["Version"]?.ToString()  ?? "";
                    var cloudName = item["Name"]?.ToString()     ?? asmName;
                    bool hasUpdate = System.Version.TryParse(cloudVer, out var cv) && System.Version.TryParse(localVer, out var lv)
                        ? cv > lv
                        : !string.Equals(cloudVer, localVer, StringComparison.OrdinalIgnoreCase);
                    if (hasUpdate)
                        updates.Add(new { assembly_name = asmName, name = cloudName, local_version = localVer, cloud_version = cloudVer });
                }

                await _wsService.SendAsync(new {
                    type = "plugin_check_updates_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = true, updates,
                        msg = updates.Count > 0 ? $"发现 {updates.Count} 个可更新插件" : "所有插件均为最新版" }
                });
            }
            catch (Exception ex)
            {
                await _wsService.SendAsync(new {
                    type = "plugin_check_updates_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = false, msg = ex.Message }
                });
            }
        }

        public async Task HandlePluginUpdate(PacketEnvelope envelope)
        {
            EnsureBlacklistLoaded();
            var jobj         = JObject.Parse(envelope.Payload?.ToString() ?? "{}");
            var assemblyName = jobj["assembly_name"]?.ToString() ?? "";
            var pluginsDir   = GetPluginsDir();

            // 确定要更新的插件列表
            List<string> toUpdate;
            if (!string.IsNullOrWhiteSpace(assemblyName))
            {
                if (_updateBlacklist.Contains(assemblyName))
                {
                    await _wsService.SendAsync(new {
                        type = "plugin_update_resp", msg_id = Guid.NewGuid().ToString("N"),
                        timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                        payload = new { ref_id = envelope.MsgId, success = false, assembly_name = assemblyName,
                            msg = $"{assemblyName} 在更新排除列表中，跳过" }
                    });
                    return;
                }
                toUpdate = new List<string> { assemblyName };
            }
            else
            {
                var pluginList = typeof(ServerApi).GetField("plugins", _rflag)?.GetValue(null) as List<PluginContainer>;
                toUpdate = pluginList == null ? new List<string>() :
                    pluginList.GroupBy(p => p.Plugin.GetType().Assembly.GetName().Name ?? "")
                        .Select(g => g.Key).Where(n => !string.IsNullOrEmpty(n) && !_updateBlacklist.Contains(n)).ToList();

                // 补充伴生程序集
                try
                {
                    var loadedAsmsUpd = typeof(ServerApi).GetField("loadedAssemblies", _rflag)?.GetValue(null)
                                         as Dictionary<string, Assembly>;
                    if (loadedAsmsUpd != null && Directory.Exists(pluginsDir))
                    {
                        foreach (var kv in loadedAsmsUpd)
                        {
                            if (string.IsNullOrEmpty(kv.Key) || _updateBlacklist.Contains(kv.Key)) continue;
                            if (toUpdate.Any(x => string.Equals(x, kv.Key, StringComparison.OrdinalIgnoreCase))) continue;
                            if (File.Exists(Path.Combine(pluginsDir, kv.Key + ".dll"))) toUpdate.Add(kv.Key);
                        }
                    }
                }
                catch { }
            }

            var tshockVer = Uri.EscapeDataString(TShock.VersionNum.ToString());
            var updated   = new List<string>();
            var failed    = new List<string>();

            var (loadedAsms, gameObj, pluginList2) = GetServerApiInternals();

            foreach (var asmToUpdate in toUpdate)
            {
                try
                {
                    var zipBytes = await _httpClient.GetByteArrayAsync(
                        $"http://api.terraria.ink:11434/plugin/get_plugin_zip?assembly_name={Uri.EscapeDataString(asmToUpdate)}&tshock_version={tshockVer}");

                    var fileMap     = await ExtractZip(zipBytes);
                    var writtenDlls = await WriteFilesToPluginsDir(fileMap, pluginsDir);

                    if (loadedAsms != null && gameObj != null && pluginList2 != null)
                    {
                        var reloaded = new List<string>();
                        var hotFail  = new List<string>();
                        foreach (var asmN in writtenDlls)
                            await HotLoadAssembly(asmN, pluginsDir, loadedAsms, gameObj, pluginList2, reloaded, hotFail);
                        failed.AddRange(hotFail);
                    }
                    updated.Add(asmToUpdate);
                }
                catch (Exception ex)
                {
                    failed.Add($"{asmToUpdate}: {ex.Message}");
                    TShock.Log.Error($"[Agent] 更新 {asmToUpdate} 失败: {ex.Message}");
                }
            }

            var msg = updated.Count > 0 ? $"已更新 {updated.Count} 个插件: {string.Join("、", updated)}" : "没有插件被更新";
            if (failed.Any()) msg += $"；失败: {string.Join("、", failed)}";

            await _wsService.SendAsync(new {
                type = "plugin_update_resp", msg_id = Guid.NewGuid().ToString("N"),
                timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                payload = new { ref_id = envelope.MsgId, success = updated.Count > 0 || !failed.Any(), updated, failed, msg }
            });
        }

        public async Task HandlePluginDisable(PacketEnvelope envelope)
        {
            var jobj         = JObject.Parse(envelope.Payload?.ToString() ?? "{}");
            var assemblyName = jobj["assembly_name"]?.ToString() ?? "";
            if (string.IsNullOrWhiteSpace(assemblyName))
            {
                await _wsService.SendAsync(new { type = "plugin_disable_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = false, msg = "未指定插件名" } });
                return;
            }

            var pluginsDir = GetPluginsDir();
            try
            {
                var (loadedAsms, _, pluginList) = GetServerApiInternals();
                bool unloaded = false;
                if (loadedAsms != null && pluginList != null && loadedAsms.TryGetValue(assemblyName, out var oldAsm))
                {
                    foreach (var p in pluginList.Where(x => x.Plugin.GetType().Assembly == oldAsm).ToList())
                    {
                        try { p.Plugin.Dispose(); p.DeInitialize(); } catch { }
                        pluginList.Remove(p);
                    }
                    loadedAsms.Remove(assemblyName);
                    unloaded = true;
                }

                var dllPath = Path.Combine(pluginsDir, assemblyName + ".dll");
                if (File.Exists(dllPath)) File.Move(dllPath, dllPath + ".disabled", true);
                var pdbPath = Path.Combine(pluginsDir, assemblyName + ".pdb");
                if (File.Exists(pdbPath)) try { File.Move(pdbPath, pdbPath + ".disabled", true); } catch { }

                var msg = unloaded ? $"{assemblyName} 已禁用（热卸载，重启时不加载）" : $"{assemblyName} 已标记为禁用（重启时不加载）";
                await _wsService.SendAsync(new { type = "plugin_disable_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = true, assembly_name = assemblyName, msg } });
            }
            catch (Exception ex)
            {
                await _wsService.SendAsync(new { type = "plugin_disable_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = false, assembly_name = assemblyName, msg = ex.Message } });
            }
        }

        public async Task HandlePluginEnable(PacketEnvelope envelope)
        {
            var jobj         = JObject.Parse(envelope.Payload?.ToString() ?? "{}");
            var assemblyName = jobj["assembly_name"]?.ToString() ?? "";
            if (string.IsNullOrWhiteSpace(assemblyName))
            {
                await _wsService.SendAsync(new { type = "plugin_enable_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = false, msg = "未指定插件名" } });
                return;
            }

            var pluginsDir = GetPluginsDir();
            try
            {
                var disabledPath = Path.Combine(pluginsDir, assemblyName + ".dll.disabled");
                if (!File.Exists(disabledPath)) throw new Exception($"未找到禁用的插件文件: {assemblyName}.dll.disabled");

                var dllPath = Path.Combine(pluginsDir, assemblyName + ".dll");
                File.Move(disabledPath, dllPath, true);
                var pdbDisabled = Path.Combine(pluginsDir, assemblyName + ".pdb.disabled");
                if (File.Exists(pdbDisabled))
                    try { File.Move(pdbDisabled, Path.Combine(pluginsDir, assemblyName + ".pdb"), true); } catch { }

                var (loadedAsms, gameObj, pluginList) = GetServerApiInternals();
                string hotMsg = "已重命名，重启后加载";

                if (loadedAsms != null && gameObj != null && pluginList != null)
                {
                    var reloaded = new List<string>();
                    var hotFail  = new List<string>();
                    await HotLoadAssembly(assemblyName, pluginsDir, loadedAsms, gameObj, pluginList, reloaded, hotFail);
                    hotMsg = reloaded.Any() ? $"已热启用 {reloaded[0]}" : "已加载（依赖库），重启后完全生效";
                    if (hotFail.Any()) hotMsg = $"热启用失败: {hotFail[0]}";
                }

                await _wsService.SendAsync(new { type = "plugin_enable_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = true, assembly_name = assemblyName, msg = hotMsg } });
            }
            catch (Exception ex)
            {
                await _wsService.SendAsync(new { type = "plugin_enable_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = false, assembly_name = assemblyName, msg = ex.Message } });
            }
        }

        public async Task HandlePluginBlacklist(PacketEnvelope envelope)
        {
            EnsureBlacklistLoaded();
            var jobj         = JObject.Parse(envelope.Payload?.ToString() ?? "{}");
            var action       = jobj["action"]?.ToString()        ?? "list";
            var assemblyName = jobj["assembly_name"]?.ToString() ?? "";

            switch (action)
            {
                case "add":    if (!string.IsNullOrWhiteSpace(assemblyName)) { _updateBlacklist.Add(assemblyName);    SaveBlacklist(); } break;
                case "remove": if (!string.IsNullOrWhiteSpace(assemblyName)) { _updateBlacklist.Remove(assemblyName); SaveBlacklist(); } break;
            }

            await _wsService.SendAsync(new { type = "plugin_blacklist_resp", msg_id = Guid.NewGuid().ToString("N"),
                timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                payload = new { ref_id = envelope.MsgId, success = true,
                    action, assembly_name = assemblyName, blacklist = _updateBlacklist.OrderBy(x => x).ToList() } });
        }

        public async Task HandleCheckApm(PacketEnvelope envelope)
        {
            var pluginsDir  = GetPluginsDir();
            bool fileExists = File.Exists(Path.Combine(pluginsDir, "AutoPluginManager.dll"));

            bool isLoaded = false;
            try
            {
                isLoaded = ServerApi.Plugins.Any(p =>
                    string.Equals(p.Plugin.GetType().Assembly.GetName().Name,
                        "AutoPluginManager", StringComparison.OrdinalIgnoreCase));
            }
            catch { }

            await _wsService.SendAsync(new {
                type      = "plugin_check_apm_resp",
                msg_id    = Guid.NewGuid().ToString("N"),
                timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                payload   = new { ref_id = envelope.MsgId, success = true,
                    installed = fileExists, loaded = isLoaded }
            });
        }

        public async Task HandleApmInstall(PacketEnvelope envelope)
        {
            var pluginsDir = GetPluginsDir();

            var mirrors = new[]
            {
                "https://ghfast.top/https://github.com/UnrealMultiple/TShockPlugin/releases/download/V1.0.0.0/Plugins.zip",
                "https://gh.llkk.cc/https://github.com/UnrealMultiple/TShockPlugin/releases/download/V1.0.0.0/Plugins.zip",
                "https://github.com/UnrealMultiple/TShockPlugin/releases/download/V1.0.0.0/Plugins.zip",
            };

            byte[]? zipBytes = null;
            foreach (var url in mirrors)
            {
                try { zipBytes = await _httpClient.GetByteArrayAsync(url); break; }
                catch { }
            }

            if (zipBytes == null)
            {
                await _wsService.SendAsync(new {
                    type = "plugin_install_apm_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = false, msg = "所有镜像均无法访问，请检查服务器网络" }
                });
                return;
            }

            try
            {
                Directory.CreateDirectory(pluginsDir);
                var installed   = new List<string>();
                var fullPlugins = Path.GetFullPath(pluginsDir);

                using var ms  = new MemoryStream(zipBytes);
                using var zip = new ZipArchive(ms, ZipArchiveMode.Read);
                foreach (var entry in zip.Entries)
                {
                    if (!entry.FullName.StartsWith("Apm/", StringComparison.OrdinalIgnoreCase)) continue;
                    if (string.IsNullOrEmpty(entry.Name)) continue;

                    var dest     = Path.GetFullPath(Path.Combine(pluginsDir, entry.Name));
                    if (!dest.StartsWith(fullPlugins + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase)
                        && !dest.Equals(fullPlugins, StringComparison.OrdinalIgnoreCase)) continue;

                    using var src = entry.Open();
                    using var dst = new FileStream(dest, FileMode.Create, FileAccess.Write, FileShare.None);
                    await src.CopyToAsync(dst);
                    installed.Add(entry.Name);
                }

                if (installed.Count == 0)
                {
                    await _wsService.SendAsync(new {
                        type = "plugin_install_apm_resp", msg_id = Guid.NewGuid().ToString("N"),
                        timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                        payload = new { ref_id = envelope.MsgId, success = false, msg = "压缩包中未找到 Apm/ 文件夹" }
                    });
                    return;
                }

                bool   hotReloaded  = false;
                string hotReloadMsg = $"已将 {installed.Count} 个文件写入 ServerPlugins/";
                try
                {
                    var (loadedAsms, gameObj, pluginList) = GetServerApiInternals();
                    if (loadedAsms == null || gameObj == null || pluginList == null)
                        throw new Exception("无法访问 TSAPI 内部状态（版本不兼容）");

                    var reloaded = new List<string>();
                    var hotFail  = new List<string>();
                    await HotLoadAssembly("AutoPluginManager", pluginsDir, loadedAsms, gameObj, pluginList, reloaded, hotFail);

                    if (reloaded.Any())
                    {
                        hotReloaded  = true;
                        hotReloadMsg = $"APM {reloaded[0]} 热重载成功，插件管理功能即刻可用，无需重启";
                    }
                    else if (hotFail.Any())
                    {
                        hotReloadMsg = $"已写入 {installed.Count} 个文件，热重载失败（{hotFail[0]}），重启服务器后生效";
                    }
                    else
                    {
                        hotReloadMsg = $"已写入 {installed.Count} 个文件，但热重载未能启动（ApiVersion 可能不匹配），重启服务器后生效";
                    }
                }
                catch (Exception hotEx)
                {
                    hotReloadMsg = $"已写入 {installed.Count} 个文件，热重载失败（{hotEx.Message}），重启服务器后生效";
                    TShock.Log.Error($"[Agent] APM 热重载失败: {hotEx.Message}");
                }

                await _wsService.SendAsync(new {
                    type = "plugin_install_apm_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = true,
                        hot_reloaded = hotReloaded, files = installed, msg = hotReloadMsg }
                });
            }
            catch (Exception ex)
            {
                await _wsService.SendAsync(new {
                    type = "plugin_install_apm_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = false, msg = ex.Message }
                });
            }
        }
    }
}
