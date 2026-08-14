import { DemoSpecProofClient, demoDashboard, type DashboardData, type Station } from '@specproof/api-client';
import {
  AppShell,
  Button,
  Card,
  LanguageSwitcher,
  Metric,
  PageHeader,
  StatusBadge,
  ThemeToggle,
  formatPercent,
  formatTimestamp,
} from '@specproof/web-ui';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { jsPDF } from 'jspdf';
import {
  BarChart3,
  FileCheck2,
  Gauge,
  LayoutDashboard,
  Settings,
  ShieldCheck,
  Shirt,
  Users,
} from 'lucide-react';
import { useMemo, useState, type FormEvent, type ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { Link, Navigate, Route, Routes, useNavigate, useParams } from 'react-router-dom';
import './tokens.css';

const adminSessionKey = 'specproof-admin-session';

interface AdminSession {
  readonly token: string;
  readonly tenantId: string;
  readonly role: string;
}

function readAdminSession(): AdminSession | null {
  const value = window.sessionStorage.getItem(adminSessionKey);
  if (value === null) return null;
  try {
    return JSON.parse(value) as AdminSession;
  } catch {
    window.sessionStorage.removeItem(adminSessionKey);
    return null;
  }
}

async function createDevelopmentSession(tenantId: string, role: string): Promise<AdminSession> {
  const baseUrl = import.meta.env.VITE_PLATFORM_API_URL;
  let token = 'demo-token';
  if (baseUrl !== undefined && baseUrl.length > 0) {
    const query = new URLSearchParams({ tenantId, subject: 'admin-ui', role });
    const response = await fetch(`${baseUrl}/api/v1/auth/dev-token?${query.toString()}`);
    if (!response.ok) throw new Error('development_authentication_failed');
    const payload = await response.json() as { token?: unknown };
    if (typeof payload.token !== 'string') throw new Error('development_authentication_invalid');
    token = payload.token;
  }
  return { token, tenantId, role };
}

function hasSession(): boolean {
  return readAdminSession() !== null;
}

function LoginPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [role, setRole] = useState('admin');
  const [tenantId, setTenantId] = useState('11111111-1111-1111-1111-111111111111');
  const [denied, setDenied] = useState(false);

  if (hasSession()) return <Navigate to="/" replace />;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (role !== 'admin' && role !== 'auditor') {
      setDenied(true);
      return;
    }
    try {
      const session = await createDevelopmentSession(tenantId, role);
      window.sessionStorage.setItem(adminSessionKey, JSON.stringify(session));
      navigate('/');
    } catch {
      setDenied(true);
    }
  }

  return (
    <main className="admin-login">
      <Card className="admin-login-card">
        <div className="brand-lockup login-brand"><span className="brand-mark">S</span><div><strong>{t('app.title')}</strong><small>{t('app.section')}</small></div></div>
        <p className="eyebrow">{t('login.eyebrow')}</p>
        <h1>{t('login.title')}</h1>
        <p>{t('login.description')}</p>
        <form onSubmit={(event) => void submit(event)}>
          <label htmlFor="admin-tenant">{t('login.tenant')}</label>
          <select id="admin-tenant" value={tenantId} onChange={(event) => setTenantId(event.target.value)}><option value="11111111-1111-1111-1111-111111111111">SpecProof Demo UK</option><option value="22222222-2222-2222-2222-222222222222">SpecProof Demo APAC</option></select>
          <label htmlFor="admin-role">{t('login.role')}</label>
          <select id="admin-role" value={role} onChange={(event) => setRole(event.target.value)}>
            <option value="admin">{t('login.admin')}</option>
            <option value="auditor">{t('login.auditor')}</option>
            <option value="operator">Operator</option>
          </select>
          {denied ? <p role="alert">{t('login.denied')}</p> : null}
          <Button type="submit">{t('login.submit')}</Button>
        </form>
      </Card>
    </main>
  );
}

