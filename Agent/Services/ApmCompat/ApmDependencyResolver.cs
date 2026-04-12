using System;
using System.Collections.Generic;
using System.Linq;
using System.Net.Http;
using System.Threading.Tasks;
using Newtonsoft.Json.Linq;

namespace TerrariaManagerAgent.Services.ApmCompat
{
    /// <summary>
    /// APM 兼容的云端依赖解析器：
    /// 通过插件清单接口递归解析依赖。
    /// </summary>
    internal sealed class ApmDependencyResolver
    {
        private readonly HttpClient _httpClient;
        private readonly string _apiBase;

        public ApmDependencyResolver(HttpClient httpClient, string apiBase = "http://api.terraria.ink:11434")
        {
            _httpClient = httpClient;
            _apiBase = apiBase.TrimEnd('/');
        }

        public static string NormalizeAssemblyName(string raw)
        {
            if (string.IsNullOrWhiteSpace(raw)) return string.Empty;
            var s = raw.Trim();

            var commaIdx = s.IndexOf(',');
            if (commaIdx > 0) s = s.Substring(0, commaIdx).Trim();

            if (s.EndsWith(".dll", StringComparison.OrdinalIgnoreCase))
            {
                var slash = Math.Max(s.LastIndexOf('/'), s.LastIndexOf('\\'));
                if (slash >= 0) s = s.Substring(slash + 1);
                s = s.Substring(0, s.Length - 4);
            }

            return s.Trim();
        }

        public async Task<(List<string> DependencyOrder, List<string> UnresolvedDependencies)> ResolveDependencyOrderAsync(
            string rootAssembly,
            string tshockVersion)
        {
            var root = NormalizeAssemblyName(rootAssembly);
            var visited = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            var visiting = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            var unresolved = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            var order = new List<string>();

            async Task Dfs(string asm)
            {
                if (visited.Contains(asm)) return;
                if (visiting.Contains(asm)) return;
                visiting.Add(asm);

                var (ok, deps) = await TryFetchManifestDependenciesAsync(asm, tshockVersion);
                if (!ok)
                {
                    // 根插件保持严格校验；未解析集合主要用于依赖节点。
                    if (!string.Equals(asm, root, StringComparison.OrdinalIgnoreCase))
                        unresolved.Add(asm);
                }

                foreach (var dep in deps)
                {
                    if (string.IsNullOrWhiteSpace(dep)) continue;
                    await Dfs(dep);
                }

                visiting.Remove(asm);
                visited.Add(asm);
                if (!string.Equals(asm, root, StringComparison.OrdinalIgnoreCase)) order.Add(asm);
            }

            await Dfs(root);
            return (
                order.Distinct(StringComparer.OrdinalIgnoreCase).ToList(),
                unresolved.ToList()
            );
        }

        private async Task<(bool Ok, List<string> Dependencies)> TryFetchManifestDependenciesAsync(
            string assemblyName,
            string tshockVersion)
        {
            var dependencies = new List<string>();
            try
            {
                var url =
                    $"{_apiBase}/plugin/get_plugin_manifest/?assembly_name={Uri.EscapeDataString(assemblyName)}&tshock_version={Uri.EscapeDataString(tshockVersion)}";
                var json = await _httpClient.GetStringAsync(url);
                var token = JToken.Parse(json);

                // 同时兼容直接清单格式和 { data: ... } 包装格式。
                var dataToken = token is JObject obj && obj["data"] != null ? obj["data"]! : token;

                var depToken = dataToken["Dependencies"] ?? dataToken["dependencies"];
                if (depToken is JArray depArr)
                {
                    dependencies = depArr
                        .Select(x => NormalizeAssemblyName(x?.ToString() ?? ""))
                        .Where(x => !string.IsNullOrWhiteSpace(x))
                        .Distinct(StringComparer.OrdinalIgnoreCase)
                        .ToList();
                    return (true, dependencies);
                }

                if (depToken != null && depToken.Type == JTokenType.String)
                {
                    dependencies = depToken.ToString()
                        .Split(new[] { ',', ';' }, StringSplitOptions.RemoveEmptyEntries)
                        .Select(NormalizeAssemblyName)
                        .Where(x => !string.IsNullOrWhiteSpace(x))
                        .Distinct(StringComparer.OrdinalIgnoreCase)
                        .ToList();
                    return (true, dependencies);
                }

                // 清单存在但无依赖项。
                return (true, dependencies);
            }
            catch
            {
                return (false, dependencies);
            }
        }
    }
}
