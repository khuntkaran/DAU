'use client';

import 'leaflet/dist/leaflet.css';
import { divIcon } from 'leaflet';
import { useEffect, useMemo } from 'react';
import { Circle, LayersControl, MapContainer, Marker, TileLayer, useMap, useMapEvents } from 'react-leaflet';
import type { LatLng, MapFocus } from '../types';

export const GANDHINAGAR: LatLng = { lat: 23.2156, lng: 72.6369 };

const PIN_ZOOM = 18;
// Leaflet positions the outer element, so only the inner shape may be rotated.
const pinIcon = divIcon({
  className: 'map-pin',
  html: '<span class="map-pin-shape"></span>',
  iconSize: [28, 28],
  iconAnchor: [14, 28],
});

function ClickToPin({ onPick }: { onPick: (point: LatLng) => void }) {
  useMapEvents({
    click: ({ latlng }) => onPick({ lat: latlng.lat, lng: latlng.lng }),
  });
  return null;
}

/** Moves the view only for location and search results, never while dragging the pin. */
function FollowFocus({ focus }: { focus: MapFocus | null }) {
  const map = useMap();
  useEffect(() => {
    if (!focus) return;
    // A vague fix zooms out far enough to show its whole accuracy circle.
    const accuracy = focus.accuracy_m ?? 0;
    map.setView(focus, accuracy > 150 ? Math.max(13, PIN_ZOOM - Math.ceil(Math.log2(accuracy / 150))) : PIN_ZOOM);
  }, [map, focus]);
  return null;
}

interface MapPickerProps {
  value: LatLng | null;
  focus: MapFocus | null;
  accuracyM: number | null;
  onChange: (point: LatLng) => void;
  streetLabel: string;
  satelliteLabel: string;
}

/** Loaded with next/dynamic and ssr: false, because Leaflet needs window. */
export default function MapPicker({ value, focus, accuracyM, onChange, streetLabel, satelliteLabel }: MapPickerProps) {
  const dragHandlers = useMemo(
    () => ({
      dragend: (event: { target: { getLatLng: () => LatLng } }) => {
        const { lat, lng } = event.target.getLatLng();
        onChange({ lat, lng });
      },
    }),
    [onChange],
  );

  return (
    <MapContainer center={value ?? GANDHINAGAR} zoom={12} maxZoom={19} className="h-80 w-full rounded-xl lg:h-96">
      <LayersControl position="topright">
        <LayersControl.BaseLayer checked name={streetLabel}>
          <TileLayer
            attribution="&copy; OpenStreetMap contributors"
            url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
            maxZoom={19}
          />
        </LayersControl.BaseLayer>
        <LayersControl.BaseLayer name={satelliteLabel}>
          <TileLayer
            attribution="Imagery &copy; Esri, Maxar, Earthstar Geographics"
            url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
            maxZoom={19}
          />
        </LayersControl.BaseLayer>
      </LayersControl>
      <ClickToPin onPick={onChange} />
      <FollowFocus focus={focus} />
      {value && accuracyM && (
        <Circle center={value} radius={accuracyM} pathOptions={{ color: '#0e7a5a', fillOpacity: 0.1, weight: 1 }} />
      )}
      {value && <Marker position={value} icon={pinIcon} draggable eventHandlers={dragHandlers} />}
    </MapContainer>
  );
}
