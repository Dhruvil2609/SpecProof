import {
  DemoSpecProofClient,
  HttpSpecProofClient,
  demoDashboard,
  type Inspection,
  type SpecProofClient,
} from '@specproof/api-client';
import {
  AppShell,
  Button,
  Card,
  ErrorState,
  LanguageSwitcher,
  MeasurementOverlay,
  Metric,
  PageHeader,
  StatusBadge,
  ThemeToggle,
  formatDistance,
  formatPercent,
  formatTimestamp,
} from '@specproof/web-ui';
import { useQuery } from '@tanstack/react-query';
import {
  Camera,
  ClipboardCheck,
  Gauge,
  History,
  LayoutDashboard,
  ScanLine,
} from 'lucide-react';
import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type FormEvent,
  type ReactNode,
} from 'react';
import { useTranslation } from 'react-i18next';
import {
  Link,
  Navigate,
  Route,
  Routes,
  useNavigate,
  useParams,
} from 'react-router-dom';
import { createStationGateway, type PreviewFrame, type StationReadiness } from './stationGateway';
import './tokens.css';

interface AuthSession {
  readonly token: string;
  readonly tenantId: string;
  readonly role: string;
}

interface AuthContextValue {
  readonly session: AuthSession | null;
  readonly signIn: (tenantId: string, role: string) => Promise<void>;
  readonly signOut: () => void;
}

const authStorageKey = 'specproof-operator-session';
const AuthContext = createContext<AuthContextValue | null>(null);

function readSession(): AuthSession | null {
  const raw = window.sessionStorage.getItem(authStorageKey);
  if (raw === null) return null;
  try {
    const parsed: unknown = JSON.parse(raw);
    if (
      typeof parsed === 'object' &&
      parsed !== null &&
      'token' in parsed &&
      'tenantId' in parsed &&
      'role' in parsed &&
      typeof parsed.token === 'string' &&
      typeof parsed.tenantId === 'string' &&
      typeof parsed.role === 'string'
    ) {
      return parsed as AuthSession;
    }
  } catch {
    window.sessionStorage.removeItem(authStorageKey);
  }
  return null;
}

function AuthProvider({ children }: { readonly children: ReactNode }) {
  const [session, setSession] = useState<AuthSession | null>(readSession);

  const value = useMemo<AuthContextValue>(
    () => ({
      session,
      signIn: async (tenantId: string, role: string) => {
        const baseUrl = import.meta.env.VITE_PLATFORM_API_URL as string | undefined;
        let token = 'demo-token';
        if (baseUrl !== undefined && baseUrl.length > 0) {
          const query = new URLSearchParams({ tenantId, subject: 'operator-ui', role });
          const response = await fetch(`${baseUrl}/api/v1/auth/dev-token?${query.toString()}`);
          if (!response.ok) throw new Error('development_authentication_failed');
          const payload: unknown = await response.json();
          if (
            typeof payload !== 'object' ||
            payload === null ||
            !('token' in payload) ||
            typeof payload.token !== 'string'
          ) {
            throw new Error('development_authentication_invalid');
          }
          token = payload.token;
        }
        const nextSession = { token, tenantId, role };
        window.sessionStorage.setItem(authStorageKey, JSON.stringify(nextSession));
        setSession(nextSession);
      },
      signOut: () => {
        window.sessionStorage.removeItem(authStorageKey);
        setSession(null);
      },
    }),
    [session],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (context === null) throw new Error('useAuth must be used within AuthProvider');
  return context;
}

function RequireAuth({ children }: { readonly children: ReactNode }) {
  const { session } = useAuth();
  return session === null ? <Navigate to="/login" replace /> : children;
}

function LoginPage() {
  const { t } = useTranslation();
  const { session, signIn } = useAuth();
  const navigate = useNavigate();
  const [tenantId, setTenantId] = useState('11111111-1111-1111-1111-111111111111');
  const [role, setRole] = useState('operator');
  const [error, setError] = useState(false);

  if (session !== null) return <Navigate to="/" replace />;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      await signIn(tenantId, role);
      navigate('/');
    } catch {
      setError(true);
    }
  }

  return (
    <main className="login-page">
      <Card className="login-card">
        <div className="brand-lockup login-brand">
          <span className="brand-mark">S</span>
          <div><strong>{t('app.title')}</strong><small>{t('app.section')}</small></div>
        </div>
        <p className="eyebrow">{t('login.eyebrow')}</p>
        <h1>{t('login.title')}</h1>
        <p>{t('login.description')}</p>
        <form onSubmit={(event) => void submit(event)}>
          <label htmlFor="operator-tenant">{t('login.tenant')}</label>
          <select id="operator-tenant" value={tenantId} onChange={(event) => setTenantId(event.target.value)}>
            <option value="11111111-1111-1111-1111-111111111111">SpecProof Demo UK</option>
            <option value="22222222-2222-2222-2222-222222222222">SpecProof Demo APAC</option>
          </select>
          <label htmlFor="operator-role">{t('login.role')}</label>
          <select id="operator-role" value={role} onChange={(event) => setRole(event.target.value)}>
            <option value="operator">{t('login.operator')}</option>
            <option value="auditor">{t('login.auditor')}</option>
          </select>
          {error ? <p role="alert">{t('login.error')}</p> : null}
          <Button type="submit">{t('login.submit')}</Button>
        </form>
      </Card>
    </main>
  );
}

