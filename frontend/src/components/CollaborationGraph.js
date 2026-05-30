import React, { useState, useRef, useEffect } from 'react';
import { Users, MessageSquare, ArrowRightLeft, Zap, Activity } from 'lucide-react';
import { clsx } from 'clsx';

// 简单的力导向图模拟
const generateLayout = (agents, negotiations) => {
  // 固定几个点
  const positions = {};
  const centerX = 400;
  const centerY = 250;
  const radius = 150;

  agents.forEach((agent, i) => {
    const angle = (i / agents.length) * 2 * Math.PI - Math.PI / 2;
    positions[agent.id] = {
      x: centerX + radius * Math.cos(angle),
      y: centerY + radius * Math.sin(angle)
    };
  });

  // EOC 放中间
  const eocAgent = agents.find(a => a.role === 'eoc');
  if (eocAgent) {
    positions[eocAgent.id] = { x: centerX, y: centerY };
  }

  return positions;
};

const ROLE_STYLES = {
  eoc: { color: '#facc15', bg: '#854d0e', label: 'EOC' },
  fire: { color: '#ef4444', bg: '#7f1d1d', label: '消防' },
  medical: { color: '#3b82f6', bg: '#1e3a5f', label: '医疗' },
  logistics: { color: '#f97316', bg: '#7c2d12', label: '物流' },
  public_info: { color: '#a855f7', bg: '#581c87', label: '公宣' },
};

export default function CollaborationGraph({ data }) {
  const [hoveredNode, setHoveredNode] = useState(null);
  const positions = generateLayout(data.agents, data.negotiations);

  return (
    <div className="h-full w-full bg-slate-900 flex flex-col">
      <div className="p-4 border-b border-slate-700 bg-slate-800 flex items-center justify-between">
        <h2 className="font-bold text-white flex items-center gap-2">
          <Users className="w-5 h-5 text-indigo-400" />
          协作图谱
        </h2>
        <div className="flex gap-4 text-xs text-slate-400">
          <span className="flex items-center gap-1"><div className="w-2 h-2 bg-blue-500 rounded-full" /> 协商请求</span>
          <span className="flex items-center gap-1"><div className="w-2 h-2 bg-green-500 rounded-full" /> 资源转移</span>
          <span className="flex items-center gap-1"><div className="w-2 h-2 bg-red-500 rounded-full" /> 冲突仲裁</span>
        </div>
      </div>

      <div className="flex-1 relative overflow-hidden">
        <svg className="w-full h-full">
          {/* 连接线条 */}
          {data.negotiations.map((neg) => {
            const fromPos = positions[neg.from];
            const toPos = positions[neg.to];
            if (!fromPos || !toPos) return null;

            const strokeColor = neg.status === 'success' ? '#22c55e' : neg.status === 'failed' ? '#ef4444' : '#6366f1';

            return (
              <g key={neg.id}>
                <line
                  x1={fromPos.x}
                  y1={fromPos.y}
                  x2={toPos.x}
                  y2={toPos.y}
                  stroke={strokeColor}
                  strokeWidth="3"
                  strokeDasharray={neg.status === 'pending' ? "5,5" : "none"}
                  opacity={0.8}
                  className="cursor-pointer"
                />
                {/* 箭头或动画点 */}
                <circle
                  cx={(fromPos.x + toPos.x) / 2}
                  cy={(fromPos.y + toPos.y) / 2}
                  r="5"
                  fill={strokeColor}
                  className="animate-pulse"
                />
              </g>
            );
          })}

          {/* 节点 */}
          {data.agents.map((agent) => {
            const pos = positions[agent.id];
            if (!pos) return null;
            const style = ROLE_STYLES[agent.role] || ROLE_STYLES.eoc;
            const isHovered = hoveredNode === agent.id;

            return (
              <g
                key={agent.id}
                onMouseEnter={() => setHoveredNode(agent.id)}
                onMouseLeave={() => setHoveredNode(null)}
                className="cursor-pointer"
              >
                <circle
                  cx={pos.x}
                  cy={pos.y}
                  r={isHovered ? 45 : 35}
                  fill={style.bg}
                  stroke={style.color}
                  strokeWidth={isHovered ? 4 : 2}
                  className="transition-all duration-200"
                />
                <text
                  x={pos.x}
                  y={pos.y + 5}
                  textAnchor="middle"
                  fill="white"
                  fontSize="16"
                  fontWeight="bold"
                >
                  {style.label}
                </text>
                {isHovered && (
                  <text
                    x={pos.x}
                    y={pos.y + 60}
                    textAnchor="middle"
                    fill="#94a3b8"
                    fontSize="12"
                  >
                    {agent.currentTask}
                  </text>
                )}
              </g>
            );
          })}
        </svg>

        {/* 详情卡片 */}
        {hoveredNode && (
          <div className="absolute bottom-4 left-4 bg-slate-800 border border-slate-700 p-4 rounded-xl shadow-xl w-72">
            {(() => {
              const agent = data.agents.find(a => a.id === hoveredNode);
              if (!agent) return null;
              return (
                <>
                  <div className="flex items-center gap-3 mb-3">
                    <div className="w-10 h-10 rounded-full flex items-center justify-center"
                      style={{ backgroundColor: ROLE_STYLES[agent.role].bg }}>
                      <span className="text-xl">
                        {agent.role === 'fire' && '🚒'}
                        {agent.role === 'medical' && '🚑'}
                        {agent.role === 'logistics' && '🚚'}
                        {agent.role === 'public_info' && '📢'}
                        {agent.role === 'eoc' && '🏢'}
                      </span>
                    </div>
                    <div>
                      <div className="font-bold text-white">{ROLE_STYLES[agent.role].label}</div>
                      <div className="text-xs text-slate-400">{agent.currentTask}</div>
                    </div>
                  </div>
                  <div className="border-t border-slate-700 pt-3">
                    <div className="text-xs font-semibold text-slate-500 mb-2">活跃连接:</div>
                    <div className="flex flex-wrap gap-1">
                      {data.negotiations
                        .filter(n => n.from === hoveredNode || n.to === hoveredNode)
                        .map(n => (
                          <span key={n.id} className={clsx(
                            "px-2 py-0.5 rounded text-xs",
                            n.status === 'success' ? "bg-green-950 text-green-400" :
                              n.status === 'failed' ? "bg-red-950 text-red-400" : "bg-blue-950 text-blue-400"
                          )}>
                            {n.from === hoveredNode ? '→' : '←'} {n.from === hoveredNode ? n.to : n.from}
                          </span>
                        ))}
                    </div>
                  </div>
                </>
              );
            })()}
          </div>
        )}
      </div>
    </div>
  );
}
