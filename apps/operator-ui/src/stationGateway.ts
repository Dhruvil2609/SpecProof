export interface StationReadiness {
  readonly ready: boolean;
  readonly calibrationId: string;
  readonly cameraStatus: string;
}

export interface PreviewFrame {
  readonly sequence: number;
  readonly capturedAtUtc: string;
  readonly colorJpegBase64: string;
  readonly depthPngBase64: string;
  readonly colorWidth: number;
  readonly colorHeight: number;
  readonly depthWidth: number;
  readonly depthHeight: number;
}

export interface CaptureReceipt {
  readonly captureId: string;
  readonly checksumSha256: string;
  readonly calibrationId: string;
  readonly capturedAtUtc: string;
  readonly inspectionId: string;
  readonly processingStatus: string;
}

export interface CaptureRequestContext {
  readonly tenantId: string;
  readonly stationId: string;
  readonly stationCode: string;
  readonly cameraSerial: string;
  readonly inspectionId: string;
  readonly orderCode: string;
  readonly styleCode: string;
  readonly sizeCode: string;
  readonly batchId: string | null;
  readonly techPackId: string;
  readonly techPackVersion: number;
}

export interface StationGateway {
  getReadiness(signal?: AbortSignal): Promise<StationReadiness>;
  subscribePreview(onFrame: (frame: PreviewFrame) => void, onError: () => void): () => void;
  capture(context: CaptureRequestContext, signal?: AbortSignal): Promise<CaptureReceipt>;
}

const colorPixel = '/9j/4AAQSkZJRgABAQAAAQABAAD/2Q==';
const depthPixel = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=';

export class SimulatedStationGateway implements StationGateway {
  async getReadiness(): Promise<StationReadiness> {
    return { ready: true, calibrationId: 'CAL-2026-0810-04', cameraStatus: 'READY' };
  }

  subscribePreview(onFrame: (frame: PreviewFrame) => void, _onError: () => void): () => void {
    void _onError;
    let sequence = 0;
    const emit = () => onFrame({
      sequence: sequence++,
      capturedAtUtc: new Date(Date.UTC(2026, 7, 12, 10, 0, sequence)).toISOString(),
      colorJpegBase64: colorPixel,
      depthPngBase64: depthPixel,
      colorWidth: 1280,
      colorHeight: 720,
      depthWidth: 848,
      depthHeight: 480,
    });
    emit();
    const timer = window.setInterval(emit, 250);
    return () => window.clearInterval(timer);
  }

  async capture(context: CaptureRequestContext): Promise<CaptureReceipt> {
    void context;
    return {
      captureId: '00000000-0000-0000-0000-000000000601',
      checksumSha256: 'a'.repeat(64),
      calibrationId: 'CAL-2026-0810-04',
      capturedAtUtc: '2026-08-12T10:00:05.000Z',
      inspectionId: '00000000-0000-0000-0000-000000000601',
      processingStatus: 'Completed',
    };
  }
}

export class LiveStationGateway implements StationGateway {
  constructor(private readonly baseUrl: string) {}

  async getReadiness(signal?: AbortSignal): Promise<StationReadiness> {
    const response = await fetch(`${this.baseUrl}/api/v1/health`, { signal: signal ?? null });
    if (!response.ok) throw new Error(`Station health failed: ${response.status}`);
    const health = await response.json() as { status: string; cameraStatus: string };
    return {
      ready: health.status.toLowerCase() === 'ok' && health.cameraStatus.toLowerCase() === 'ok',
      calibrationId: 'LIVE',
      cameraStatus: health.cameraStatus,
    };
  }

  subscribePreview(onFrame: (frame: PreviewFrame) => void, onError: () => void): () => void {
    const socketUrl = new URL('/api/v1/preview', this.baseUrl);
    socketUrl.protocol = socketUrl.protocol === 'https:' ? 'wss:' : 'ws:';
    const socket = new WebSocket(socketUrl);
    socket.addEventListener('message', (event) => onFrame(JSON.parse(String(event.data)) as PreviewFrame));
    socket.addEventListener('error', onError);
    return () => socket.close();
  }

  async capture(context: CaptureRequestContext, signal?: AbortSignal): Promise<CaptureReceipt> {
    const response = await fetch(`${this.baseUrl}/api/v1/captures`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ ...context, frameCount: 5 }),
      signal: signal ?? null,
    });
    if (!response.ok) throw new Error(`Station capture failed: ${response.status}`);
    return response.json() as Promise<CaptureReceipt>;
  }
}

export function createStationGateway(
  mode = import.meta.env.VITE_STATION_MODE,
  baseUrl = import.meta.env.VITE_STATION_API_URL,
): StationGateway {
  return mode === 'live' && baseUrl
    ? new LiveStationGateway(baseUrl.replace(/\/$/, ''))
    : new SimulatedStationGateway();
}
