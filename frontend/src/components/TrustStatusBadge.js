import React from 'react';
import { Shield, CheckCircle, AlertCircle, XCircle } from 'lucide-react';
import { clsx } from 'clsx';

export default function TrustStatusBadge({ status }) {
    const getConfig = () => {
        switch(status) {
            case 'passed':
                return {
                    icon: CheckCircle,
                    color: 'text-green-400',
                    bg: 'bg-green-500/10',
                    label: '已通过'
                };
            case 'failed':
                return {
                    icon: XCircle,
                    color: 'text-red-400',
                    bg: 'bg-red-500/10',
                    label: '未通过'
                };
            case 'warning':
                return {
                    icon: AlertCircle,
                    color: 'text-amber-400',
                    bg: 'bg-amber-500/10',
                    label: '有警告'
                };
            default:
                return {
                    icon: Shield,
                    color: 'text-slate-400',
                    bg: 'bg-slate-500/10',
                    label: '校验中'
                };
        }
    };
    
    const config = getConfig();
    const Icon = config.icon;
    
    return (
        <div className={clsx("flex items-center gap-2 px-3 py-1.5 rounded-full", config.bg)}>
            <Icon size={16} className={config.color} />
            <span className={clsx("text-xs font-medium", config.color)}>
                {config.label}
            </span>
        </div>
    );
}
