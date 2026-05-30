import React from 'react';
import { CircleMarker, Tooltip } from 'react-leaflet';

// 基础设施位置（模拟）
const INFRASTRUCTURE = [
  { id: 'hospital_1', type: 'hospital', lat: 39.907, lng: 116.403, name: '市中心医院', capacity: 200, occupancy: 120 },
  { id: 'warehouse_1', type: 'warehouse', lat: 39.902, lng: 116.412, name: '物资仓库 A', supplies: 85 },
  { id: 'shelter_1', type: 'shelter', lat: 39.912, lng: 116.402, name: '避难所 1', capacity: 500, occupancy: 280 },
  { id: 'shelter_2', type: 'shelter', lat: 39.908, lng: 116.414, name: '避难所 2', capacity: 300, occupancy: 150 },
];

const getInfraColor = (type) => {
  switch (type) {
    case 'hospital': return '#3b82f6'; // 蓝色
    case 'warehouse': return '#22c55e'; // 绿色
    case 'shelter': return '#f59e0b'; // 橙色
    default: return '#6b7280';
  }
};

const getInfraIcon = (type) => {
  switch (type) {
    case 'hospital': return '🏥';
    case 'warehouse': return '📦';
    case 'shelter': return '⛺';
    default: return '📍';
  }
};

export default function InfrastructureLayer() {
  return (
    <>
      {INFRASTRUCTURE.map((infra) => (
        <CircleMarker
          key={infra.id}
          center={[infra.lat, infra.lng]}
          radius={8}
          fillColor={getInfraColor(infra.type)}
          color="#ffffff"
          weight={2}
          fillOpacity={0.9}
        >
          <Tooltip>
            <div className="text-sm p-1">
              <div className="font-bold flex items-center gap-2">
                {getInfraIcon(infra.type)} {infra.name}
              </div>
              {infra.capacity && (
                <div className="text-xs text-slate-600 mt-1">
                  容量: {infra.occupancy}/{infra.capacity}
                </div>
              )}
              {infra.supplies !== undefined && (
                <div className="text-xs text-green-600 mt-1">
                  物资剩余: {infra.supplies}%
                </div>
              )}
            </div>
          </Tooltip>
        </CircleMarker>
      ))}
    </>
  );
}
