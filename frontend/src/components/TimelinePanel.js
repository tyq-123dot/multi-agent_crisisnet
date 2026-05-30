import React, { useRef, useEffect } from 'react';
import { MessageSquare, AlertTriangle, Shield, Truck, Activity, Bell } from 'lucide-react';
import { clsx } from 'clsx';

const EVENT_TYPE_CONFIG = {
  eoc: { icon: Shield, color: 'text-yellow-500', bg: 'bg-yellow-500/10' },
  resource: { icon: Truck, color: 'text-orange-500', bg: 'bg-orange-500/10' },
  negotiation: { icon: Activity, color: 'text-blue-500', bg: 'bg-blue-500/10' },
  public: { icon: Bell, color: 'text-purple-500', bg: 'bg-purple-500/10' },
  collision: { icon: AlertTriangle, color: 'text-red-500', bg: 'bg-red-500/10' },
};

export default function TimelinePanel({ events, currentTick, className }) {
  const scrollRef = useRef(null);

  // 自动滚动到最新事件
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events]);

  return (
    <div className={clsx("flex flex-col bg-slate-800 border-l border-slate-700", className)}>
      <div className="p-4 border-b border-slate-700 flex items-center justify-between bg-slate-800/50">
        <h2 className="font-bold text-slate-200 flex items-center gap-2">
          <MessageSquare className="w-5 h-5 text-blue-400" />
          实时事件流
        </h2>
        <div className="flex gap-2">
          {Object.keys(EVENT_TYPE_CONFIG).map(type => (
            <button key={type} className="p-1 hover:bg-slate-700 rounded text-xs opacity-60 hover:opacity-100">
              {type[0].toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar"
      >
        {events.map((event) => {
          const config = EVENT_TYPE_CONFIG[event.type] || EVENT_TYPE_CONFIG.eoc;
          const Icon = config.icon;
          
          return (
            <div 
              key={event.id} 
              className={clsx(
                "flex gap-3 p-3 rounded-lg border transition-all duration-200",
                event.tick === currentTick - 1 
                  ? "bg-slate-700/50 border-slate-500 shadow-lg scale-[1.02]" 
                  : "bg-slate-800/50 border-slate-700 hover:bg-slate-700/30"
              )}
            >
              <div className={clsx("w-8 h-8 rounded-full flex items-center justify-center shrink-0", config.bg)}>
                <Icon className={clsx("w-4 h-4", config.color)} />
              </div>
              
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-0.5">
                  <span className="text-xs font-mono text-slate-400">[{event.time}]</span>
                  <span className="text-[10px] uppercase tracking-wider text-slate-500">Tick {event.tick}</span>
                </div>
                <p className="text-sm text-slate-200">{event.message}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
