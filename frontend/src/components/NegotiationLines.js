import React from 'react';
import { Polyline, Tooltip } from 'react-leaflet';

export default function NegotiationLines({ negotiations, agents }) {
  return (
    <>
      {negotiations.map((neg) => {
        const fromAgent = agents.find(a => a.id === neg.from);
        const toAgent = agents.find(a => a.id === neg.to);
        
        if (!fromAgent || !toAgent) return null;
        
        const getColor = () => {
          switch (neg.status) {
            case 'success': return '#22c55e';
            case 'failed': return '#ef4444';
            case 'pending': return '#f59e0b';
            default: return '#6366f1';
          }
        };

        return (
          <Polyline
            key={neg.id}
            positions={[
              [fromAgent.position.lat, fromAgent.position.lng],
              [toAgent.position.lat, toAgent.position.lng]
            ]}
            pathOptions={{
              color: getColor(),
              weight: 3,
              opacity: 0.8,
              dashArray: neg.status === 'pending' ? '5, 10' : null,
              className: neg.status === 'pending' ? 'animate-pulse' : ''
            }}
          >
            <Tooltip>
              <div className="p-2">
                <div className="font-semibold">
                  {neg.status === 'success' ? '✅ 协商成功' : 
                   neg.status === 'failed' ? '❌ 协商失败' : '⏳ 协商中...'}
                </div>
                <div className="text-xs text-slate-500 mt-1">
                  {fromAgent.id} ↔ {toAgent.id}
                </div>
                <div className="text-xs text-slate-400">
                  轮次: {neg.rounds}
                </div>
              </div>
            </Tooltip>
          </Polyline>
        );
      })}
    </>
  );
}
