export type InspectionStatus = 'PASS' | 'FAIL' | 'REVIEW' | 'INVALID' | 'PENDING';

export interface Measurement {
  readonly pomId: string;
  readonly canonicalName: string;
  readonly measuredValueMm: number;
  readonly targetValueMm: number;
  readonly lowerToleranceMm: number;
  readonly upperToleranceMm: number;
  readonly deviationMm: number;
  readonly confidence: number;
  readonly status: InspectionStatus;
  readonly overlay: readonly { readonly x: number; readonly y: number }[];
}

export interface Inspection {
  readonly id: string;
  readonly captureId: string;
  readonly orderCode: string;
  readonly styleCode: string;
  readonly sizeCode: string;
  readonly stationCode: string;
  readonly capturedAtUtc: string;
  readonly status: InspectionStatus;
  readonly evidenceHash: string;
  readonly measurements: readonly Measurement[];
}

export interface Station {
  readonly id: string;
  readonly code: string;
  readonly factory: string;
  readonly status: 'ONLINE' | 'WARNING' | 'OFFLINE';
  readonly cameraStatus: string;
  readonly storageStatus: string;
  readonly clockStatus: string;
  readonly queueDepth: number;
  readonly calibrationExpiresAtUtc: string;
  readonly softwareVersion: string;
}

export interface CaptureContext {
  readonly orderCode: string;
  readonly styleCode: string;
  readonly sizeCode: string;
  readonly batchCode: string;
}

export interface TechPack {
  readonly id: string;
  readonly brand: string;
  readonly styleCode: string;
  readonly category: string;
  readonly version: number;
  readonly status: 'APPROVED' | 'MAPPING_REQUIRED' | 'DRAFT';
  readonly hash: string;
  readonly mappings: readonly {
    readonly originalTerm: string;
    readonly canonicalPomId: string | null;
    readonly status: 'APPROVED' | 'AMBIGUOUS' | 'UNKNOWN';
  }[];
}

export interface UserAccount {
  readonly id: string;
  readonly name: string;
  readonly email: string;
  readonly role: string;
  readonly active: boolean;
}

export interface Evidence {
  readonly id: string;
  readonly inspectionId: string;
  readonly recordHash: string;
  readonly previousHash: string | null;
  readonly signatureAlgorithm: string;
  readonly signatureValid: boolean;
  readonly modelVersion: string;
  readonly ontologyVersion: string;
  readonly compilerVersion: string;
  readonly producedAtUtc: string;
}

export interface DashboardData {
  readonly inspections: readonly Inspection[];
  readonly stations: readonly Station[];
  readonly techPacks: readonly TechPack[];
  readonly users: readonly UserAccount[];
  readonly evidence: readonly Evidence[];
}

export interface ApiProblem {
  readonly type?: string;
  readonly title?: string;
  readonly status: number;
  readonly detail?: string;
}
