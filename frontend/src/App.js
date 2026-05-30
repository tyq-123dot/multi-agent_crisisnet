import React, { useState, useEffect, useCallback, useRef } from 'react';
import { MapContainer, TileLayer } from 'react-leaflet';
import { Play, Pause, FastForward, LayoutDashboard, AlertTriangle, Shield, MapPin, Users, MessageSquare } from 'lucide-react';
import { clsx } from 'clsx';

import DisasterLayer from './components/DisasterLayer';
import AgentMarkers from './components/AgentMarkers';
import InfrastructureLayer from './components/InfrastructureLayer';
import NegotiationLines from './components/NegotiationLines';
import TimelinePanel from './components/TimelinePanel';
import AgentDetailPanel from './components/AgentDetailPanel';
import GlobalDashboard from './components/GlobalDashboard';
import CollaborationGraph from './components/CollaborationGraph';
import CommanderPanel from './components/CommanderPanel';
import { useWebSocket } from './services/websocket';

// 生成模拟数据（在 WebSocket 未连接时使用）
const generateMockData = (tick) => ({
  tick,
  worldState: {
    zones: {
      zone_01: { disasterIntensity: 0.1, trapped: 2, casualties: 1, roadAvailable: true },
      zone_02: { disasterIntensity: 0.3, trapped: 5, casualties: 3, roadAvailable: true },
      zone_03: { disasterIntensity: 0.6, trapped: 12, casualties: 8, roadAvailable: false },
      zone_04: { disasterIntensity: 0.9, trapped: 25, casualties: 15, roadAvailable: false },
      zone_05: { disasterIntensity: 0.7, trapped: 18, casualties: 12, roadAvailable: true },
      zone_06: { disasterIntensity: 0.2, trapped: 3, casualties: 1, roadAvailable: true },
      zone_07: { disasterIntensity: 0.0, trapped: 0, casualties: 0, roadAvailable: true },
      zone_08: { disasterIntensity: 0.1, trapped: 1, casualties: 0, roadAvailable: true },
      zone_09: { disasterIntensity: 0.0, trapped: 0, casualties: 0, roadAvailable: true },
    },
    eocPriorities: {},
    infrastructureStatus: {
      power: 'online',
      water: 'online',
      gas: 'online'
    }
  },
  agents: [
    {
      id: 'eoc',
      role: 'eoc',
      position: { lat: 39.9042, lng: 116.4074 },
      currentTask: '分析态势，提供建议',
      resources: {},
      lastDecision: {},
      thinking: '正在分析当前灾害分布...'
    },
    {
      id: 'fire_1',
      role: 'fire',
      position: { lat: 39.9082, lng: 116.4124 },
      currentTask: '前往 zone_04 灭火',
      resources: { water: 80, pumps: 2 },
      lastDecision: { action: 'move_to', target: 'zone_04', reason: 'zone_04 火灾严重' },
      thinking: '检测到 zone_04 灾害严重，决定前往救援...'
    },
    {
      id: 'medical_1',
      role: 'medical',
      position: { lat: 39.9012, lng: 116.4024 },
      currentTask: '在 zone_03 治疗伤员',
      resources: { medkits: 45, ambulances: 3 },
      lastDecision: { action: 'treat', reason: 'zone_03 有大量伤员' },
      thinking: '当前有大量伤员，需要药品...'
    },
    {
      id: 'warehouse_1',
      role: 'warehouse',
      position: { lat: 39.9102, lng: 116.4004 },
      currentTask: '管理物资库存',
      resources: { food: 500, medkits: 200, water: 300 },
      lastDecision: { action: 'manage_warehouse', inventory: 'check' },
      thinking: '盘点库存中...'
    },
    {
      id: 'transport_1',
      role: 'transport',
      position: { lat: 39.9062, lng: 116.3994 },
      currentTask: '待命',
      resources: { trucks: 5, drivers: 5 },
      lastDecision: { action: 'wait' },
      thinking: '等待运输任务'
    },
    {
      id: 'police_1',
      role: 'police',
      position: { lat: 39.9002, lng: 116.4094 },
      currentTask: '巡逻与交通管制',
      resources: { officers: 10, vehicles: 4 },
      lastDecision: { action: 'patrol' },
      thinking: '监控道路状况'
    },
    {
      id: 'utility_1',
      role: 'utility',
      position: { lat: 39.9052, lng: 116.4044 },
      currentTask: '巡检基础设施',
      resources: { repair_teams: 3, equipment: 'full' },
      lastDecision: { action: 'inspect' },
      thinking: '检查水电煤气状况'
    },
    {
      id: 'public_info',
      role: 'public_info',
      position: { lat: 39.9032, lng: 116.4104 },
      currentTask: '监控并发布公告',
      resources: {},
      lastDecision: { action: 'monitor' },
      thinking: '分析社交媒体信息...'
    }
  ],
  events: [
    { id: 1, time: '12:30:00', type: 'eoc', message: 'EOC 提供决策建议', tick: tick - 5 },
    { id: 2, time: '12:31:00', type: 'resource', message: '消防队报告：剩余水量 75%', tick: tick - 4 },
    { id: 3, time: '12:32:00', type: 'negotiation', message: '医疗 ↔ 仓库：协商物资', tick: tick - 3 },
    { id: 4, time: '12:33:00', type: 'public', message: '公宣队发布预警', tick: tick - 2 },
  ],
  negotiations: [],
  escalatedConflicts: [],
  pendingActions: [],
  suggestions: {
    pending: [],
    recent: []
  },
  kpis: {
    rescued: 45,
    trapped: 66,
    casualtyRate: 18,
    deliverySuccess: 92,
    avgResponseTime: 4.2
  },
  resources: {
    helicopter: 2,
    medkit: 125,
    waterPump: 8,
    food: 350
  }
});

