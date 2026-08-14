import { afterEach, describe, expect, it, vi } from 'vitest';

import { createStationGateway, SimulatedStationGateway } from './stationGateway';

describe('station gateway', () => {
  afterEach(() => vi.useRealTimers());

  it('defaults to deterministic simulated readiness and capture', async () => {
    const gateway = createStationGateway(undefined, undefined);

    expect(gateway).toBeInstanceOf(SimulatedStationGateway);
    await expect(gateway.getReadiness()).resolves.toMatchObject({ ready: true });
    await expect(gateway.capture()).resolves.toMatchObject({ calibrationId: 'CAL-2026-0810-04' });
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
