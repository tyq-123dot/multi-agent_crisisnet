import React, { useState } from 'react';
import {
  Check, X, Edit3, Clock, AlertTriangle, Shield, Activity, User, Zap, Lock, Unlock,
  MessageSquare, TrendingUp, Trash2, Undo2, ClipboardList, Terminal, Send
} from 'lucide-react';
import { clsx } from 'clsx';

function VerificationBadge({ result }) {
  const status = result.status;

  const getColor = () => {
    switch (status) {
      case 'passed': return 'bg-green-500/20 text-green-400 border-green-500/30';
      case 'failed': return 'bg-red-500/20 text-red-400 border-red-500/30';
      case 'warning': return 'bg-amber-500/20 text-amber-400 border-amber-500/30';
      default: return 'bg-slate-600/20 text-slate-400 border-slate-500/30';
    }
  };

  return (
    <div className={clsx(
      "flex items-center gap-2 px-3 py-1.5 rounded-full text-xs border",
      getColor()
    )}>
      {status === 'passed' && <Check size={14} />}
      {status === 'failed' && <X size={14} />}
      {status === 'warning' && <AlertTriangle size={14} />}
      <span className="font-medium">{result.check_name.replace('_', ' ')}</span>
      <span className="opacity-75">{result.message}</span>
    </div>
  );
}

function PermissionLevelBadge({ level }) {
  const levelInfo = {
    1: {
      label: "LEVEL 1 - 需人类批准",
      color: "bg-red-500/20 text-red-400 border-red-500/40",
      icon: Lock
    },
    2: {
      label: "LEVEL 2 - 自动执行但记录",
      color: "bg-amber-500/20 text-amber-400 border-amber-500/40",
      icon: Shield
    },
    3: {
      label: "LEVEL 3 - 自动执行",
      color: "bg-green-500/20 text-green-400 border-green-500/40",
      icon: Unlock
    }
  };

  const info = levelInfo[level] || levelInfo[3];
  const Icon = info.icon;

  return (
    <div className={clsx(
      "flex items-center gap-2 px-3 py-1.5 rounded-full text-xs border font-semibold",
      info.color
    )}>
      <Icon size={14} />
      <span>{info.label}</span>
    </div>
  );
}

