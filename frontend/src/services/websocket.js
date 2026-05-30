import { useState, useEffect, useCallback, useRef } from 'react';

const WS_URL = 'ws://localhost:8000';

export function useWebSocket() {
  const [isConnected, setIsConnected] = useState(false);
  const [data, setData] = useState(null);
  const wsRef = useRef(null);

  const sendMessage = useCallback((message) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    }
  }, []);

  const sendCommand = useCallback((command) => {
    sendMessage({
      type: 'command',
      command: command
    });
  }, [sendMessage]);

  useEffect(() => {
    let reconnectTimeout;

    const connect = () => {
      console.log('正在连接 WebSocket...');
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;
      window.wsInstance = ws; // 暴露到全局供 App.js 直接使用

      ws.onopen = () => {
        console.log('WebSocket 已连接');
        setIsConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          if (message.type === 'state') {
            setData(message.data);
          }
        } catch (e) {
          console.error('解析消息失败:', e);
        }
      };

      ws.onclose = () => {
        console.log('WebSocket 已断开，5秒后重连...');
        setIsConnected(false);
        window.wsInstance = null;
        reconnectTimeout = setTimeout(connect, 5000);
      };

      ws.onerror = (error) => {
        console.error('WebSocket 错误:', error);
      };
    };

    connect();

    return () => {
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
      window.wsInstance = null;
    };
  }, []);

  return {
    isConnected,
    data,
    sendCommand,
    sendMessage
  };
}