function RequireAdmin({ children }: { readonly children: ReactNode }) {
  return hasSession() ? children : <Navigate to="/login" replace />;
}

function AdminShell() {
  const { t, i18n } = useTranslation();
  const client = useMemo(() => new DemoSpecProofClient(), []);
  const dashboard = useQuery({ queryKey: ['admin-dashboard'], queryFn: () => client.getDashboard() });
  const data = dashboard.data ?? demoDashboard;
  const session = readAdminSession();
  const navigation = [
    { to: '/', label: t('navigation.dashboard'), icon: LayoutDashboard, end: true },
    ...(session?.role === 'admin' ? [
      { to: '/stations', label: t('navigation.stations'), icon: Gauge },
      { to: '/specs', label: t('navigation.specs'), icon: FileCheck2 },
      { to: '/categories', label: t('navigation.categories'), icon: Shirt },
      { to: '/users', label: t('navigation.users'), icon: Users },
      { to: '/roles', label: t('navigation.roles'), icon: ShieldCheck },
    ] : []),
    { to: '/reports', label: t('navigation.reports'), icon: BarChart3 },
    ...(session?.role === 'admin' ? [{ to: '/settings', label: t('navigation.settings'), icon: Settings }] : []),
  ];
  const utilities = (
    <div className="utility-cluster">
      <LanguageSwitcher label={t('app.language')} value={i18n.language} options={[{ value: 'en', label: 'EN' }, { value: 'qps-ploc', label: 'QA' }]} onChange={(value) => void i18n.changeLanguage(value)} />
      <ThemeToggle darkLabel={t('app.theme.dark')} lightLabel={t('app.theme.light')} />
    </div>
  );

  return (
    <AppShell productLabel={t('app.title')} sectionLabel={t('app.section')} navigation={navigation} utilities={utilities}>
      <Routes>
        <Route index element={<ControlRoom data={data} />} />
        <Route path="stations" element={<AdminOnly><StationsPage data={data} /></AdminOnly>} />
        <Route path="stations/:id" element={<AdminOnly><StationDetailPage data={data} /></AdminOnly>} />
        <Route path="specs" element={<AdminOnly><SpecsPage data={data} /></AdminOnly>} />
        <Route path="specs/import" element={<AdminOnly><SpecImportPage /></AdminOnly>} />
        <Route path="specs/:id/versions/:version" element={<AdminOnly><SpecDetailPage data={data} /></AdminOnly>} />
        <Route path="categories" element={<AdminOnly><CategoriesPage /></AdminOnly>} />
        <Route path="users" element={<AdminOnly><UsersPage data={data} /></AdminOnly>} />
        <Route path="roles" element={<AdminOnly><RolesPage /></AdminOnly>} />
        <Route path="reports" element={<ReportsPage data={data} />} />
        <Route path="evidence/:id" element={<EvidencePage data={data} />} />
        <Route path="settings" element={<AdminOnly><SettingsPage /></AdminOnly>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppShell>
  );
}

function AdminOnly({ children }: { readonly children: ReactNode }) {
  return readAdminSession()?.role === 'admin' ? children : <Navigate to="/reports" replace />;
}

function ControlRoom({ data }: { readonly data: DashboardData }) {
  const { t } = useTranslation();
  const online = data.stations.filter((station) => station.status === 'ONLINE').length;
  const warning = data.stations.filter((station) => station.status !== 'ONLINE').length;
  const pass = data.inspections.filter((inspection) => inspection.status === 'PASS').length;
  return (
    <>
      <PageHeader eyebrow={t('dashboard.eyebrow')} title={t('dashboard.title')} description={t('dashboard.description')} />
      <div className="metrics-grid">
        <Metric label={t('dashboard.online')} value={String(online)} detail={String(data.stations.length)} tone="cyan" />
        <Metric label={t('dashboard.warning')} value={String(warning)} detail={t('status.warning')} tone="fail" />
        <Metric label={t('dashboard.inspections')} value={String(data.inspections.length)} detail="UTC" tone="amber" />
        <Metric label={t('dashboard.pass_rate')} value={formatPercent(pass / data.inspections.length)} detail={t('status.pass')} tone="pass" />
      </div>
      <Card className="admin-table-card"><h2>{t('dashboard.activity')}</h2><StationTable stations={data.stations} /></Card>
    </>
  );
}

function StationTable({ stations }: { readonly stations: readonly Station[] }) {
  const { t } = useTranslation();
  return (
    <div className="table-scroll"><table><thead><tr><th>{t('station.code')}</th><th>{t('station.factory')}</th><th>{t('station.camera')}</th><th>{t('station.storage')}</th><th>{t('station.queue')}</th><th>{t('station.status')}</th><th /></tr></thead><tbody>{stations.map((station) => <tr key={station.id}><td className="mono">{station.code}</td><td>{station.factory}</td><td>{station.cameraStatus}</td><td>{station.storageStatus}</td><td>{station.queueDepth}</td><td><StationBadge station={station} /></td><td><Link to={`/stations/${station.id}`}>{t('station.open')}</Link></td></tr>)}</tbody></table></div>
  );
}

function StationBadge({ station }: { readonly station: Station }) {
  const { t } = useTranslation();
  const mapped = station.status === 'ONLINE' ? 'PASS' : station.status === 'WARNING' ? 'REVIEW' : 'INVALID';
  return <StatusBadge status={mapped} label={t(`status.${station.status.toLowerCase()}`)} />;
}

function StationsPage({ data }: { readonly data: DashboardData }) {
  const { t } = useTranslation();
  return <><PageHeader eyebrow={t('station.eyebrow')} title={t('station.title')} description={t('station.description')} /><Card className="admin-table-card"><StationTable stations={data.stations} /></Card></>;
}

function StationDetailPage({ data }: { readonly data: DashboardData }) {
  const { t } = useTranslation();
  const { id } = useParams();
  const station = data.stations.find((candidate) => candidate.id === id) ?? data.stations[0];
  const [saved, setSaved] = useState(false);
  if (station === undefined) return <Navigate to="/stations" replace />;
  return (
    <>
      <PageHeader eyebrow={t('station.eyebrow')} title={station.code} description={station.factory} actions={<StationBadge station={station} />} />
      <div className="metrics-grid">
        <Metric label={t('station.camera')} value={station.cameraStatus} tone="cyan" />
        <Metric label={t('station.storage')} value={station.storageStatus} tone="amber" />
        <Metric label={t('station.queue')} value={String(station.queueDepth)} tone="fail" />
        <Metric label={t('station.version')} value={station.softwareVersion} />
      </div>
      <Card className="editor-card"><h2>{t('station.configuration')}</h2><p>{t('station.configuration_help')}</p><label htmlFor="station-config">JSON</label><textarea id="station-config" rows={10} defaultValue={'{\n  "previewDepth": true,\n  "captureFrameCount": 3,\n  "unitSystem": "metric"\n}'} /><Button onClick={() => setSaved(true)}>{t('station.save')}</Button>{saved ? <p role="status" className="success-message">{t('station.saved')}</p> : null}</Card>
    </>
  );
}

function SpecsPage({ data }: { readonly data: DashboardData }) {
  const { t } = useTranslation();
  return (
    <>
      <PageHeader eyebrow={t('spec.eyebrow')} title={t('spec.title')} description={t('spec.description')} actions={<Link className="button" to="/specs/import">{t('spec.import')}</Link>} />
      <Card className="admin-table-card"><div className="table-scroll"><table><thead><tr><th>{t('spec.brand')}</th><th>{t('spec.style')}</th><th>{t('spec.category')}</th><th>{t('spec.version')}</th><th>{t('spec.status')}</th><th>{t('spec.hash')}</th><th /></tr></thead><tbody>{data.techPacks.map((pack) => <tr key={pack.id}><td>{pack.brand}</td><td className="mono">{pack.styleCode}</td><td>{pack.category}</td><td>v{pack.version}</td><td><StatusBadge status={pack.status === 'APPROVED' ? 'PASS' : 'REVIEW'} label={t(`status.${pack.status.toLowerCase()}`)} /></td><td className="mono">{pack.hash}</td><td><Link to={`/specs/${pack.id}/versions/${pack.version}`}>{t('spec.open')}</Link></td></tr>)}</tbody></table></div></Card>
    </>
  );
}

function SpecImportPage() {
  const { t } = useTranslation();
  const [parsed, setParsed] = useState(false);
  function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); setParsed(true); }
  return (
    <>
      <PageHeader eyebrow={t('spec.eyebrow')} title={t('spec.upload_title')} description={t('spec.upload_help')} />
      <Card className="editor-card"><form onSubmit={submit}><label htmlFor="tech-pack-file">{t('spec.file')}</label><input id="tech-pack-file" type="file" accept=".csv,.xlsx,.json" required /><Button type="submit">{t('spec.upload')}</Button></form>{parsed ? <div className="mapping-preview"><StatusBadge status="REVIEW" label={t('status.mapping_required')} /><p>2 canonical mappings / 1 ambiguous term</p></div> : null}</Card>
    </>
  );
}

