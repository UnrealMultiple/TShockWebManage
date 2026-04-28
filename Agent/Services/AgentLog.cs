using System;
using System.Linq;
using TShockAPI;

namespace TerrariaManagerAgent.Services
{
    public static class AgentLog
    {
        private static volatile bool _debugEnabled;

        public static void SetDebugEnabled(bool enabled)
        {
            _debugEnabled = enabled;
        }

        public static void Info(string scope, string eventName, params (string Key, object? Value)[] fields)
        {
            Write(TShock.Log.Info, scope, eventName, fields);
        }

        public static void Warn(string scope, string eventName, params (string Key, object? Value)[] fields)
        {
            Write(TShock.Log.Warn, scope, eventName, fields);
        }

        public static void Error(string scope, string eventName, params (string Key, object? Value)[] fields)
        {
            Write(TShock.Log.Error, scope, eventName, fields);
        }

        public static void Console(string scope, string eventName, params (string Key, object? Value)[] fields)
        {
            Write(TShock.Log.ConsoleInfo, scope, eventName, fields);
        }

        public static void Audit(string eventName, params (string Key, object? Value)[] fields)
        {
            Console("Audit", eventName, fields);
        }

        public static void Debug(string scope, string eventName, params (string Key, object? Value)[] fields)
        {
            if (!_debugEnabled) return;
            Write(TShock.Log.Info, scope, eventName, fields);
        }

        private static void Write(Action<string> writer, string scope, string eventName, params (string Key, object? Value)[] fields)
        {
            try
            {
                writer(Build(scope, eventName, fields));
            }
            catch (ObjectDisposedException)
            {
            }
            catch
            {
            }
        }

        private static string Build(string scope, string eventName, params (string Key, object? Value)[] fields)
        {
            var prefix = $"[Agent][{Clean(scope)}] event={Clean(eventName)}";
            if (fields == null || fields.Length == 0) return prefix;

            var suffix = string.Join(" | ", fields
                .Where(f => !string.IsNullOrWhiteSpace(f.Key))
                .Select(f => $"{Clean(f.Key)}={FormatValue(f.Value)}"));
            return string.IsNullOrWhiteSpace(suffix) ? prefix : $"{prefix} | {suffix}";
        }

        private static string Clean(string value)
        {
            return (value ?? string.Empty)
                .Replace("\r", " ")
                .Replace("\n", " ")
                .Replace("|", "/")
                .Trim();
        }

        private static string FormatValue(object? value)
        {
            if (value == null) return "-";
            var text = Clean(Convert.ToString(value) ?? string.Empty);
            if (text.Length == 0) return "\"\"";
            return text.Contains(' ') || text.Contains('=') ? $"\"{text.Replace("\"", "\\\"")}\"" : text;
        }
    }
}
