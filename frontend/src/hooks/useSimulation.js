import { useState, useEffect, useRef } from 'react';

export function useSimulation() {
  const [isConnected, setIsConnected] = useState(false);
  const [data, setData] = useState(null);
  const wsRef = useRef(null);

  useEffect(() => {
    // 这里连接后端 WebSocket
    // 目前使用模拟数据，所以不需要实际连接
    setIsConnected(true);
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  return {
    isConnected,
    data,
    sendCommand: (cmd) => {
      console.log('Sending command:', cmd);
    }
  };
}