function SpecDetailPage({ data }: { readonly data: DashboardData }) {
  const { t } = useTranslation();
  const { id } = useParams();
  const pack = data.techPacks.find((candidate) => candidate.id === id) ?? data.techPacks[0];
  const [approved, setApproved] = useState(false);
  if (pack === undefined) return <Navigate to="/specs" replace />;
  return (
    <>
      <PageHeader eyebrow={t('spec.eyebrow')} title={`${pack.brand} / ${pack.styleCode}`} description={`v${pack.version} · ${pack.hash}`} />
      <Card className="admin-table-card"><div className="table-scroll"><table><thead><tr><th>{t('spec.original')}</th><th>{t('spec.canonical')}</th><th>{t('spec.mapping')}</th></tr></thead><tbody>{pack.mappings.map((mapping) => <tr key={mapping.originalTerm}><td>{mapping.originalTerm}</td><td className="mono">{mapping.canonicalPomId ?? '—'}</td><td><StatusBadge status={mapping.status === 'APPROVED' ? 'PASS' : 'REVIEW'} label={mapping.status} /></td></tr>)}</tbody></table></div><Button onClick={() => setApproved(true)} disabled={pack.mappings.some((mapping) => mapping.canonicalPomId === null)}>{t('spec.approve')}</Button>{approved ? <p role="status" className="success-message">{t('spec.approved')}</p> : null}</Card>
    </>
  );
}

