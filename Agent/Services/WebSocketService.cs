using System;
using System.Collections.Generic;
using System.Net.WebSockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Newtonsoft.Json;
using TShockAPI;
using TerrariaManagerAgent.Models;

namespace TerrariaManagerAgent.Services
{
    /// <summary>
    /// 负责 WebSocket 连接的管理与指令分发
    /// </summary>
    public class WebSocketService : IDisposable
    {
        private ClientWebSocket _ws;
        private CancellationTokenSource _cts;
        private readonly string _url;       // 已拼入 agent_key 参数
        private readonly string _endpointDisplay;
        private readonly SemaphoreSlim _sendLock = new SemaphoreSlim(1, 1);
        private bool _isConnecting = false;
        private bool _shouldReconnect = true;

        public event Func<string, Task> OnMessageReceived;

        public WebSocketService(string baseUrl, string agentKey)
        {
            // 将 agent_key 作为查询参数拼入 URL
            _endpointDisplay = baseUrl.TrimEnd('/');
            _url = $"{_endpointDisplay}?agent_key={Uri.EscapeDataString(agentKey)}";
            _cts = new CancellationTokenSource();
        }

        public async Task StartAsync()
        {
            _shouldReconnect = true;
            _ = Task.Run(() => ConnectionLoop());
            await Task.CompletedTask;
        }

        private async Task ConnectionLoop()
        {
            while (_shouldReconnect && !_cts.Token.IsCancellationRequested)
            {
                try
                {
                    await ConnectWithRetry();
                    await ReceiveLoop();

                    if (_shouldReconnect && !_cts.Token.IsCancellationRequested)
                    {
                        SafeLog(() => AgentLog.Console("WebSocket", "connection_lost", ("retry_after_seconds", 5)));
                        await Task.Delay(5000, _cts.Token);
                    }
                }
                catch (OperationCanceledException) { break; }
                catch (ObjectDisposedException) { break; }
                catch (Exception ex)
                {
                    SafeLog(() => AgentLog.Error("WebSocket", "connection_loop_failed", ("error", ex.Message)));
                    try { await Task.Delay(5000, _cts.Token); }
                    catch (OperationCanceledException) { break; }
                }
            }
        }

        private async Task ConnectWithRetry()
        {
            int retry = 0;
            while (!_cts.Token.IsCancellationRequested && retry < 5)
            {
                try
                {
                    if (_isConnecting) return;
                    _isConnecting = true;

                    _ws?.Dispose();
                    _ws = new ClientWebSocket();
                    await _ws.ConnectAsync(new Uri(_url), _cts.Token);
                    SafeLog(() => AgentLog.Info("WebSocket", "connected", ("endpoint", _endpointDisplay)));
                    _isConnecting = false;
                    return;
                }
                catch (Exception ex)
                {
                    retry++;
                    _isConnecting = false;
                    SafeLog(() => AgentLog.Warn("WebSocket", "connect_failed",
                        ("endpoint", _endpointDisplay),
                        ("retry", $"{retry}/5"),
                        ("error", ex.Message)));
                    try { await Task.Delay(5000, _cts.Token); }
                    catch (OperationCanceledException) { return; }
                }
            }
            throw new Exception("无法建立 WebSocket 连接");
        }

        private async Task ReceiveLoop()
        {
            var buffer = new byte[1024 * 16];
            var messageBuilder = new StringBuilder();

            try
            {
                while (_ws?.State == WebSocketState.Open && !_cts.Token.IsCancellationRequested)
                {
                    var result = await _ws.ReceiveAsync(new ArraySegment<byte>(buffer), _cts.Token);
                    if (result.MessageType == WebSocketMessageType.Close) break;

                    messageBuilder.Append(Encoding.UTF8.GetString(buffer, 0, result.Count));
                    if (!result.EndOfMessage) continue;

                    var message = messageBuilder.ToString();
                    messageBuilder.Clear();

                    if (OnMessageReceived != null)
                    {
                        _ = OnMessageReceived.Invoke(message);
                    }
                }
            }
            catch (OperationCanceledException) { /* 正常关闭时取消，不记录 */ }
            catch (ObjectDisposedException) { /* TShock 正在关闭，忽略 */ }
            catch (Exception ex)
            {
                SafeLog(() => AgentLog.Error("WebSocket", "receive_failed", ("error", ex.Message)));
            }
        }

        public async Task SendAsync(object data)
        {
            if (_ws?.State != WebSocketState.Open) return;

            try { await _sendLock.WaitAsync(_cts.Token); }
            catch (OperationCanceledException) { return; }
            catch (ObjectDisposedException) { return; }
            try
            {
                var json = JsonConvert.SerializeObject(data);
                var bytes = Encoding.UTF8.GetBytes(json);
                await _ws.SendAsync(new ArraySegment<byte>(bytes), WebSocketMessageType.Text, true, _cts.Token);
            }
            catch (OperationCanceledException) { /* 关闭中，忽略 */ }
            catch (Exception ex)
            {
                SafeLog(() => AgentLog.Error("WebSocket", "send_failed", ("error", ex.Message)));
            }
            finally
            {
                try { _sendLock.Release(); } catch { /* 已释放 */ }
            }
        }

        /// <summary>通知 WS 服务停止重连（在进程退出前调用，避免 dispose 后再写日志）</summary>
        public void SignalShutdown()
        {
            _shouldReconnect = false;
            try { _cts?.Cancel(); } catch { }
        }

        /// <summary>安全日志写入：忽略 TShock 已释放时的 ObjectDisposedException</summary>
        private static void SafeLog(Action action)
        {
            try { action(); }
            catch (ObjectDisposedException) { }
            catch { }
        }

        public void Dispose()
        {
            _shouldReconnect = false;
            try { _cts?.Cancel(); } catch { }
            try { _ws?.Dispose(); } catch { }
            try { _cts?.Dispose(); } catch { }
            try { _sendLock?.Dispose(); } catch { }
        }
    }
}
