'use client';

import 'leaflet/dist/leaflet.css';
import { CircleMarker, MapContainer, TileLayer, Tooltip } from 'react-leaflet';
import type { OpenRequest } from '../types';

const GUJARAT_CENTRE: [number, number] = [22.9, 72.6];

interface RequestsMapProps {
  requests: OpenRequest[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

/** Loaded with next/dynamic and ssr: false, because Leaflet needs window. */
export default function RequestsMap({ requests, selectedId, onSelect }: RequestsMapProps) {
  return (
    <MapContainer center={GUJARAT_CENTRE} zoom={8} className="h-96 w-full rounded-xl lg:h-[34rem]">
      <TileLayer
        attribution="&copy; OpenStreetMap contributors"
        url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {requests.map((request) => (
        <CircleMarker
          key={request.id}
          center={[request.approx_lat, request.approx_lng]}
          radius={request.id === selectedId ? 14 : 10}
          eventHandlers={{ click: () => onSelect(request.id) }}
          pathOptions={{ color: '#0a5540', fillColor: '#f5a524', fillOpacity: 0.9 }}
        >
          <Tooltip>{request.request_code}</Tooltip>
        </CircleMarker>
      ))}
    </MapContainer>
  );
}
