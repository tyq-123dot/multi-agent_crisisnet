import React from 'react';
import { Marker, Popup, Tooltip } from 'react-leaflet';
import L from 'leaflet';
import { Truck, Flame, Shield, Megaphone, Star, Activity } from 'lucide-react';

// 自定义图标
const createIcon = (color, emoji) => {
  return L.divIcon({
    className: 'custom-agent-marker',
    html: `<div style="
      width: 36px;
      height: 36px;
      background: ${color};
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 20px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.3);
      border: 3px solid white;
      position: relative;
    ">${emoji}</div>`,
    iconSize: [36, 36],
    iconAnchor: [18, 18],
  });
};

const AGENT_CONFIG = {
  fire: { color: '#dc2626', emoji: '🚒', label: '消防队' },
  medical: { color: '#ffffff', emoji: '🚑', label: '医疗队' },
  warehouse: { color: '#f97316', emoji: '🏭', label: '物资仓库' },
  transport: { color: '#0ea5e9', emoji: '🚚', label: '运输队' },
  police: { color: '#475569', emoji: '🚓', label: '警察局' },
  utility: { color: '#10b981', emoji: '🔧', label: '基础设施' },
  public_info: { color: '#9333ea', emoji: '📢', label: '公宣队' },
  eoc: { color: '#facc15', emoji: '🏢', label: 'EOC' },
};

export default function AgentMarkers({ agents, selectedAgent, onSelectAgent }) {
  return (
    <>
      {agents.map((agent) => {
        const config = AGENT_CONFIG[agent.role] || AGENT_CONFIG.eoc;

        return (
          <Marker
            key={agent.id}
            position={[agent.position.lat, agent.position.lng]}
            icon={createIcon(config.color, config.emoji)}
            eventHandlers={{
              click: () => onSelectAgent(agent.id),
            }}
          >
            <Tooltip direction="top" offset={[0, -10]} opacity={1}>
              <div className="p-2">
                <div className="font-bold text-sm">{config.label}</div>
                <div className="text-xs text-slate-500">{agent.currentTask}</div>
              </div>
            </Tooltip>
            <Popup>
              <div className="p-2 min-w-[200px]">
                <h3 className="font-bold text-lg mb-2">{config.label}</h3>
                <p className="text-sm text-slate-600 mb-2">{agent.currentTask}</p>

                {Object.keys(agent.resources).length > 0 && (
                  <div className="border-t pt-2 mt-2">
                    <div className="text-xs font-semibold text-slate-500 mb-1">资源:</div>
                    <div className="flex flex-wrap gap-2">
                      {Object.entries(agent.resources).map(([key, val]) => (
                        <span key={key} className="bg-slate-100 px-2 py-1 rounded text-xs">
                          {key}: {val}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                <button
                  className="mt-3 w-full bg-blue-500 text-white text-xs py-1.5 rounded hover:bg-blue-600 transition-colors"
                  onClick={() => onSelectAgent(agent.id)}
                >
                  查看详情
                </button>
              </div>
            </Popup>
          </Marker>
        );
      })}
    </>
  );
}
