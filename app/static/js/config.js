export const APP_VERSION = '1.1';
export const API_BASE = location.origin;
export const WS_URL = (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws';
export const STALE_MINUTES = 30;