function createClient(token: () => string | null): SpecProofClient {
  const baseUrl = import.meta.env.VITE_PLATFORM_API_URL as string | undefined;
  return baseUrl === undefined || baseUrl.length === 0
    ? new DemoSpecProofClient()
    : new HttpSpecProofClient(baseUrl, token);
}

function OperatorShell() {
  const { t, i18n } = useTranslation();
  const { session } = useAuth();
  const client = useMemo(() => createClient(() => session?.token ?? null), [session]);
  const dashboard = useQuery({ queryKey: ['operator-dashboard', session?.tenantId], queryFn: ({ signal }) => client.getDashboard(signal) });
  const navigation = [
    { to: '/', label: t('navigation.dashboard'), icon: LayoutDashboard, end: true },
    { to: '/capture/select', label: t('navigation.capture'), icon: Camera },
    { to: '/history', label: t('navigation.history'), icon: History },
    { to: '/inspections/00000000-0000-0000-0000-000000000601', label: t('navigation.results'), icon: ClipboardCheck },
  ];
  const utilities = (
    <div className="utility-cluster">
      <LanguageSwitcher
        label={t('app.language')}
        value={i18n.language}
        options={[
          { value: 'en', label: 'EN' },
          { value: 'qps-ploc', label: 'QA' },
        ]}
        onChange={(value) => void i18n.changeLanguage(value)}
      />
      <ThemeToggle darkLabel={t('app.theme.dark')} lightLabel={t('app.theme.light')} />
    </div>
  );

  return (
    <AppShell productLabel={t('app.title')} sectionLabel={t('app.section')} navigation={navigation} utilities={utilities}>
      {dashboard.isError ? (
        <ErrorState title={t('common.error')} detail={t('common.error')} retryLabel={t('common.retry')} onRetry={() => void dashboard.refetch()} />
      ) : (
        <Routes>
          <Route index element={<DashboardPage inspections={dashboard.data?.inspections ?? demoDashboard.inspections} />} />
          <Route path="capture/select" element={<CaptureSelectionPage />} />
          <Route path="capture/live" element={<CapturePreviewPage />} />
          <Route path="capture/processing" element={<ProcessingPage />} />
          <Route path="inspections/:id" element={<InspectionPage inspections={dashboard.data?.inspections ?? demoDashboard.inspections} />} />
          <Route path="inspections/:id/review" element={<ReviewPage client={client} />} />
          <Route path="history" element={<HistoryPage inspections={dashboard.data?.inspections ?? demoDashboard.inspections} />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      )}
    </AppShell>
  );
}

function DashboardPage({ inspections }: { readonly inspections: readonly Inspection[] }) {
  const { t } = useTranslation();
  const passCount = inspections.filter((inspection) => inspection.status === 'PASS').length;
  const reviewCount = inspections.filter((inspection) => inspection.status === 'REVIEW').length;
  return (
    <>
      <PageHeader eyebrow={t('dashboard.eyebrow')} title={t('dashboard.title')} description={t('dashboard.description')} actions={<Link className="button" to="/capture/select">{t('navigation.capture')}</Link>} />
      <div className="metrics-grid">
        <Metric label={t('dashboard.today')} value={String(inspections.length)} detail={t('dashboard.order')} tone="amber" />
        <Metric label={t('dashboard.pass_rate')} value={formatPercent(passCount / inspections.length)} detail={t('status.pass')} tone="pass" />
        <Metric label={t('dashboard.review_queue')} value={String(reviewCount)} detail={t('status.review')} tone="fail" />
        <Metric label={t('dashboard.station')} value="ONLINE" detail="STN-LON-01" tone="cyan" />
      </div>
      <Card className="table-card">
        <h2>{t('dashboard.recent')}</h2>
        <InspectionTable inspections={inspections} />
      </Card>
    </>
  );
}

function InspectionTable({ inspections }: { readonly inspections: readonly Inspection[] }) {
  const { t } = useTranslation();
  return (
    <div className="table-scroll">
      <table>
        <thead><tr><th>{t('dashboard.order')}</th><th>{t('dashboard.style')}</th><th>{t('dashboard.size')}</th><th>{t('dashboard.time')}</th><th>{t('dashboard.status')}</th><th><span className="sr-only">{t('dashboard.open')}</span></th></tr></thead>
        <tbody>
          {inspections.map((inspection) => (
            <tr key={inspection.id}>
              <td className="mono">{inspection.orderCode}</td><td>{inspection.styleCode}</td><td>{inspection.sizeCode}</td>
              <td><time dateTime={inspection.capturedAtUtc}>{formatTimestamp(inspection.capturedAtUtc)}</time></td>
              <td><StatusBadge status={inspection.status} label={t(`status.${inspection.status.toLowerCase()}`)} /></td>
              <td><Link to={`/inspections/${inspection.id}`}>{t('dashboard.open')}</Link></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function CaptureSelectionPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [context, setContext] = useState({ order: 'PO-24081', style: 'SP-TEE-01', size: 'M', batch: 'B-0810-A' });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    window.sessionStorage.setItem('specproof-capture-context', JSON.stringify(context));
    navigate('/capture/live');
  }

  return (
    <>
      <PageHeader eyebrow={t('capture.eyebrow')} title={t('capture.title')} description={t('capture.description')} />
      <Card className="form-card">
        <form className="context-grid" onSubmit={submit}>
          <label htmlFor="capture-order">{t('capture.order')}<select id="capture-order" value={context.order} onChange={(event) => setContext({ ...context, order: event.target.value })}><option>PO-24081</option><option>PO-24079</option></select></label>
          <label htmlFor="capture-style">{t('capture.style')}<select id="capture-style" value={context.style} onChange={(event) => setContext({ ...context, style: event.target.value })}><option>SP-TEE-01</option><option>CORE-02</option></select></label>
          <label htmlFor="capture-size">{t('capture.size')}<select id="capture-size" value={context.size} onChange={(event) => setContext({ ...context, size: event.target.value })}><option>S</option><option>M</option><option>L</option><option>XL</option></select></label>
          <label htmlFor="capture-batch">{t('capture.batch')}<select id="capture-batch" value={context.batch} onChange={(event) => setContext({ ...context, batch: event.target.value })}><option>B-0810-A</option><option>B-0810-B</option></select></label>
          <Button type="submit">{t('capture.continue')}</Button>
        </form>
      </Card>
    </>
  );
}

function CapturePreviewPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [depth, setDepth] = useState(true);
  const [recapture, setRecapture] = useState(false);
  const [readiness, setReadiness] = useState<StationReadiness | null>(null);
  const [frame, setFrame] = useState<PreviewFrame | null>(null);
  const gateway = useMemo(() => createStationGateway(), []);

  useEffect(() => {
    const controller = new AbortController();
    void gateway.getReadiness(controller.signal).then(setReadiness).catch(() => setRecapture(true));
    const unsubscribe = gateway.subscribePreview(setFrame, () => setRecapture(true));
    return () => {
      controller.abort();
      unsubscribe();
    };
  }, [gateway]);

  async function triggerCapture() {
    try {
      await gateway.capture();
      navigate('/capture/processing');
    } catch {
      setRecapture(true);
    }
  }

  if (recapture) {
    return (
      <>
        <PageHeader eyebrow={t('capture.recapture')} title={t('capture.recapture')} description={t('capture.recapture_detail')} />
        <Card className="recapture-card"><ScanLine aria-hidden="true" size={60} /><Button onClick={() => setRecapture(false)}>{t('capture.try_again')}</Button></Card>
      </>
    );
  }

  return (
    <>
      <PageHeader eyebrow={t('capture.preview_eyebrow')} title={t('capture.preview_title')} description={t('capture.preview_description')} />
      <div className="capture-layout">
        <Card className={`preview-card ${depth ? 'depth-mode' : ''}`}>
          <div className="preview-toolbar"><button className={!depth ? 'active' : ''} onClick={() => setDepth(false)}>{t('capture.rgb')}</button><button className={depth ? 'active' : ''} onClick={() => setDepth(true)}>{t('capture.depth')}</button></div>
          <div className="camera-frame"><div className="capture-zone"><div className="preview-garment" /></div><span className="frame-label">{frame?.colorWidth ?? 1280} × {frame?.colorHeight ?? 720} / #{frame?.sequence ?? 0}</span></div>
        </Card>
        <div className="capture-controls">
          <Card><StatusBadge status={readiness?.ready ? 'PASS' : 'REVIEW'} label={readiness?.ready ? t('capture.ready') : t('status.review')} /><p>{t('capture.preview_description')}</p></Card>
          <Card><StatusBadge status="PASS" label={t('capture.calibration')} /><p>{readiness?.calibrationId ?? '—'}</p></Card>
          <Button disabled={!readiness?.ready} onClick={() => void triggerCapture()}>{t('capture.trigger')}</Button>
          <Button className="button-secondary" onClick={() => setRecapture(true)}>{t('capture.recapture')}</Button>
        </div>
      </div>
    </>
  );
}

function ProcessingPage() {
  const { t } = useTranslation();
  const [step, setStep] = useState(0);
  const steps = ['processing.capture', 'processing.surface', 'processing.measure', 'processing.evidence'] as const;

  useEffect(() => {
    const timer = window.setInterval(() => setStep((current) => Math.min(current + 1, steps.length)), 260);
    return () => window.clearInterval(timer);
  }, [steps.length]);

  return (
    <>
      <PageHeader eyebrow={t('processing.eyebrow')} title={t('processing.title')} description={t('processing.description')} />
      <Card className="processing-card">
        <div className="processing-orbit"><Gauge aria-hidden="true" /><strong>{Math.round((step / steps.length) * 100)}%</strong></div>
        <ol>{steps.map((key, index) => <li key={key} className={index < step ? 'complete' : index === step ? 'active' : ''}><span>{index + 1}</span>{t(key)}</li>)}</ol>
        {step === steps.length ? <Link className="button" to="/inspections/00000000-0000-0000-0000-000000000601">{t('processing.complete')}</Link> : null}
      </Card>
    </>
  );
}

function InspectionPage({ inspections }: { readonly inspections: readonly Inspection[] }) {
  const { t } = useTranslation();
  const { id } = useParams();
  const inspection = inspections.find((candidate) => candidate.id === id) ?? inspections[0];
  if (inspection === undefined) return <Navigate to="/history" replace />;
  return (
    <>
      <PageHeader eyebrow={t('result.eyebrow')} title={t('result.title')} actions={<StatusBadge status={inspection.status} label={t(`status.${inspection.status.toLowerCase()}`)} />} />
      <div className="result-layout">
        <MeasurementOverlay label={t('result.overlay')} lines={inspection.measurements.map((measurement) => ({ id: measurement.pomId, label: measurement.canonicalName, status: measurement.status, points: measurement.overlay }))} />
        <Card className="result-summary"><p className="eyebrow">{inspection.orderCode} / {inspection.styleCode} / {inspection.sizeCode}</p><h2>{inspection.stationCode}</h2><time dateTime={inspection.capturedAtUtc}>{formatTimestamp(inspection.capturedAtUtc)}</time><code>{inspection.evidenceHash}</code><div className="page-actions"><Link className="button" to={`/inspections/${inspection.id}/review`}>{t('result.review')}</Link><Link className="button button-secondary" to="/capture/select">{t('result.new')}</Link></div></Card>
      </div>
      <Card className="table-card"><div className="table-scroll"><table><thead><tr><th>{t('result.pom')}</th><th>{t('result.measured')}</th><th>{t('result.target')}</th><th>{t('result.deviation')}</th><th>{t('result.confidence')}</th><th>{t('dashboard.status')}</th></tr></thead><tbody>{inspection.measurements.map((measurement) => <tr key={measurement.pomId}><td>{measurement.canonicalName}</td><td>{formatDistance(measurement.measuredValueMm, 'metric')}</td><td>{formatDistance(measurement.targetValueMm, 'metric')}</td><td className={measurement.status === 'FAIL' ? 'fail-text' : ''}>{formatDistance(measurement.deviationMm, 'metric')}</td><td>{formatPercent(measurement.confidence)}</td><td><StatusBadge status={measurement.status} label={t(`status.${measurement.status.toLowerCase()}`)} /></td></tr>)}</tbody></table></div></Card>
    </>
  );
}

function ReviewPage({ client }: { readonly client: SpecProofClient }) {
  const { t } = useTranslation();
  const { id = '' } = useParams();
  const [note, setNote] = useState('');
  const [saved, setSaved] = useState(false);
  async function save(outcome: string) {
    await client.reviewInspection(id, outcome, note);
    setSaved(true);
  }
  return (
    <>
      <PageHeader eyebrow={t('review.eyebrow')} title={t('review.title')} description={t('review.description')} />
      <Card className="review-card"><label htmlFor="review-note">{t('review.note')}</label><textarea id="review-note" rows={6} placeholder={t('review.note_placeholder')} value={note} onChange={(event) => setNote(event.target.value)} /><div className="review-actions"><Button onClick={() => void save('PASS')}>{t('review.pass')}</Button><Button className="button-secondary" onClick={() => void save('FAIL')}>{t('review.fail')}</Button><Button className="button-secondary" onClick={() => void save('INVALID')}>{t('review.invalid')}</Button><Button className="button-secondary" onClick={() => void save('RECAPTURE')}>{t('review.recapture')}</Button></div>{saved ? <p role="status" className="success-message">{t('review.saved')}</p> : null}</Card>
    </>
  );
}

function HistoryPage({ inspections }: { readonly inspections: readonly Inspection[] }) {
  const { t } = useTranslation();
  const [search, setSearch] = useState('');
  const normalized = search.toLowerCase();
  const filtered = inspections.filter((inspection) => [inspection.orderCode, inspection.styleCode, inspection.stationCode].some((value) => value.toLowerCase().includes(normalized)));
  return (
    <>
      <PageHeader eyebrow={t('history.eyebrow')} title={t('history.title')} description={t('history.description')} />
      <label className="search-field" htmlFor="history-search"><span className="sr-only">{t('history.search')}</span><input id="history-search" type="search" placeholder={t('history.search')} value={search} onChange={(event) => setSearch(event.target.value)} /></label>
      <Card className="table-card"><InspectionTable inspections={filtered} /></Card>
    </>
  );
}

export function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/*" element={<RequireAuth><OperatorShell /></RequireAuth>} />
      </Routes>
    </AuthProvider>
  );
}
