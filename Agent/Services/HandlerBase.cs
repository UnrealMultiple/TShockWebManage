using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using TerrariaManagerAgent.Models;

namespace TerrariaManagerAgent.Services
{
    /// <summary>
    /// 所有具体 Handler 的基类，提供共享依赖和工具方法。
    /// </summary>
    public abstract class HandlerBase
    {
        protected readonly WebSocketService _wsService;

        protected static readonly HashSet<string> _skipDirNames =
            new HashSet<string>(StringComparer.OrdinalIgnoreCase)
            { "obj", "bin", ".git", ".vs", "node_modules" };

        protected HandlerBase(WebSocketService wsService)
        {
            _wsService = wsService;
        }

        protected string GetServerDir()
        {
            try
            {
                return Path.GetDirectoryName(
                    Process.GetCurrentProcess().MainModule?.FileName
                ) ?? Directory.GetCurrentDirectory();
            }
            catch { return Directory.GetCurrentDirectory(); }
        }

        /// <summary>路径安全检查：禁止访问服务器目录之外的文件</summary>
        protected bool IsPathSafe(string path)
        {
            if (string.IsNullOrEmpty(path)) return false;
            try
            {
                var full       = Path.GetFullPath(path);
                var serverFull = Path.GetFullPath(GetServerDir());
                return full.StartsWith(serverFull, StringComparison.OrdinalIgnoreCase);
            }
            catch { return false; }
        }
    }
}
