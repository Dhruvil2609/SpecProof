/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_PLATFORM_API_URL?: string;
  readonly VITE_STATION_API_URL?: string;
  readonly VITE_STATION_MODE?: 'simulated' | 'live';
  readonly VITE_AUTH_MODE?: 'development';
}