function CategoriesPage() {
  const { t } = useTranslation();
  const [categories, setCategories] = useState(['T-shirt', 'Polo shirt']);
  const [name, setName] = useState('');
  function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); if (name.trim().length > 0) { setCategories([...categories, name.trim()]); setName(''); } }
  return <><PageHeader eyebrow={t('category.eyebrow')} title={t('category.title')} description={t('category.description')} /><Card className="editor-card"><form className="inline-form" onSubmit={submit}><label htmlFor="category-name">{t('category.name')}</label><input id="category-name" value={name} onChange={(event) => setName(event.target.value)} /><Button type="submit">{t('category.add')}</Button></form><ul className="entity-list">{categories.map((category) => <li key={category}><Shirt aria-hidden="true" />{category}<StatusBadge status="PASS" label={t('category.active')} /></li>)}</ul></Card></>;
}

function UsersPage({ data }: { readonly data: DashboardData }) {
  const { t } = useTranslation();
  const [users, setUsers] = useState(data.users);
  function addUser() {
    setUsers([...users, { id: `user-${users.length + 1}`, name: 'New operator', email: `operator${users.length + 1}@example.com`, role: 'Operator', active: true }]);
  }
  return <><PageHeader eyebrow={t('user.eyebrow')} title={t('user.title')} description={t('user.description')} actions={<Button onClick={addUser}>{t('user.add')}</Button>} /><Card className="admin-table-card"><div className="table-scroll"><table><thead><tr><th>{t('user.name')}</th><th>{t('user.email')}</th><th>{t('user.role')}</th><th>{t('user.status')}</th><th /></tr></thead><tbody>{users.map((user) => <tr key={user.id}><td>{user.name}</td><td>{user.email}</td><td><select aria-label={`${t('user.role')} ${user.name}`} value={user.role} onChange={(event) => setUsers(users.map((candidate) => candidate.id === user.id ? { ...candidate, role: event.target.value } : candidate))}><option>Administrator</option><option>Operator</option><option>Auditor</option></select></td><td><StatusBadge status={user.active ? 'PASS' : 'INVALID'} label={user.active ? t('user.active') : t('user.inactive')} /></td><td><button className="text-button" onClick={() => setUsers(users.map((candidate) => candidate.id === user.id ? { ...candidate, active: !candidate.active } : candidate))}>{user.active ? t('user.deactivate') : t('user.activate')}</button><button className="text-button" onClick={() => setUsers(users.filter((candidate) => candidate.id !== user.id))}>{t('user.delete')}</button></td></tr>)}</tbody></table></div></Card></>;
}

