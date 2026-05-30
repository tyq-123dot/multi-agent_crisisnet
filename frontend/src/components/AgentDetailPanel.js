import React from 'react';
import { X, Brain, Eye, Zap, MessageSquare, Activity } from 'lucide-react';
import { clsx } from 'clsx';

const ROLE_LABELS = {
  eoc: '应急指挥中心',
  fire: '消防救援队',
  medical: '医疗救援队',
  logistics: '物流运输队',
  public_info: '公共信息队'
};

const ROLE_COLORS = {
  eoc: 'text-yellow-500 bg-yellow-500/10',
  fire: 'text-red-500 bg-red-500/10',
  medical: 'text-blue-500 bg-blue-500/10',
  logistics: 'text-orange-500 bg-orange-500/10',
  public_info: 'text-purple-500 bg-purple-500/10'
};

export default function AgentDetailPanel({ agent, onClose }) {
  if (!agent) return null;

  return (
    <div className="border-t border-slate-700 bg-slate-800 flex flex-col max-h-[50%]">
      {/* 头部 */}
      <div className="p-4 border-b border-slate-700 flex items-start justify-between bg-slate-800">
        <div className="flex items-center gap-3">
          <div className={clsx("w-10 h-10 rounded-xl flex items-center justify-center text-xl", ROLE_COLORS[agent.role])}>
            {agent.role === 'fire' && '🚒'}
            {agent.role === 'medical' && '🚑'}
            {agent.role === 'logistics' && '🚚'}
            {agent.role === 'public_info' && '📢'}
            {agent.role === 'eoc' && '🏢'}
          </div>
          <div>
            <h3 className="font-bold text-lg text-white">{ROLE_LABELS[agent.role]}</h3>
            <p className="text-xs text-slate-400 flex items-center gap-1">
              <Activity className="w-3 h-3 text-emerald-400" />
              {agent.currentTask}
            </p>
          </div>
        </div>
        <button onClick={onClose} className="p-1 hover:bg-slate-700 rounded text-slate-400 hover:text-white">
          <X className="w-5 h-5" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-6 custom-scrollbar">
        {/* 资源状态 */}
        {Object.keys(agent.resources).length > 0 && (
          <div className="space-y-2">
            <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-orange-500" />
              资源状态
            </h4>
            <div className="grid grid-cols-2 gap-2">
              {Object.entries(agent.resources).map(([key, val]) => (
                <div key={key} className="bg-slate-900/50 p-2 rounded border border-slate-700">
                  <div className="text-xs text-slate-500">{key}</div>
                  <div className="text-lg font-mono font-bold text-white">{val}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* LLM 思考过程 - 核心展示 */}
        <div className="space-y-3">
          <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-2">
            <Brain className="w-4 h-4 text-indigo-400" />
            LLM 推理过程
          </h4>
          
          {/* 感知摘要 */}
          <div className="bg-slate-900 border border-slate-700 rounded-lg overflow-hidden">
            <div className="bg-slate-800 px-3 py-2 border-b border-slate-700 flex items-center gap-2">
              <Eye className="w-4 h-4 text-blue-400" />
              <span className="text-xs font-semibold text-slate-300">感知摘要 (Observation)</span>
            </div>
            <div className="p-3">
              <p className="text-sm text-slate-400">
                检测到附近灾害强度上升，道路状况变化，周边有受困人员需要救援...
              </p>
            </div>
          </div>

          {/* 决策理由 */}
          <div className="bg-slate-900 border border-slate-700 rounded-lg overflow-hidden">
            <div className="bg-slate-800 px-3 py-2 border-b border-slate-700 flex items-center gap-2">
              <Zap className="w-4 h-4 text-yellow-400" />
              <span className="text-xs font-semibold text-slate-300">决策理由 (Reasoning)</span>
            </div>
            <div className="p-3">
              <p className="text-sm text-slate-300 leading-relaxed">
                {agent.thinking || '正在分析当前局势...'}
              </p>
            </div>
          </div>

          {/* 生成的行动 */}
          <div className="bg-emerald-950/30 border border-emerald-900/50 rounded-lg overflow-hidden">
            <div className="bg-emerald-950/50 px-3 py-2 border-b border-emerald-900/50 flex items-center gap-2">
              <Activity className="w-4 h-4 text-emerald-400" />
              <span className="text-xs font-semibold text-emerald-300">执行行动 (Action)</span>
            </div>
            <div className="p-3 font-mono text-sm text-emerald-300">
              {agent.lastDecision ? JSON.stringify(agent.lastDecision, null, 2) : '等待决策...'}
            </div>
          </div>
        </div>

        {/* 协商历史 */}
        <div className="space-y-2">
          <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-2">
            <MessageSquare className="w-4 h-4 text-pink-400" />
            协商记录
          </h4>
          <div className="space-y-2">
            <div className="bg-slate-900/50 border border-slate-700 p-3 rounded-lg text-sm">
              <div className="flex justify-between mb-1">
                <span className="text-slate-400">与物流队协商</span>
                <span className="text-emerald-400 text-xs">成功</span>
              </div>
              <p className="text-slate-500 text-xs">"请求 10 箱药品..."</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