function App() {
  const [activeTab, setActiveTab] = useState('map');
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [localData, setLocalData] = useState(null);
  const [localTick, setLocalTick] = useState(100);
  const [showCommander, setShowCommander] = useState(false);
  
  // 使用 WebSocket 连接
  const { isConnected, data: wsData, sendCommand } = useWebSocket();
  
  // 如果 WebSocket 没有数据，使用本地模拟数据
  const data = localData || wsData || generateMockData(localTick);
  const tick = data?.tick || localTick;
  const totalTicks = 500;
  
  // 本地模拟更新（当没有 WebSocket 时使用）
  useEffect(() => {
    if (!wsData && isPlaying) {
      const interval = setInterval(() => {
        setLocalTick(t => t + 1);
      }, 1000 / speed);
      return () => clearInterval(interval);
    }
  }, [isPlaying, speed, wsData]);
  
  useEffect(() => {
    if (!wsData) {
      setLocalData(generateMockData(localTick));
    }
  }, [localTick, wsData]);
  
  // 处理播放/暂停
  const handlePlayPause = () => {
    const newState = !isPlaying;
    setIsPlaying(newState);
    if (isConnected) {
      sendCommand(newState ? 'play' : 'pause');
    }
  };
  
  // 处理人类决策
  const handleHumanDecision = (cardId, decision, feedback = null) => {
    if (isConnected && window.wsInstance) {
      try {
        window.wsInstance.send(JSON.stringify({
          type: 'human_decision',
          card_id: cardId,
          decision: decision,
          feedback: feedback
        }));
      } catch (e) {
        console.error('Failed to send human decision:', e);
      }
    } else {
      console.log('Human decision simulated:', { cardId, decision, feedback });
    }
  };
  
  // 处理取消动作
  const handleCancelAction = (actionId, reason = '用户取消') => {
    if (isConnected && window.wsInstance) {
      try {
        window.wsInstance.send(JSON.stringify({
          type: 'cancel_action',
          action_id: actionId,
          reason: reason
        }));
      } catch (e) {
        console.error('Failed to cancel action:', e);
      }
    } else {
      console.log('Cancel action simulated:', { actionId, reason });
    }
  };
  
  // 处理修改动作
  const handleModifyAction = (actionId, newPayload, reason = '用户修改') => {
    if (isConnected && window.wsInstance) {
      try {
        window.wsInstance.send(JSON.stringify({
          type: 'modify_action',
          action_id: actionId,
          new_payload: newPayload,
          reason: reason
        }));
      } catch (e) {
        console.error('Failed to modify action:', e);
      }
    } else {
      console.log('Modify action simulated:', { actionId, newPayload, reason });
    }
  };
  
  // 处理解决冲突
  const handleResolveConflict = (sessionId, resolution) => {
    if (isConnected && window.wsInstance) {
      try {
        window.wsInstance.send(JSON.stringify({
          type: 'resolve_conflict',
          session_id: sessionId,
          resolution: resolution
        }));
      } catch (e) {
        console.error('Failed to resolve conflict:', e);
      }
    } else {
      console.log('Resolve conflict simulated:', { sessionId, resolution });
    }
  };
  
  return (
    <div className="h-screen w-full bg-slate-900 text-slate-100 flex flex-col overflow-hidden">
      {/* 顶部导航栏 */}
      <header className="h-14 bg-slate-800 border-b border-slate-700 flex items-center px-6 justify-between shrink-0 z-50">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-red-600 rounded-lg flex items-center justify-center">
            <AlertTriangle className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="font-bold text-lg tracking-tight">CrisisNet</h1>
            <p className="text-xs text-slate-400 flex items-center gap-2">
              {isConnected ? (
                <>
                  <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                  已连接后端
                </>
              ) : (
                <>
                  <span className="w-2 h-2 bg-amber-500 rounded-full" />
                  本地模拟模式
                </>
              )}
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-6">
          {/* 主标签页 */}
          <div className="flex bg-slate-900/50 p-1 rounded-lg">
            {[ 
              { id: 'map', icon: MapPin, label: '地图' },
              { id: 'dashboard', icon: LayoutDashboard, label: '仪表盘' },
              { id: 'collaboration', icon: Users, label: '协作' }
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={clsx(
                  "flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors",
                  activeTab === tab.id 
                    ? "bg-slate-700 text-white shadow-sm" 
                    : "text-slate-400 hover:text-slate-200"
                )}
              >
                <tab.icon className="w-4 h-4" />
                {tab.label}
              </button>
            ))}
          </div>
          
          {/* 指挥官模式开关 */}
          <button
            onClick={() => setShowCommander(!showCommander)}
            className={clsx(
              "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all",
              showCommander 
                ? "bg-blue-600 text-white" 
                : "bg-slate-700 text-slate-300 hover:bg-slate-600"
            )}
          >
            <Shield className="w-4 h-4" />
            指挥官模式
          </button>
          
          {/* 仿真时间控件 */}
          <div className="flex items-center bg-slate-900 rounded-lg p-1.5 pl-4 border border-slate-700">
            <div className="text-sm mr-4 font-mono text-slate-300">
              <span className="text-slate-500">Tick:</span> {tick} / {totalTicks}
            </div>
            
            <button 
              onClick={() => setSpeed(s => Math.max(0.5, s - 0.5))}
              className="p-2 hover:bg-slate-700 rounded text-slate-400 hover:text-white"
            >
              <FastForward className="w-4 h-4 rotate-180" />
            </button>
            
            <button 
              onClick={handlePlayPause}
              className={clsx(
                "p-2 rounded mx-1",
                isPlaying ? "bg-amber-500/20 text-amber-500" : "bg-emerald-500/20 text-emerald-500"
              )}
            >
              {isPlaying ? <Pause className="w-5 h-5 fill-current" /> : <Play className="w-5 h-5 fill-current" />}
            </button>
            
            <button 
              onClick={() => setSpeed(s => Math.min(3, s + 0.5))}
              className="p-2 hover:bg-slate-700 rounded text-slate-400 hover:text-white"
            >
              <FastForward className="w-4 h-4" />
            </button>
            
            <div className="w-12 text-center text-xs text-slate-500 ml-2 font-medium">
              {speed}x
            </div>
          </div>
        </div>
      </header>
      
      {/* 主内容区 */}
      <main className="flex-1 flex overflow-hidden">
        {/* 左侧 - 地图/可视化区域 */}
        <div className={clsx("flex-1 relative group transition-all duration-300", showCommander && "lg:w-1/2 w-full")}>
          {activeTab === 'map' && (
            <div className="absolute inset-0">
              <MapContainer center={[39.9042, 116.4074]} zoom={15} zoomControl={false} style={{ height: '100%', width: '100%' }}>
                <TileLayer
                  attribution='© OpenStreetMap'
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                <DisasterLayer zones={Object.values(data.worldState.zones)} />
                <InfrastructureLayer />
                <NegotiationLines negotiations={data.negotiations} agents={data.agents} />
                <AgentMarkers 
                  agents={data.agents} 
                  selectedAgent={selectedAgent}
                  onSelectAgent={setSelectedAgent}
                />
              </MapContainer>
              
              {/* 地图浮动控制器 */}
              <div className="absolute top-4 left-4 z-[1000] flex flex-col gap-2">
                <div className="bg-slate-900/90 backdrop-blur border border-slate-700 p-3 rounded-lg shadow-xl">
                  <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">图例</h3>
                  <div className="space-y-1.5 text-xs">
                    <div className="flex items-center gap-2"><div className="w-3 h-3 bg-red-500 rounded"></div> 消防队</div>
                    <div className="flex items-center gap-2"><div className="w-3 h-3 bg-white border border-slate-400 rounded-full flex items-center justify-center text-red-600 font-bold text-[8px]">+</div> 医疗队</div>
                    <div className="flex items-center gap-2"><div className="w-3 h-3 bg-orange-500 rounded"></div> 仓库</div>
                    <div className="flex items-center gap-2"><div className="w-3 h-3 bg-sky-500 rounded"></div> 运输</div>
                    <div className="flex items-center gap-2"><div className="w-3 h-3 bg-slate-500 rounded"></div> 警察</div>
                    <div className="flex items-center gap-2"><div className="w-3 h-3 bg-emerald-500 rounded"></div> 基础设施</div>
                    <div className="flex items-center gap-2"><div className="w-3 h-3 bg-purple-500 rounded"></div> 公宣</div>
                    <div className="flex items-center gap-2"><div className="w-3 h-3 bg-yellow-400 rounded-full"></div> EOC</div>
                  </div>
                </div>
              </div>
            </div>
          )}
          
          {activeTab === 'dashboard' && (
            <GlobalDashboard data={data} />
          )}
          
          {activeTab === 'collaboration' && (
            <CollaborationGraph data={data} />
          )}
        </div>
        
        {/* 右侧面板区域 */}
        <div className={clsx(
          "flex flex-col transition-all duration-300",
          showCommander ? "w-1/2 border-l border-slate-700" : "w-96"
        )}>
          {showCommander ? (
            <CommanderPanel 
              suggestions={data.suggestions}
              pendingActions={data.pendingActions || []}
              escalatedConflicts={data.escalatedConflicts || []}
              onDecision={handleHumanDecision}
              onCancelAction={handleCancelAction}
              onModifyAction={handleModifyAction}
              onResolveConflict={handleResolveConflict}
            />
          ) : (
            <>
              <TimelinePanel 
                events={data.events} 
                currentTick={tick} 
                className="flex-1"
              />
              
              {selectedAgent && (
                <AgentDetailPanel 
                  agent={data.agents.find(a => a.id === selectedAgent)} 
                  onClose={() => setSelectedAgent(null)}
                />
              )}
            </>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