function RolesPage() {
  const { t } = useTranslation();
  const permissions = [
    ['inspections.read', true, true, true],
    ['inspections.capture', true, true, false],
    ['inspections.review', true, false, true],
    ['stations.manage', true, false, false],
    ['specs.manage', true, false, false],
    ['users.manage', true, false, false],
    ['reports.read', true, false, true],
  ] as const;
  return <><PageHeader eyebrow={t('role.eyebrow')} title={t('role.title')} description={t('role.description')} /><Card className="admin-table-card"><div className="table-scroll"><table><thead><tr><th>{t('role.permission')}</th><th>{t('role.admin')}</th><th>{t('role.operator')}</th><th>{t('role.auditor')}</th></tr></thead><tbody>{permissions.map(([permission, admin, operator, auditor]) => <tr key={permission}><td className="mono">{permission}</td>{[admin, operator, auditor].map((allowed, index) => <td key={index}>{allowed ? '✓' : '—'}</td>)}</tr>)}</tbody></table></div></Card></>;
}

function ReportsPage({ data }: { readonly data: DashboardData }) {
  const { t } = useTranslation();
  const pareto = [{ name: 'Shoulder', count: 18 }, { name: 'Body length', count: 12 }, { name: 'Sleeve', count: 8 }, { name: 'Chest', count: 4 }];
  const trend = [{ day: 'Mon', pass: 91 }, { day: 'Tue', pass: 93 }, { day: 'Wed', pass: 89 }, { day: 'Thu', pass: 95 }, { day: 'Fri', pass: 94 }];
  function exportCsv() {
    const header = 'order,style,size,status,captured_at_utc\n';
    const rows = data.inspections.map((item) => [item.orderCode, item.styleCode, item.sizeCode, item.status, item.capturedAtUtc].join(',')).join('\n');
    const link = document.createElement('a');
    link.href = URL.createObjectURL(new Blob([header + rows], { type: 'text/csv' }));
    link.download = 'specproof-inspections.csv';
    link.click();
    URL.revokeObjectURL(link.href);
  }
  function exportPdf() {
    const document = new jsPDF();
    document.text('SpecProof quality report', 18, 20);
    document.text(`Inspections: ${data.inspections.length}`, 18, 34);
    document.save('specproof-quality-report.pdf');
  }
  return (
    <>
      <PageHeader eyebrow={t('report.eyebrow')} title={t('report.title')} description={t('report.description')} actions={<><Button onClick={exportCsv}>{t('report.csv')}</Button><Button className="button-secondary" onClick={exportPdf}>{t('report.pdf')}</Button></>} />
      <div className="chart-grid">
        <Card className="chart-card"><h2>{t('report.pareto')}</h2><ResponsiveContainer width="100%" height={300}><BarChart data={pareto}><CartesianGrid stroke="var(--ink-700)" /><XAxis dataKey="name" stroke="var(--ivory-300)" /><YAxis stroke="var(--ivory-300)" /><Tooltip /><Bar dataKey="count" fill="var(--amber-400)" /></BarChart></ResponsiveContainer></Card>
        <Card className="chart-card"><h2>{t('report.trend')}</h2><ResponsiveContainer width="100%" height={300}><LineChart data={trend}><CartesianGrid stroke="var(--ink-700)" /><XAxis dataKey="day" stroke="var(--ivory-300)" /><YAxis domain={[80, 100]} stroke="var(--ivory-300)" /><Tooltip /><Line type="monotone" dataKey="pass" stroke="var(--cyan-400)" strokeWidth={3} /></LineChart></ResponsiveContainer></Card>
      </div>
      <Card className="admin-table-card"><h2>{t('report.batch')}</h2><div className="evidence-links">{data.evidence.map((record) => <Link key={record.id} to={`/evidence/${record.id}`}><ShieldCheck aria-hidden="true" />{record.inspectionId}</Link>)}</div></Card>
    </>
  );
}

