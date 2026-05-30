import React from 'react';
import { Polygon, Tooltip } from 'react-leaflet';

// 城市网格区域的边界（模拟）
const ZONE_BOUNDS = {
  'zone_01': [[39.900, 116.400], [39.905, 116.405]],
  'zone_02': [[39.900, 116.405], [39.905, 116.410]],
  'zone_03': [[39.900, 116.410], [39.905, 116.415]],
  'zone_04': [[39.905, 116.400], [39.910, 116.405]],
  'zone_05': [[39.905, 116.405], [39.910, 116.410]],
  'zone_06': [[39.905, 116.410], [39.910, 116.415]],
  'zone_07': [[39.910, 116.400], [39.915, 116.405]],
  'zone_08': [[39.910, 116.405], [39.915, 116.410]],
  'zone_09': [[39.910, 116.410], [39.915, 116.415]],
};

const getDisasterColor = (intensity) => {
  if (intensity > 0.8) return '#7f1d1d'; // 深红
  if (intensity > 0.6) return '#dc2626'; // 红
  if (intensity > 0.4) return '#ea580c'; // 橙红
  if (intensity > 0.2) return '#f97316'; // 橙
  if (intensity > 0.05) return '#fdba74'; // 浅橙
  return 'transparent';
};

export default function DisasterLayer({ zones }) {
  return (
    <>
      {zones.map((zone) => {
        const bounds = ZONE_BOUNDS[zone.id];
        if (!bounds) return null;
        
        const color = getDisasterColor(zone.disasterIntensity);
        const opacity = Math.min(0.7, zone.disasterIntensity * 0.8 + 0.1);

        return (
          <Polygon
            key={zone.id}
            positions={[
              [bounds[0][0], bounds[0][1]],
              [bounds[0][0], bounds[1][1]],
              [bounds[1][0], bounds[1][1]],
              [bounds[1][0], bounds[0][1]],
            ]}
            pathOptions={{
              fillColor: color,
              fillOpacity: opacity,
              weight: zone.roadAvailable ? 1 : 3,
              color: zone.roadAvailable ? '#475569' : '#dc2626',
              dashArray: zone.roadAvailable ? null : '5, 5',
            }}
          >
            <Tooltip>
              <div className="text-sm p-1">
                <div className="font-bold">{zone.id}</div>
                <div className="text-xs text-slate-600">
                  灾害强度: {(zone.disasterIntensity * 100).toFixed(0)}%
                </div>
                <div className="text-xs text-red-600">
                  受困: {zone.trapped} | 伤亡: {zone.casualties}
                </div>
                <div className="text-xs mt-1">
                  道路: {zone.roadAvailable ? '✅ 畅通' : '❌ 中断'}
                </div>
              </div>
            </Tooltip>
          </Polygon>
        );
      })}
    </>
  );
}
