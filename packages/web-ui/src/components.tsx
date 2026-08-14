import * as Dialog from '@radix-ui/react-dialog';
import {
  AlertTriangle,
  Check,
  ChevronRight,
  CircleX,
  Languages,
  LoaderCircle,
  Menu,
  Moon,
  Sun,
  X,
  type LucideIcon,
} from 'lucide-react';
import { useState, type ButtonHTMLAttributes, type ReactNode } from 'react';
import { NavLink } from 'react-router-dom';
import { useTheme } from './theme';

export type ResultStatus = 'PASS' | 'FAIL' | 'REVIEW' | 'INVALID' | 'PENDING';

export interface NavigationItem {
  readonly to: string;
  readonly label: string;
  readonly icon: LucideIcon;
  readonly end?: boolean;
}

export function Button({ className = '', ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button className={`button ${className}`.trim()} {...props} />;
}

export function Card({
  children,
  className = '',
}: {
  readonly children: ReactNode;
  readonly className?: string;
}) {
  return <section className={`card ${className}`.trim()}>{children}</section>;
}

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  readonly eyebrow: string;
  readonly title: string;
  readonly description?: string;
  readonly actions?: ReactNode;
}) {
  return (
    <header className="page-header">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        {description === undefined ? null : <p className="page-description">{description}</p>}
      </div>
      {actions === undefined ? null : <div className="page-actions">{actions}</div>}
    </header>
  );
}

export function StatusBadge({
  status,
  label,
}: {
  readonly status: ResultStatus;
  readonly label: string;
}) {
  const Icon = status === 'PASS' ? Check : status === 'FAIL' ? CircleX : AlertTriangle;
  return (
    <span className={`status status-${status.toLowerCase()}`}>
      <Icon aria-hidden="true" size={14} />
      {label}
    </span>
  );
}

export function Metric({
  label,
  value,
  detail,
  tone = 'neutral',
}: {
  readonly label: string;
  readonly value: string;
  readonly detail?: string;
  readonly tone?: 'neutral' | 'amber' | 'cyan' | 'pass' | 'fail';
}) {
  return (
    <Card className={`metric metric-${tone}`}>
      <span className="metric-label">{label}</span>
      <strong>{value}</strong>
      {detail === undefined ? null : <small>{detail}</small>}
    </Card>
  );
}

export function ThemeToggle({
  darkLabel,
  lightLabel,
}: {
  readonly darkLabel: string;
  readonly lightLabel: string;
}) {
  const { theme, toggleTheme } = useTheme();
  const label = theme === 'dark' ? lightLabel : darkLabel;
  return (
    <button className="icon-button" type="button" onClick={toggleTheme} aria-label={label} title={label}>
      {theme === 'dark' ? <Sun aria-hidden="true" /> : <Moon aria-hidden="true" />}
    </button>
  );
}

export function LanguageSwitcher({
  label,
  value,
  options,
  onChange,
}: {
  readonly label: string;
  readonly value: string;
  readonly options: readonly { readonly value: string; readonly label: string }[];
  readonly onChange: (value: string) => void;
}) {
  return (
    <label className="language-select">
      <Languages aria-hidden="true" size={18} />
      <span className="sr-only">{label}</span>
      <select aria-label={label} value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

export function AppShell({
  productLabel,
  sectionLabel,
  navigation,
  utilities,
  children,
}: {
  readonly productLabel: string;
  readonly sectionLabel: string;
  readonly navigation: readonly NavigationItem[];
  readonly utilities: ReactNode;
  readonly children: ReactNode;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="shell">
      <aside className={`sidebar ${open ? 'sidebar-open' : ''}`}>
        <div className="brand-lockup">
          <span className="brand-mark">S</span>
          <div>
            <strong>{productLabel}</strong>
            <small>{sectionLabel}</small>
          </div>
        </div>
        <nav className="primary-nav" aria-label={sectionLabel}>
          {navigation.map(({ to, label, icon: Icon, end }) => (
            <NavLink key={to} to={to} end={end ?? false} onClick={() => setOpen(false)}>
              <Icon aria-hidden="true" size={18} />
              <span>{label}</span>
              <ChevronRight className="nav-chevron" aria-hidden="true" size={14} />
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-foot">
          <span className="signal-dot" />
          {utilities}
        </div>
      </aside>
      <div className="shell-main">
        <header className="topbar">
          <button
            className="icon-button menu-button"
            type="button"
            onClick={() => setOpen((value) => !value)}
            aria-label={sectionLabel}
          >
            <Menu aria-hidden="true" />
          </button>
          <div className="topbar-rule"><span>SPEC / PROOF</span></div>
          {utilities}
        </header>
        <main className="page-content">{children}</main>
      </div>
    </div>
  );
}

export function LoadingState({ label }: { readonly label: string }) {
  return (
    <div className="state-panel" role="status">
      <LoaderCircle className="spin" aria-hidden="true" />
      {label}
    </div>
  );
}

export function ErrorState({
  title,
  detail,
  retryLabel,
  onRetry,
}: {
  readonly title: string;
  readonly detail: string;
  readonly retryLabel: string;
  readonly onRetry: () => void;
}) {
  return (
    <Card className="state-panel state-error">
      <AlertTriangle aria-hidden="true" />
      <strong>{title}</strong>
      <p>{detail}</p>
      <Button onClick={onRetry}>{retryLabel}</Button>
    </Card>
  );
}

export function EmptyState({
  title,
  detail,
}: {
  readonly title: string;
  readonly detail: string;
}) {
  return (
    <Card className="state-panel">
      <strong>{title}</strong>
      <p>{detail}</p>
    </Card>
  );
}

export interface OverlayLine {
  readonly id: string;
  readonly label: string;
  readonly status: ResultStatus;
  readonly points: readonly { readonly x: number; readonly y: number }[];
}

export function MeasurementOverlay({
  lines,
  label,
}: {
  readonly lines: readonly OverlayLine[];
  readonly label: string;
}) {
  return (
    <div className="measurement-canvas" role="img" aria-label={label}>
      <svg viewBox="0 0 100 100" aria-hidden="true">
        <path className="garment-shape" d="M31 18 L40 11 Q50 17 60 11 L69 18 L83 28 L75 40 L67 34 L70 88 L30 88 L33 34 L25 40 L17 28 Z" />
        {lines.map((line) => (
          <g key={line.id} className={`overlay-${line.status.toLowerCase()}`}>
            <polyline points={line.points.map((point) => `${point.x},${point.y}`).join(' ')} />
            {line.points.map((point, index) => (
              <circle key={`${line.id}-${index}`} cx={point.x} cy={point.y} r="1.2" />
            ))}
          </g>
        ))}
      </svg>
      <div className="overlay-legend">
        {lines.map((line) => (
          <span key={line.id}>
            <i className={`legend-${line.status.toLowerCase()}`} />
            {line.label}
          </span>
        ))}
      </div>
    </div>
  );
}

export function Modal({
  trigger,
  title,
  description,
  closeLabel,
  children,
}: {
  readonly trigger: ReactNode;
  readonly title: string;
  readonly description: string;
  readonly closeLabel: string;
  readonly children: ReactNode;
}) {
  return (
    <Dialog.Root>
      <Dialog.Trigger asChild>{trigger}</Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="dialog-overlay" />
        <Dialog.Content className="dialog-content">
          <Dialog.Title>{title}</Dialog.Title>
          <Dialog.Description>{description}</Dialog.Description>
          {children}
          <Dialog.Close className="dialog-close" aria-label={closeLabel}>
            <X aria-hidden="true" />
          </Dialog.Close>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
