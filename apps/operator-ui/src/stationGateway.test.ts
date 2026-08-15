import { afterEach, describe, expect, it, vi } from 'vitest';

import { createStationGateway, SimulatedStationGateway } from './stationGateway';

describe('station gateway', () => {
  afterEach(() => vi.useRealTimers());

  it('defaults to deterministic simulated readiness and capture', async () => {
    const gateway = createStationGateway(undefined, undefined);

    expect(gateway).toBeInstanceOf(SimulatedStationGateway);
    await expect(gateway.getReadiness()).resolves.toMatchObject({ ready: true });
    await expect(gateway.capture(captureContext())).resolves.toMatchObject({
      calibrationId: 'CAL-2026-0810-04',
      inspectionId: '00000000-0000-0000-0000-000000000601',
    });
  });

  it('streams deterministic preview sequence values', () => {
    vi.useFakeTimers();
    const gateway = new SimulatedStationGateway();
    const sequences: number[] = [];

    const unsubscribe = gateway.subscribePreview((frame) => sequences.push(frame.sequence), () => undefined);
    vi.advanceTimersByTime(500);
    unsubscribe();

    expect(sequences).toEqual([0, 1, 2]);
  });
});

function captureContext() {
  return {
    tenantId: '11111111-1111-1111-1111-111111111111',
    stationId: '33333333-3333-3333-3333-333333333333',
    stationCode: 'STN-LON-01',
    cameraSerial: 'MOCK-001',
    inspectionId: '00000000-0000-0000-0000-000000000601',
    orderCode: 'PO-24081',
    styleCode: 'SP-TEE-01',
    sizeCode: 'M',
    batchId: '44444444-4444-4444-4444-444444444441',
    techPackId: '55555555-5555-5555-5555-555555555555',
    techPackVersion: 1,
  };
}
