import React from 'react';
import { Users, TrendingDown, TrendingUp, Activity, Package, Clock, Zap } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, Cell } from 'recharts';
import { clsx } from 'clsx';

// 模拟历史数据
const HISTORY_DATA = [
  { name: 'T-10', rescued: 10, casualties: 5 },
  { name: 'T-8', rescued: 15, casualties: 7 },
  { name: 'T-6', rescued: 25, casualties: 10 },
  { name: 'T-4', rescued: 35, casualties: 12 },
  { name: 'T-2', rescued: 42, casualties: 16 },
  { name: 'Now', rescued: 45, casualties: 18 },
];

const RESOURCE_THRESHOLDS = {
  helicopter: 3,
  medkit: 100,
  waterPump: 10,
  foodRation: 400
};

const RESOURCE_MAX = {
  helicopter: 3,
  medkit: 200,
  waterPump: 15,
  foodRation: 500
};

const RESOURCE_LABELS = {
  helicopter: '直升机 (架次)',
  medkit: '医疗箱 (箱)',
  waterPump: '水泵 (台)',
  foodRation: '食物配给 (份)'
};

export default function GlobalDashboard({ data }) {
  const { kpis, resources } = data;

  return (
    <div className="h-full w-full bg-slate-900 p-6 overflow-y-auto custom-scrollbar">
      <div className="max-w-6xl mx-auto space-y-6">
        
        {/* KPI 卡片组 */}
        <div className="grid grid-cols-4 gap-4">
          <div className="bg-slate-800 p-4 rounded-xl border border-slate-700">
            <div className="flex items-center justify-between mb-2">
              <Users className="w-5 h-5 text-emerald-500" />
              <span className="text-xs text-emerald-400 bg-emerald-950/50 px-2 py-0.5 rounded-full">+5</span>
            </div>
            <div className="text-2xl font-bold text-white">{kpis.rescued}</div>
            <div className="text-xs text-slate-400">已救援 / {kpis.trapped} 受困</div>
          </div>

          <div className="bg-slate-800 p-4 rounded-xl border border-slate-700">
            <div className="flex items-center justify-between mb-2">
              <TrendingUp className="w-5 h-5 text-red-500" />
              <span className="text-xs text-red-400 bg-red-950/50 px-2 py-0.5 rounded-full">+2%</span>
            </div>
            <div className="text-2xl font-bold text-white">{kpis.casualtyRate}%</div>
            <div className="text-xs text-slate-400">伤亡率 (累积)</div>
          </div>

          <div className="bg-slate-800 p-4 rounded-xl border border-slate-700">
            <div className="flex items-center justify-between mb-2">
              <Package className="w-5 h-5 text-blue-500" />
              <span className="text-xs text-blue-400 bg-blue-950/50 px-2 py-0.5 rounded-full">稳定</span>
            </div>
            <div className="text-2xl font-bold text-white">{kpis.deliverySuccess}%</div>
            <div className="text-xs text-slate-400">物资送达成功率</div>
          </div>

          <div className="bg-slate-800 p-4 rounded-xl border border-slate-700">
            <div className="flex items-center justify-between mb-2">
              <Clock className="w-5 h-5 text-amber-500" />
              <span className="text-xs text-amber-400 bg-amber-950/50 px-2 py-0.5 rounded-full">-0.1m</span>
            </div>
            <div className="text-2xl font-bold text-white">{kpis.avgResponseTime}m</div>
            <div className="text-xs text-slate-400">平均响应时间</div>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-6">
          {/* 趋势图 */}
          <div className="bg-slate-800 p-5 rounded-xl border border-slate-700">
            <h3 className="text-sm font-bold text-slate-300 mb-4">救援 & 伤亡趋势</h3>
            <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={HISTORY_DATA}>
                  <defs>
                    <linearGradient id="colorRescued" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                    </linearGradient>
                    <linearGradient id="colorCasualties" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                  <XAxis dataKey="name" stroke="#64748b" fontSize={12} tickLine={false} axisLine={false} />
                  <YAxis stroke="#64748b" fontSize={12} tickLine={false} axisLine={false} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }}
                    itemStyle={{ color: '#f1f5f9' }}
                  />
                  <Area type="monotone" dataKey="rescued" stroke="#10b981" fillOpacity={1} fill="url(#colorRescued)" />
                  <Area type="monotone" dataKey="casualties" stroke="#ef4444" fillOpacity={1} fill="url(#colorCasualties)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* 资源状态 */}
          <div className="bg-slate-800 p-5 rounded-xl border border-slate-700">
            <h3 className="text-sm font-bold text-slate-300 mb-4 flex items-center gap-2">
              <Zap className="w-4 h-4" />
              全局资源池
            </h3>
            <div className="space-y-4">
              {Object.entries(resources).map(([key, val]) => {
                const max = RESOURCE_MAX[key] || 100;
                const percent = (val / max) * 100;
                const isLow = val < RESOURCE_THRESHOLDS[key];
                
                return (
                  <div key={key} className="space-y-1">
                    <div className="flex justify-between text-xs">
                      <span className="text-slate-400">{RESOURCE_LABELS[key]}</span>
                      <span className={clsx("font-mono font-bold", isLow ? "text-red-400 animate-pulse" : "text-slate-200")}>
                        {val} / {max}
                      </span>
                    </div>
                    <div className="h-2 bg-slate-900 rounded-full overflow-hidden">
                      <div 
                        className={clsx(
                          "h-full transition-all duration-500",
                          isLow ? "bg-red-500" : percent > 50 ? "bg-emerald-500" : "bg-amber-500"
                        )}
                        style={{ width: `${percent}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* 区域优先级对比 - EOC 视角 */}
        <div className="bg-slate-800 p-5 rounded-xl border border-slate-700">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold text-slate-300">区域优先级 (EOC 决策 vs 实际灾害)</h3>
          </div>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart 
                data={data.worldState.zones.map(z => ({
                  name: z.id,
                  eoc: data.worldState.eocPriorities[z.id] || 0,
                  actual: z.disasterIntensity
                }))}
                margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="name" stroke="#64748b" />
                <YAxis stroke="#64748b" />
                <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155' }} />
                <Bar dataKey="actual" name="实际灾害" fill="#94a3b8" />
                <Bar dataKey="eoc" name="EOC 优先级" fill="#facc15" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