function EvidencePage({ data }: { readonly data: DashboardData }) {
  const { t } = useTranslation();
  const { id } = useParams();
  const record = data.evidence.find((candidate) => candidate.id === id) ?? data.evidence[0];
  if (record === undefined) return <Navigate to="/reports" replace />;
  return <><PageHeader eyebrow={t('evidence.eyebrow')} title={t('evidence.title')} actions={<StatusBadge status={record.signatureValid ? 'PASS' : 'FAIL'} label={t('evidence.valid')} />} /><Card className="evidence-card"><EvidenceField label={t('evidence.record_hash')} value={record.recordHash} /><EvidenceField label={t('evidence.previous_hash')} value={record.previousHash ?? 'GENESIS'} /><EvidenceField label={t('evidence.algorithm')} value={record.signatureAlgorithm} /><EvidenceField label={t('evidence.model')} value={record.modelVersion} /><EvidenceField label={t('evidence.ontology')} value={record.ontologyVersion} /><EvidenceField label={t('evidence.compiler')} value={record.compilerVersion} /><time dateTime={record.producedAtUtc}>{formatTimestamp(record.producedAtUtc)}</time></Card></>;
}

function EvidenceField({ label, value }: { readonly label: string; readonly value: string }) {
  return <div><span>{label}</span><code>{value}</code></div>;
}

function SettingsPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const session = readAdminSession();
  const [tenantId, setTenantId] = useState(session?.tenantId ?? '11111111-1111-1111-1111-111111111111');
  const [switched, setSwitched] = useState(false);
  async function switchTenant() {
    const nextSession = await createDevelopmentSession(tenantId, session?.role ?? 'admin');
    window.sessionStorage.setItem(adminSessionKey, JSON.stringify(nextSession));
    queryClient.clear();
    setSwitched(true);
    navigate('/');
  }
  return <><PageHeader eyebrow={t('settings.eyebrow')} title={t('settings.title')} description={t('settings.description')} /><Card className="editor-card"><label htmlFor="settings-tenant">{t('settings.tenant')}</label><select id="settings-tenant" value={tenantId} onChange={(event) => setTenantId(event.target.value)}><option value="11111111-1111-1111-1111-111111111111">SpecProof Demo UK</option><option value="22222222-2222-2222-2222-222222222222">SpecProof Demo APAC</option></select><Button onClick={() => void switchTenant()}>{t('settings.switch')}</Button>{switched ? <p role="status" className="success-message">{t('settings.switched')}</p> : null}</Card></>;
}

export function App() {
  return <Routes><Route path="/login" element={<LoginPage />} /><Route path="/*" element={<RequireAdmin><AdminShell /></RequireAdmin>} /></Routes>;
}
