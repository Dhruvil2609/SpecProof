import type { SpecProofClient } from './client';
import type { DashboardData, Inspection, Measurement } from './models';

const measurements: readonly Measurement[] = [
  { pomId: 'chest_width', canonicalName: 'Chest width', measuredValueMm: 501.2, targetValueMm: 500, lowerToleranceMm: 5, upperToleranceMm: 5, deviationMm: 1.2, confidence: 0.98, status: 'PASS', overlay: [{ x: 31, y: 46 }, { x: 69, y: 46 }] },
  { pomId: 'body_length', canonicalName: 'Body length', measuredValueMm: 704.6, targetValueMm: 700, lowerToleranceMm: 6, upperToleranceMm: 6, deviationMm: 4.6, confidence: 0.96, status: 'PASS', overlay: [{ x: 50, y: 20 }, { x: 50, y: 88 }] },
  { pomId: 'shoulder_width', canonicalName: 'Shoulder width', measuredValueMm: 432.4, targetValueMm: 420, lowerToleranceMm: 5, upperToleranceMm: 5, deviationMm: 12.4, confidence: 0.95, status: 'FAIL', overlay: [{ x: 35, y: 22 }, { x: 65, y: 22 }] },
  { pomId: 'sleeve_opening', canonicalName: 'Sleeve opening', measuredValueMm: 176.8, targetValueMm: 175, lowerToleranceMm: 4, upperToleranceMm: 4, deviationMm: 1.8, confidence: 0.72, status: 'REVIEW', overlay: [{ x: 20, y: 32 }, { x: 31, y: 40 }] },
];

const inspections: readonly Inspection[] = [
  {
    id: '00000000-0000-0000-0000-000000000601',
    captureId: 'capture-601',
    orderCode: 'PO-24081',
    styleCode: 'SP-TEE-01',
    sizeCode: 'M',
    stationCode: 'STN-LON-01',
    capturedAtUtc: '2026-08-10T12:40:00Z',
    status: 'FAIL',
    evidenceHash: 'a4b8d48f75b91f0e6f3da357f56df25077225982a9df623e0a772a85f05fe948',
    measurements,
  },
  {
    id: '00000000-0000-0000-0000-000000000602',
    captureId: 'capture-602',
    orderCode: 'PO-24081',
    styleCode: 'SP-TEE-01',
    sizeCode: 'L',
    stationCode: 'STN-LON-01',
    capturedAtUtc: '2026-08-10T12:32:00Z',
    status: 'PASS',
    evidenceHash: 'b4b8d48f75b91f0e6f3da357f56df25077225982a9df623e0a772a85f05fe949',
    measurements: measurements.slice(0, 2).map((measurement) => ({ ...measurement, status: 'PASS' })),
  },
  {
    id: '00000000-0000-0000-0000-000000000603',
    captureId: 'capture-603',
    orderCode: 'PO-24079',
    styleCode: 'CORE-02',
    sizeCode: 'S',
    stationCode: 'STN-LON-02',
    capturedAtUtc: '2026-08-10T12:21:00Z',
    status: 'REVIEW',
    evidenceHash: 'c4b8d48f75b91f0e6f3da357f56df25077225982a9df623e0a772a85f05fe950',
    measurements: measurements.slice(3),
  },
];

export const demoDashboard: DashboardData = {
  inspections,
  stations: [
    { id: 'station-1', code: 'STN-LON-01', factory: 'London Sample Room', status: 'ONLINE', cameraStatus: 'Ready', storageStatus: 'Healthy', clockStatus: 'Synchronized', queueDepth: 0, calibrationExpiresAtUtc: '2026-08-11T06:00:00Z', softwareVersion: '1.4.2' },
    { id: 'station-2', code: 'STN-LON-02', factory: 'London Sample Room', status: 'WARNING', cameraStatus: 'Ready', storageStatus: '82% used', clockStatus: 'Synchronized', queueDepth: 3, calibrationExpiresAtUtc: '2026-08-10T15:00:00Z', softwareVersion: '1.4.1' },
    { id: 'station-3', code: 'STN-DHA-04', factory: 'Dhaka Line 4', status: 'OFFLINE', cameraStatus: 'Unavailable', storageStatus: 'Unknown', clockStatus: 'Unknown', queueDepth: 14, calibrationExpiresAtUtc: '2026-08-09T04:00:00Z', softwareVersion: '1.3.9' },
  ],
  techPacks: [
    { id: 'tech-1', brand: 'North Standard', styleCode: 'SP-TEE-01', category: 'T-shirt', version: 4, status: 'APPROVED', hash: '671a4d…f501', mappings: [{ originalTerm: '1/2 Chest', canonicalPomId: 'chest_width', status: 'APPROVED' }, { originalTerm: 'HPS Length', canonicalPomId: 'body_length', status: 'APPROVED' }] },
    { id: 'tech-2', brand: 'Common Form', styleCode: 'CORE-02', category: 'T-shirt', version: 2, status: 'MAPPING_REQUIRED', hash: 'd7231e…aa10', mappings: [{ originalTerm: 'Across Front', canonicalPomId: null, status: 'AMBIGUOUS' }, { originalTerm: 'Sleeve Hem', canonicalPomId: 'sleeve_opening', status: 'APPROVED' }] },
  ],
  users: [
    { id: 'user-1', name: 'Maya Chen', email: 'maya@example.test', role: 'Administrator', active: true },
    { id: 'user-2', name: 'Ibrahim Rahman', email: 'ibrahim@example.test', role: 'Operator', active: true },
    { id: 'user-3', name: 'Sofia Alvarez', email: 'sofia@example.test', role: 'Auditor', active: true },
  ],
  evidence: inspections.map((inspection, index) => ({
    id: `evidence-${index + 1}`,
    inspectionId: inspection.id,
    recordHash: inspection.evidenceHash,
    previousHash: index === 0 ? null : inspections[index - 1]?.evidenceHash ?? null,
    signatureAlgorithm: 'HMAC-SHA256',
    signatureValid: true,
    modelVersion: 'tshirt-landmarks-1.0.0',
    ontologyVersion: '1.0.0',
    compilerVersion: 'phase-4-compiler-v1',
    producedAtUtc: inspection.capturedAtUtc,
  })),
};

export class DemoSpecProofClient implements SpecProofClient {
  public async getDashboard(): Promise<DashboardData> {
    return Promise.resolve(demoDashboard);
  }

  public async getInspection(id: string): Promise<Inspection> {
    const inspection = demoDashboard.inspections.find((candidate) => candidate.id === id);
    if (inspection === undefined) throw new Error('Inspection not found');
    return Promise.resolve(inspection);
  }

  public async reviewInspection(): Promise<void> {
    return Promise.resolve();
  }
}