function SuggestionCard({ card, onApprove, onReject, onModify }) {
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedback, setFeedback] = useState('');

  const roleColors = {
    'eoc': 'bg-yellow-500/20 text-yellow-400',
    'fire': 'bg-red-500/20 text-red-400',
    'medical': 'bg-blue-500/20 text-blue-400',
    'warehouse': 'bg-orange-500/20 text-orange-400',
    'transport': 'bg-sky-500/20 text-sky-400',
    'police': 'bg-slate-500/20 text-slate-200',
    'utility': 'bg-emerald-500/20 text-emerald-400',
    'public_info': 'bg-purple-500/20 text-purple-400'
  };

  const roleLabels = {
    'eoc': '🏢 EOC',
    'fire': '🚒 消防',
    'medical': '🚑 医疗',
    'warehouse': '🏭 仓库',
    'transport': '🚚 运输',
    'police': '🚓 警察',
    'utility': '🔧 公共设施',
    'public_info': '📢 公共信息'
  };

  const statusColors = {
    'pending': 'border-amber-500/50 bg-amber-500/5',
    'approved': 'border-green-500/50 bg-green-500/5',
    'rejected': 'border-red-500/50 bg-red-500/5',
    'modified': 'border-blue-500/50 bg-blue-500/5',
    'timeout': 'border-slate-500/50 bg-slate-500/5'
  };

  return (
    <div className={clsx(
      "border rounded-xl p-5 space-y-4 transition-all duration-200",
      statusColors[card.status]
    )}>
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3">
          <div className={clsx("w-12 h-12 rounded-xl flex items-center justify-center text-2xl", roleColors[card.agent_role])}>
            {roleLabels[card.agent_role]?.split(' ')[0]}
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="font-bold text-white">
                {roleLabels[card.agent_role] || card.agent_role}
              </h3>
            </div>
            <p className="text-sm text-slate-400">
              {card.agent_id} · {new Date(card.created_at).toLocaleTimeString()}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <PermissionLevelBadge level={card.permission_level} />
          {card.deadline && card.status === 'pending' && card.permission_level === 1 && (
            <div className="flex items-center gap-1.5 text-amber-400 text-sm">
              <Clock size={16} />
              <span className="font-mono">
                {Math.max(0, Math.ceil((new Date(card.deadline) - new Date()) / 1000))}s
              </span>
            </div>
          )}
        </div>
      </div>

      <div className="space-y-2">
        <div className="text-slate-300 leading-relaxed">
          <span className="text-slate-400">💭 智能体推理：</span> {card.reasoning}
        </div>

        <div className="bg-slate-900/50 border border-slate-700 rounded-lg p-3">
          <div className="text-xs text-slate-400 mb-2 font-semibold uppercase tracking-wider">
            提议的动作
          </div>
          <div className="font-mono text-sm text-slate-200">
            {JSON.stringify(card.action_payload, null, 2)}
          </div>
        </div>
      </div>

      {card.verification_results && card.verification_results.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-xs text-slate-400 font-semibold uppercase tracking-wider">
            <Shield size={14} />
            可信校验结果
          </div>
          <div className="flex flex-wrap gap-2">
            {card.verification_results.map((vr, idx) => (
              <VerificationBadge key={idx} result={vr} />
            ))}
          </div>
        </div>
      )}

      {card.status === 'pending' && card.permission_level === 1 ? (
        <div className="space-y-3">
          <div className="flex gap-2">
            <button
              onClick={() => onApprove(card.card_id)}
              className="flex-1 flex items-center justify-center gap-2 bg-green-500 hover:bg-green-600 text-white px-4 py-2.5 rounded-lg font-medium transition-colors"
            >
              <Check size={18} />
              批准
            </button>
            <button
              onClick={() => setShowFeedback(true)}
              className="flex-1 flex items-center justify-center gap-2 bg-blue-500 hover:bg-blue-600 text-white px-4 py-2.5 rounded-lg font-medium transition-colors"
            >
              <Edit3 size={18} />
              修改
            </button>
            <button
              onClick={() => onReject(card.card_id)}
              className="flex-1 flex items-center justify-center gap-2 bg-red-500 hover:bg-red-600 text-white px-4 py-2.5 rounded-lg font-medium transition-colors"
            >
              <X size={18} />
              拒绝
            </button>
          </div>

          {showFeedback && (
            <div className="bg-slate-900/70 border border-slate-700 rounded-lg p-3 space-y-2">
              <textarea
                className="w-full bg-slate-950 border border-slate-700 rounded-md p-2 text-sm text-white focus:outline-none focus:border-blue-500"
                placeholder="添加修改意见或备注..."
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                rows={2}
              />
              <div className="flex justify-end gap-2">
                <button
                  onClick={() => {
                    setShowFeedback(false);
                    setFeedback('');
                  }}
                  className="px-3 py-1.5 text-sm text-slate-400 hover:text-white"
                >
                  取消
                </button>
                <button
                  onClick={() => {
                    onModify(card.card_id, feedback);
                    setShowFeedback(false);
                    setFeedback('');
                  }}
                  className="px-3 py-1.5 text-sm bg-blue-500 text-white rounded-md hover:bg-blue-600"
                >
                  确认修改
                </button>
              </div>
            </div>
          )}
        </div>
      ) : card.status === 'pending' ? (
        <div className="text-sm text-amber-400 italic bg-amber-500/5 p-3 rounded-lg border border-amber-500/30">
          此权限级别无需人工审核，已自动执行。
        </div>
      ) : (
        <div className="border-t border-slate-700/50 pt-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className={clsx(
              "px-2 py-1 rounded-full text-xs font-medium",
              card.status === 'approved' ? 'bg-green-500/20 text-green-400' :
                card.status === 'rejected' ? 'bg-red-500/20 text-red-400' :
                  card.status === 'modified' ? 'bg-blue-500/20 text-blue-400' :
                    'bg-slate-500/20 text-slate-400'
            )}>
              {card.status.charAt(0).toUpperCase() + card.status.slice(1)}
            </span>
            {card.resolved_at && (
              <span className="text-sm text-slate-500">
                {new Date(card.resolved_at).toLocaleTimeString()}
              </span>
            )}
          </div>
          {card.human_feedback && (
            <p className="text-sm text-slate-400 italic">
              "{card.human_feedback}"
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function EscalatedConflictCard({ conflict, onResolve }) {
  const [showResolver, setShowResolver] = useState(false);
  const [resolutionText, setResolutionText] = useState('');

  return (
    <div className="border border-red-500/50 bg-red-500/5 rounded-xl p-5 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <AlertTriangle className="text-red-400" />
          <h3 className="font-bold text-white">冲突升级</h3>
        </div>
        <span className="text-xs text-red-400 bg-red-500/20 px-2 py-1 rounded-full">
          需要人工介入
        </span>
      </div>

      <div className="space-y-2">
        <p className="text-slate-300">{conflict.summary}</p>
        <p className="text-sm text-slate-500">
          参与者: {conflict.participants.join(' ↔ ')}
        </p>
      </div>

      {conflict.messages && conflict.messages.length > 0 && (
        <div className="bg-slate-900/70 border border-slate-700 rounded-lg p-3">
          <div className="text-xs text-slate-400 mb-2 font-semibold uppercase tracking-wider">
            协商历史
          </div>
          <div className="space-y-2">
            {conflict.messages.map((msg, idx) => (
              <div key={idx} className="text-xs text-slate-300">
                <span className="text-slate-500">[{msg.step}]</span> {msg.sender}:
                {JSON.stringify(msg.content)}
              </div>
            ))}
          </div>
        </div>
      )}

      {!showResolver ? (
        <button
          onClick={() => setShowResolver(true)}
          className="w-full bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded-lg font-medium transition-colors"
        >
          解决冲突
        </button>
      ) : (
        <div className="space-y-2">
          <textarea
            className="w-full bg-slate-950 border border-slate-700 rounded-md p-2 text-sm text-white focus:outline-none focus:border-blue-500"
            placeholder="输入解决方案..."
            value={resolutionText}
            onChange={(e) => setResolutionText(e.target.value)}
            rows={3}
          />
          <div className="flex gap-2">
            <button
              onClick={() => setShowResolver(false)}
              className="flex-1 bg-slate-700 hover:bg-slate-600 text-white px-4 py-2 rounded-lg"
            >
              取消
            </button>
            <button
              onClick={() => {
                onResolve(conflict.session_id, resolutionText);
                setShowResolver(false);
                setResolutionText('');
              }}
              className="flex-1 bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded-lg"
            >
              提交解决
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function HelpRequestCard({ request, onApprove, onReject }) {
  const getCredibilityColor = (score) => {
    if (score >= 0.7) return 'bg-green-500/20 text-green-400 border-green-500/30';
    if (score >= 0.4) return 'bg-amber-500/20 text-amber-400 border-amber-500/30';
    return 'bg-red-500/20 text-red-400 border-red-500/30';
  };

  return (
    <div className="border border-slate-700 bg-slate-800 rounded-xl p-5 space-y-4">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-red-500/20 flex items-center justify-center text-2xl">
            🚨
          </div>
          <div>
            <h3 className="font-bold text-white">{request.location}</h3>
            <p className="text-sm text-slate-400">
              {request.request_id} · {request.post_count} 条相关帖子
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div className={clsx(
            "flex items-center gap-2 px-3 py-1.5 rounded-full text-xs border font-semibold",
            getCredibilityColor(request.verification?.credibility_score || 0.5)
          )}>
            <Shield size={14} />
            可信度: {Math.round((request.verification?.credibility_score || 0.5) * 100)}%
          </div>
          <div className="flex items-center gap-1.5 text-amber-400 text-sm">
            <TrendingUp size={16} />
            <span className="font-mono">热度: {request.heat_score}</span>
          </div>
        </div>
      </div>

      <div className="bg-slate-900/50 border border-slate-700 rounded-lg p-4">
        <div className="text-xs text-slate-400 mb-2 font-semibold uppercase tracking-wider">
          求助内容
        </div>
        <p className="text-slate-200">{request.content_summary}</p>
      </div>

      {request.verification && (
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-xs text-slate-400 font-semibold uppercase tracking-wider">
            <Shield size={14} />
            可信度分析
          </div>
          <div className="bg-slate-900/70 border border-slate-700 rounded-lg p-3 space-y-2">
            <p className="text-sm text-slate-300">{request.verification.reasoning}</p>
            {request.verification.supporting_factors?.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {request.verification.supporting_factors.map((factor, idx) => (
                  <span key={idx} className="px-2 py-1 bg-green-500/10 text-green-400 text-xs rounded-full">
                    ✓ {factor}
                  </span>
                ))}
              </div>
            )}
            {request.verification.risk_factors?.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {request.verification.risk_factors.map((factor, idx) => (
                  <span key={idx} className="px-2 py-1 bg-red-500/10 text-red-400 text-xs rounded-full">
                    ⚠ {factor}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      <div className="flex gap-2">
        <button
          onClick={() => onReject(request.request_id)}
          className="flex-1 flex items-center justify-center gap-2 bg-slate-600 hover:bg-slate-500 text-white px-4 py-2.5 rounded-lg font-medium transition-colors"
        >
          <X size={18} />
          驳回
        </button>
        <button
          onClick={() => onApprove(request.request_id)}
          className="flex-1 flex items-center justify-center gap-2 bg-green-500 hover:bg-green-600 text-white px-4 py-2.5 rounded-lg font-medium transition-colors"
        >
          <Check size={18} />
          批准
        </button>
      </div>
    </div>
  );
}

function PendingActionCard({ action, onCancel, onModify }) {
  const [showModifying, setShowModifying] = useState(false);
  const [newPayloadText, setNewPayloadText] = useState('');

  const roleColors = {
    'eoc': 'bg-yellow-500/20 text-yellow-400',
    'fire': 'bg-red-500/20 text-red-400',
    'medical': 'bg-blue-500/20 text-blue-400',
    'warehouse': 'bg-orange-500/20 text-orange-400',
    'transport': 'bg-sky-500/20 text-sky-400',
    'police': 'bg-slate-500/20 text-slate-200',
    'utility': 'bg-emerald-500/20 text-emerald-400',
    'public_info': 'bg-purple-500/20 text-purple-400'
  };

  const roleLabels = {
    'eoc': '🏢 EOC',
    'fire': '🚒 消防',
    'medical': '🚑 医疗',
    'warehouse': '🏭 仓库',
    'transport': '🚚 运输',
    'police': '🚓 警察',
    'utility': '🔧 公共设施',
    'public_info': '📢 公共信息'
  };

  return (
    <div className="border border-slate-700 bg-slate-800 rounded-xl p-4 space-y-3">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className={clsx("w-10 h-10 rounded-lg flex items-center justify-center text-xl", roleColors[action.agent_role])}>
            {roleLabels[action.agent_role]?.split(' ')[0]}
          </div>
          <div>
            <p className="font-medium text-white">{roleLabels[action.agent_role]}</p>
            <p className="text-xs text-slate-400">{action.action_id}</p>
          </div>
        </div>
        <div className="flex gap-1">
          <button
            onClick={() => setShowModifying(!showModifying)}
            className="p-1.5 text-blue-400 hover:text-blue-300 hover:bg-blue-500/20 rounded"
            title="修改动作"
          >
            <Edit3 size={16} />
          </button>
          <button
            onClick={() => onCancel(action.action_id)}
            className="p-1.5 text-red-400 hover:text-red-300 hover:bg-red-500/20 rounded"
            title="取消动作"
          >
            <Trash2 size={16} />
          </button>
        </div>
      </div>

      <div className="bg-slate-900 border border-slate-700 rounded-lg p-3">
        <div className="font-mono text-xs text-slate-200">
          {JSON.stringify(action.action_payload, null, 2)}
        </div>
      </div>

      {showModifying && (
        <div className="space-y-2">
          <textarea
            className="w-full bg-slate-950 border border-slate-700 rounded-md p-2 text-sm text-white font-mono focus:outline-none focus:border-blue-500"
            placeholder="输入新的动作 JSON..."
            value={newPayloadText}
            onChange={(e) => setNewPayloadText(e.target.value)}
            rows={3}
          />
          <div className="flex gap-2">
            <button
              onClick={() => setShowModifying(false)}
              className="flex-1 text-xs px-3 py-1.5 text-slate-400 hover:text-white"
            >
              取消
            </button>
            <button
              onClick={() => {
                try {
                  const newPayload = JSON.parse(newPayloadText);
                  onModify(action.action_id, newPayload);
                  setShowModifying(false);
                } catch (e) {
                  alert('JSON 格式错误');
                }
              }}
              className="flex-1 text-xs px-3 py-1.5 bg-blue-500 text-white rounded-md hover:bg-blue-600"
            >
              保存修改
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function DirectCommandPanel({ onSendCommand }) {
  const [command, setCommand] = useState('');
  const [targetAgents, setTargetAgents] = useState([]);
  const [isSending, setIsSending] = useState(false);

  const availableAgents = ['eoc', 'fire_rescue', 'medical', 'logistics', 'public_info'];

  const handleSend = async () => {
    if (!command.trim()) return;
    setIsSending(true);
    await onSendCommand(command, targetAgents);
    setCommand('');
    setIsSending(false);
  };

  const toggleAgent = (agent) => {
    if (targetAgents.includes(agent)) {
      setTargetAgents(targetAgents.filter(a => a !== agent));
    } else {
      setTargetAgents([...targetAgents, agent]);
    }
  };

  return (
    <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
      <div className="flex items-center gap-2 mb-3">
        <Terminal size={18} className="text-blue-400" />
        <h3 className="font-semibold text-white">直接指令</h3>
      </div>
      <textarea
        value={command}
        onChange={(e) => setCommand(e.target.value)}
        placeholder="输入指令，例如：'所有医疗队集中到第三中学'"
        className="w-full bg-slate-950 border border-slate-700 rounded-lg p-3 text-sm text-white placeholder-slate-500 mb-3 focus:outline-none focus:border-blue-500"
        rows={3}
      />
      <div className="flex flex-wrap gap-2 mb-3">
        {availableAgents.map(agent => (
          <button
            key={agent}
            onClick={() => toggleAgent(agent)}
            className={clsx(
              "px-3 py-1 text-xs rounded-full transition-colors",
              targetAgents.includes(agent)
                ? "bg-blue-500 text-white"
                : "bg-slate-700 text-slate-300 hover:bg-slate-600"
            )}
          >
            {agent}
          </button>
        ))}
      </div>
      <button
        onClick={handleSend}
        disabled={!command.trim() || isSending}
        className="w-full bg-blue-500 hover:bg-blue-600 disabled:bg-slate-600 disabled:cursor-not-allowed text-white py-2 rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
      >
        <Send size={16} />
        发送指令
      </button>
    </div>
  );
}

function ApprovalRequestCard({ request, onApprove, onReject, onModify }) {
  const [showModify, setShowModify] = useState(false);
  const [modifiedDecision, setModifiedDecision] = useState('');

  const levelColors = {
    1: 'bg-green-500/20 text-green-400 border-green-500/30',
    2: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
    3: 'bg-red-500/20 text-red-400 border-red-500/30',
    4: 'bg-red-600/30 text-red-300 border-red-600/50'
  };

  const handleModify = () => {
    try {
      const decision = JSON.parse(modifiedDecision || '{}');
      onModify(request.request_id, decision);
      setShowModify(false);
    } catch (e) {
      alert('JSON 格式错误');
    }
  };

  return (
    <div className="bg-slate-800 rounded-xl p-5 border border-slate-700">
      <div className="flex items-start justify-between mb-3">
        <div>
          <span className={clsx(
            "px-2 py-1 rounded-full text-xs font-semibold border mb-2",
            levelColors[request.level]
          )}>
            LEVEL {request.level}
          </span>
          <h4 className="font-semibold text-white">
            {request.agent_role} 决策请求
          </h4>
          <p className="text-xs text-slate-400">
            {new Date(request.created_at).toLocaleString()}
          </p>
        </div>
      </div>

      <div className="mb-4">
        <p className="text-sm text-slate-300 mb-2">{request.reasoning}</p>
        <div className="bg-slate-950 rounded-lg p-3 font-mono text-xs text-slate-300">
          {JSON.stringify(request.decision, null, 2)}
        </div>
      </div>

      {!showModify ? (
        <div className="flex gap-2">
          <button
            onClick={() => onReject(request.request_id)}
            className="flex-1 bg-slate-600 hover:bg-slate-500 text-white py-2 rounded-lg font-medium transition-colors"
          >
            拒绝
          </button>
          <button
            onClick={() => setShowModify(true)}
            className="flex-1 bg-blue-500 hover:bg-blue-600 text-white py-2 rounded-lg font-medium transition-colors"
          >
            修改
          </button>
          <button
            onClick={() => onApprove(request.request_id)}
            className="flex-1 bg-green-500 hover:bg-green-600 text-white py-2 rounded-lg font-medium transition-colors"
          >
            批准
          </button>
        </div>
      ) : (
        <div className="space-y-2">
          <textarea
            value={modifiedDecision || JSON.stringify(request.decision, null, 2)}
            onChange={(e) => setModifiedDecision(e.target.value)}
            className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs font-mono text-white"
            rows={4}
          />
          <div className="flex gap-2">
            <button
              onClick={() => setShowModify(false)}
              className="flex-1 bg-slate-600 hover:bg-slate-500 text-white py-2 rounded-lg"
            >
              取消
            </button>
            <button
              onClick={handleModify}
              className="flex-1 bg-blue-500 hover:bg-blue-600 text-white py-2 rounded-lg"
            >
              确认修改
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function CommanderPanel({
  suggestions,
  pendingActions,
  escalatedConflicts,
  helpRequests,
  approvalRequests,
  onDecision,
  onCancelAction,
  onModifyAction,
  onResolveConflict,
  onApproveHelpRequest,
  onRejectHelpRequest,
  onApproveApproval,
  onRejectApproval,
  onModifyApproval,
  onSendCommand
}) {
  const [activeTab, setActiveTab] = useState('help-requests');
  const [showCommandPanel, setShowCommandPanel] = useState(false);

  const pendingSuggestions = suggestions?.pending || [];
  const recentSuggestions = suggestions?.recent || [];
  const pendingHelpRequests = helpRequests || [];
  const pendingApprovals = approvalRequests || [];

  return (
    <div className="h-full bg-slate-900 flex flex-col">
      <div className="p-4 border-b border-slate-700 bg-slate-800">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-bold text-lg text-white flex items-center gap-2">
            <User className="text-blue-400" />
            指挥官控制台
          </h2>
          <div className="flex gap-2">
            <button
              onClick={() => setShowCommandPanel(!showCommandPanel)}
              className="flex items-center gap-1 px-3 py-1.5 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-sm transition-colors"
            >
              <Terminal size={14} />
              指令
            </button>
          </div>
        </div>

        <div className="flex flex-wrap gap-2 mb-3">
          {pendingHelpRequests.length > 0 && (
            <span className="bg-red-500/20 text-red-400 text-xs px-2 py-1 rounded-full font-medium animate-pulse">
              {pendingHelpRequests.length} 求助待审核
            </span>
          )}
          {pendingApprovals.length > 0 && (
            <span className="bg-orange-500/20 text-orange-400 text-xs px-2 py-1 rounded-full font-medium animate-pulse">
              {pendingApprovals.length} 决策待审核
            </span>
          )}
          {pendingSuggestions.filter(c => c.permission_level === 1).length > 0 && (
            <span className="bg-red-500/20 text-red-400 text-xs px-2 py-1 rounded-full font-medium">
              {pendingSuggestions.filter(c => c.permission_level === 1).length} LEVEL 1 待审核
            </span>
          )}
          {escalatedConflicts.length > 0 && (
            <span className="bg-red-500/20 text-red-400 text-xs px-2 py-1 rounded-full font-medium animate-pulse">
              {escalatedConflicts.length} 冲突
            </span>
          )}
          {pendingActions.length > 0 && (
            <span className="bg-amber-500/20 text-amber-400 text-xs px-2 py-1 rounded-full font-medium">
              {pendingActions.length} 待执行
            </span>
          )}
        </div>

        {showCommandPanel && (
          <DirectCommandPanel onSendCommand={onSendCommand} />
        )}

        <div className="flex border-b border-slate-700 overflow-x-auto mt-3">
          <button
            onClick={() => setActiveTab('help-requests')}
            className={clsx(
              "flex-1 px-4 py-3 text-sm font-medium transition-colors whitespace-nowrap",
              activeTab === 'help-requests' ? 'bg-slate-800 text-white border-b-2 border-blue-500' : 'text-slate-400 hover:text-slate-200'
            )}
          >
            求助审核 ({pendingHelpRequests.length})
          </button>
          <button
            onClick={() => setActiveTab('approvals')}
            className={clsx(
              "flex-1 px-4 py-3 text-sm font-medium transition-colors whitespace-nowrap",
              activeTab === 'approvals' ? 'bg-slate-800 text-white border-b-2 border-blue-500' : 'text-slate-400 hover:text-slate-200'
            )}
          >
            决策审核 ({pendingApprovals.length})
          </button>
          <button
            onClick={() => setActiveTab('suggestions')}
            className={clsx(
              "flex-1 px-4 py-3 text-sm font-medium transition-colors whitespace-nowrap",
              activeTab === 'suggestions' ? 'bg-slate-800 text-white border-b-2 border-blue-500' : 'text-slate-400 hover:text-slate-200'
            )}
          >
            建议 ({pendingSuggestions.length})
          </button>
          <button
            onClick={() => setActiveTab('conflicts')}
            className={clsx(
              "flex-1 px-4 py-3 text-sm font-medium transition-colors whitespace-nowrap",
              activeTab === 'conflicts' ? 'bg-slate-800 text-white border-b-2 border-blue-500' : 'text-slate-400 hover:text-slate-200'
            )}
          >
            冲突 ({escalatedConflicts.length})
          </button>
          <button
            onClick={() => setActiveTab('actions')}
            className={clsx(
              "flex-1 px-4 py-3 text-sm font-medium transition-colors whitespace-nowrap",
              activeTab === 'actions' ? 'bg-slate-800 text-white border-b-2 border-blue-500' : 'text-slate-400 hover:text-slate-200'
            )}
          >
            待执行 ({pendingActions.length})
          </button>
          <button
            onClick={() => setActiveTab('recent')}
            className={clsx(
              "flex-1 px-4 py-3 text-sm font-medium transition-colors whitespace-nowrap",
              activeTab === 'recent' ? 'bg-slate-800 text-white border-b-2 border-blue-500' : 'text-slate-400 hover:text-slate-200'
            )}
          >
            历史
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
        {activeTab === 'help-requests' && pendingHelpRequests.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-slate-500">
            <MessageSquare size={48} className="mb-3 opacity-30" />
            <p className="text-lg font-medium">暂无待审核求助</p>
            <p className="text-sm">社交媒体监控中...</p>
          </div>
        )}

        {activeTab === 'help-requests' && pendingHelpRequests.map(request => (
          <HelpRequestCard
            key={request.request_id}
            request={request}
            onApprove={onApproveHelpRequest}
            onReject={onRejectHelpRequest}
          />
        ))}

        {activeTab === 'approvals' && pendingApprovals.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-slate-500">
            <Shield size={48} className="mb-3 opacity-30" />
            <p className="text-lg font-medium">暂无待审核决策</p>
            <p className="text-sm">所有决策已处理完毕</p>
          </div>
        )}

        {activeTab === 'approvals' && pendingApprovals.map(request => (
          <ApprovalRequestCard
            key={request.request_id}
            request={request}
            onApprove={onApproveApproval}
            onReject={onRejectApproval}
            onModify={onModifyApproval}
          />
        ))}

        {activeTab === 'suggestions' && pendingSuggestions.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-slate-500">
            <Zap size={48} className="mb-3 opacity-30" />
            <p className="text-lg font-medium">暂无待审核建议</p>
            <p className="text-sm">系统运行平稳中...</p>
          </div>
        )}

        {activeTab === 'suggestions' && pendingSuggestions.map(card => (
          <SuggestionCard
            key={card.card_id}
            card={card}
            onApprove={(id) => onDecision(id, 'approved')}
            onReject={(id) => onDecision(id, 'rejected')}
            onModify={(id, fb) => onDecision(id, 'modified', fb)}
          />
        ))}

        {activeTab === 'conflicts' && escalatedConflicts.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-slate-500">
            <Shield size={48} className="mb-3 opacity-30" />
            <p className="text-lg font-medium">暂无升级冲突</p>
            <p className="text-sm">智能体之间协作顺利...</p>
          </div>
        )}

        {activeTab === 'conflicts' && escalatedConflicts.map(conflict => (
          <EscalatedConflictCard
            key={conflict.session_id}
            conflict={conflict}
            onResolve={onResolveConflict}
          />
        ))}

        {activeTab === 'actions' && pendingActions.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-slate-500">
            <ClipboardList size={48} className="mb-3 opacity-30" />
            <p className="text-lg font-medium">暂无待执行动作</p>
            <p className="text-sm">所有动作已处理完毕</p>
          </div>
        )}

        {activeTab === 'actions' && pendingActions.map(action => (
          <PendingActionCard
            key={action.action_id}
            action={action}
            onCancel={onCancelAction}
            onModify={onModifyAction}
          />
        ))}

        {activeTab === 'recent' && recentSuggestions.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-slate-500">
            <Activity size={48} className="mb-3 opacity-30" />
            <p className="text-lg font-medium">暂无历史记录</p>
            <p className="text-sm">开始仿真后将显示处理记录</p>
          </div>
        )}

        {activeTab === 'recent' && recentSuggestions.map(card => (
          <SuggestionCard
            key={card.card_id}
            card={card}
            onApprove={() => { }}
            onReject={() => { }}
            onModify={() => { }}
          />
        ))}
      </div>
    </div>
  );
}
