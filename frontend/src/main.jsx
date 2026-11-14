import React from 'react';
import { createRoot } from 'react-dom/client';
import AnalyticsApp from './AnalyticsApp';
import EdgeEmitterApp from './EdgeEmitterApp';
import './styles.css';

/**
 * Application entry router: selects between Edge Emitter Deck (:5174 / ?app=edge / VITE_APP_ROLE=edge)
 * and Server Analytics Console (:5173 default) at runtime using one shared bundle.
 */
const params = new URLSearchParams(window.location.search);
const isEdgeApp =
  window.location.port === '5174' ||
  params.get('app') === 'edge' ||
  import.meta.env.VITE_APP_ROLE === 'edge';

document.title = isEdgeApp
  ? 'RoastGlass · Edge Emitter Deck (:5174)'
  : 'RoastGlass · Server Analytics Console (:5173)';

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    {isEdgeApp ? <EdgeEmitterApp /> : <AnalyticsApp />}
  </React.StrictMode>
);
