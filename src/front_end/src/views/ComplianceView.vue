<script setup>
/**
 * ComplianceView.vue - Security and compliance dashboard.
 * Shows an audit log of classification changes (tied to KR-31),
 * a list of unclassified documents needing review,
 * and high-level compliance metrics.
 *
 * NOTE: Currently uses mock data. Wire to real endpoints once the
 * backend exposes /api/audit-log and /api/documents/unclassified.
 */

import { ref, computed } from 'vue'
import { ShieldCheck, AlertTriangle, FileClock, Filter, Download, FileWarning, ArrowRight, CheckCircle2 } from 'lucide-vue-next'

/* TODO: Replace with real backend data  */
const metrics = ref([
  { id: 'classified', label: 'Classified documents', value: 1_171, total: 1_284, tone: 'success' },
  { id: 'unclassified', label: 'Awaiting classification', value: 113, tone: 'warning' },
  { id: 'changes', label: 'Classification changes (30d)', value: 42, tone: 'neutral' },
  { id: 'reviewers', label: 'Active reviewers', value: 4, tone: 'neutral' }
])

const complianceRate = computed(() => {
  const classified = metrics.value.find((m) => m.id === 'classified')
  return classified ? Math.round((classified.value / classified.total) * 100) : 0
})

const auditLog = ref([
  {
    id: 1,
    when: '2026-04-16 09:42',
    user: 'alice.lee',
    document: 'customer-data-policy.pdf',
    from: 'Internal',
    to: 'Confidential',
    action: 'classification-change'
  },
  {
    id: 2,
    when: '2026-04-16 09:18',
    user: 'm.muaath',
    document: 'public-api-docs.md',
    from: null,
    to: 'Public',
    action: 'initial-classification'
  },
  {
    id: 3,
    when: '2026-04-15 16:55',
    user: 'alice.lee',
    document: 'internal-memo-q1.docx',
    from: 'Sensitive',
    to: 'Internal',
    action: 'classification-change'
  },
  {
    id: 4,
    when: '2026-04-15 14:22',
    user: 'j.kumar',
    document: 'security-audit-2026.pdf',
    from: null,
    to: 'Confidential',
    action: 'initial-classification'
  },
  {
    id: 5,
    when: '2026-04-15 11:07',
    user: 'm.muaath',
    document: 'deployment-guide.md',
    from: 'Internal',
    to: 'Sensitive',
    action: 'classification-change'
  },
  {
    id: 6,
    when: '2026-04-14 15:33',
    user: 'alice.lee',
    document: 'partner-agreement.pdf',
    from: 'Sensitive',
    to: 'Confidential',
    action: 'classification-change'
  }
])

const unclassified = ref([
  { id: 1, filename: 'release-notes-v2.3.md', source: 'GitLab', updated: '2026-04-15', size: '42 KB' },
  { id: 2, filename: 'architecture-review.pdf', source: 'GitHub', updated: '2026-04-14', size: '1.2 MB' },
  { id: 3, filename: 'vendor-contract.docx', source: 'Network FS', updated: '2026-04-13', size: '288 KB' },
  { id: 4, filename: 'onboarding-checklist.md', source: 'GitLab', updated: '2026-04-12', size: '18 KB' },
  { id: 5, filename: 'incident-report-4421.pdf', source: 'Network FS', updated: '2026-04-11', size: '764 KB' }
])

/* Audit log filter */
const filterAction = ref('all')
const filteredLog = computed(() => {
  if (filterAction.value === 'all') return auditLog.value
  return auditLog.value.filter((entry) => entry.action === filterAction.value)
})

/* Export audit log as CSV */
const exportAuditLog = () => {
  const header = ['Timestamp', 'User', 'Document', 'From', 'To', 'Action']
  const rows = auditLog.value.map((e) => [e.when, e.user, e.document, e.from ?? '—', e.to, e.action])
  const csv = [header, ...rows].map((row) => row.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(',')).join('\n')

  const blob = new Blob([csv], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `audit-log-${new Date().toISOString().split('T')[0]}.csv`
  link.click()
  URL.revokeObjectURL(url)
}

const classBadge = (level) => {
  if (!level) return 'badge-none'
  return `badge-${level.toLowerCase()}`
}
</script>

<template>
  <section class="compliance-view">
    <header class="view-header">
      <h1>Security & Compliance</h1>
      <p class="subtitle">Audit trail, document classification status, and compliance posture.</p>
    </header>

    <!-- Compliance rate hero -->
    <article class="hero-card">
      <div class="hero-main">
        <p class="hero-eyebrow"><ShieldCheck :size="14" /> COMPLIANCE RATE</p>
        <p class="hero-value">{{ complianceRate }}%</p>
        <p class="hero-subtext">
          {{ metrics[0].value.toLocaleString() }} of {{ metrics[0].total.toLocaleString() }} documents classified
        </p>
      </div>

      <div class="hero-progress">
        <div class="progress-track">
          <div class="progress-fill" :style="{ width: `${complianceRate}%` }"></div>
        </div>
        <div class="progress-markers">
          <span>0%</span>
          <span>50%</span>
          <span>100%</span>
        </div>
      </div>
    </article>

    <!-- Secondary metrics -->
    <div class="metric-grid">
      <article v-for="metric in metrics.slice(1)" :key="metric.id" :class="['metric-card', `tone-${metric.tone}`]">
        <p class="metric-label">{{ metric.label }}</p>
        <p class="metric-value">{{ metric.value.toLocaleString() }}</p>
      </article>
    </div>

    <div class="compliance-grid">
      <!-- Audit log -->
      <article class="panel panel-wide">
        <header class="panel-header">
          <div>
            <h2><FileClock :size="16" /> Classification Audit Log</h2>
            <p class="panel-sub">Every change to a document's classification level.</p>
          </div>
          <div class="panel-actions">
            <div class="filter-wrap">
              <Filter :size="13" />
              <select v-model="filterAction" class="filter-select">
                <option value="all">All actions</option>
                <option value="classification-change">Changes</option>
                <option value="initial-classification">Initial classifications</option>
              </select>
            </div>
            <button class="btn-outline" type="button" @click="exportAuditLog">
              <Download :size="13" />
              Export CSV
            </button>
          </div>
        </header>

        <div class="table-wrap">
          <table class="audit-table">
            <thead>
              <tr>
                <th>When</th>
                <th>User</th>
                <th>Document</th>
                <th>Change</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="entry in filteredLog" :key="entry.id">
                <td class="cell-when">{{ entry.when }}</td>
                <td class="cell-user">
                  <span class="user-chip">{{ entry.user }}</span>
                </td>
                <td class="cell-doc">{{ entry.document }}</td>
                <td class="cell-change">
                  <span v-if="entry.from" :class="['class-badge', classBadge(entry.from)]">{{ entry.from }}</span>
                  <span v-else class="class-badge badge-none">Unclassified</span>
                  <ArrowRight :size="12" class="arrow" />
                  <span :class="['class-badge', classBadge(entry.to)]">{{ entry.to }}</span>
                </td>
              </tr>
              <tr v-if="filteredLog.length === 0">
                <td colspan="4" class="empty-state">
                  <CheckCircle2 :size="20" />
                  <p>No audit entries match this filter.</p>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </article>

      <!-- Unclassified documents -->
      <article class="panel">
        <header class="panel-header">
          <div>
            <h2><AlertTriangle :size="16" class="warn-icon" /> Needs Review</h2>
            <p class="panel-sub">Documents without a security classification.</p>
          </div>
          <span class="count-pill">{{ unclassified.length }}</span>
        </header>

        <ul class="review-list">
          <li v-for="doc in unclassified" :key="doc.id" class="review-row">
            <div class="review-main">
              <div class="review-icon"><FileWarning :size="14" /></div>
              <div class="review-body">
                <p class="review-name">{{ doc.filename }}</p>
                <p class="review-meta">{{ doc.source }} · {{ doc.size }} · Updated {{ doc.updated }}</p>
              </div>
            </div>
            <button class="btn-small" type="button" title="Review in search">Review</button>
          </li>
          <li v-if="unclassified.length === 0" class="empty-review">
            <CheckCircle2 :size="18" />
            All documents have been classified.
          </li>
        </ul>
      </article>
    </div>
  </section>
</template>

<style scoped>
.compliance-view {
  padding: 0.5rem;
}

.view-header {
  margin-bottom: 1.5rem;
}

.view-header h1 {
  margin: 0;
  font-size: 1.8rem;
}

.subtitle {
  margin: 0.25rem 0 0;
  color: #6b7280;
  font-size: 0.95rem;
}

.hero-card {
  background: linear-gradient(135deg, #5b21b6 0%, #7c3aed 100%);
  border-radius: 16px;
  padding: 1.5rem 1.75rem;
  color: #ffffff;
  margin-bottom: 1rem;
  display: grid;
  grid-template-columns: 1fr 1.5fr;
  gap: 2rem;
  align-items: center;
}

.hero-eyebrow {
  margin: 0;
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  opacity: 0.9;
}

.hero-value {
  margin: 0.5rem 0 0.3rem;
  font-size: 3rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  line-height: 1;
}

.hero-subtext {
  margin: 0;
  font-size: 0.9rem;
  opacity: 0.9;
}

.hero-progress {
  padding: 0.5rem 0;
}

.progress-track {
  height: 10px;
  background: rgba(255, 255, 255, 0.22);
  border-radius: 999px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: #ffffff;
  border-radius: 999px;
  transition: width 0.5s ease;
}

.progress-markers {
  display: flex;
  justify-content: space-between;
  margin-top: 0.4rem;
  font-size: 0.72rem;
  font-weight: 600;
  opacity: 0.85;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 0.85rem;
  margin-bottom: 1.25rem;
}

.metric-card {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  padding: 1rem 1.1rem;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
  border-left: 4px solid transparent;
}

.metric-card.tone-warning {
  border-left-color: #d97706;
}
.metric-card.tone-success {
  border-left-color: #059669;
}
.metric-card.tone-neutral {
  border-left-color: #7c3aed;
}

.metric-label {
  margin: 0;
  font-size: 0.78rem;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.metric-value {
  margin: 0.35rem 0 0;
  font-size: 1.65rem;
  font-weight: 700;
  color: #0f172a;
  font-variant-numeric: tabular-nums;
}

.compliance-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 1rem;
}

.panel {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  padding: 1.25rem;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
  padding-bottom: 0.85rem;
  border-bottom: 1px solid #f1f5f9;
  gap: 1rem;
  flex-wrap: wrap;
}

.panel-header h2 {
  margin: 0;
  font-size: 1rem;
  font-weight: 700;
  color: #1f2937;
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}

.panel-sub {
  margin: 0.2rem 0 0;
  font-size: 0.8rem;
  color: #94a3b8;
}

.panel-actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.warn-icon {
  color: #d97706;
}

.count-pill {
  background: #fef3c7;
  color: #92400e;
  padding: 0.25rem 0.65rem;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 700;
}

.filter-wrap {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  background: #f8fafc;
  border: 1px solid #d8dee7;
  border-radius: 8px;
  padding: 0.35rem 0.55rem;
  color: #475569;
}

.filter-select {
  border: none;
  background: transparent;
  font-size: 0.82rem;
  font-weight: 600;
  color: #1f2937;
  outline: none;
  cursor: pointer;
  font-family: inherit;
}

.btn-outline {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.45rem 0.8rem;
  border-radius: 8px;
  background: #ffffff;
  border: 1px solid #d8dee7;
  color: #475569;
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
}

.btn-outline:hover {
  border-color: #7c3aed;
  color: #7c3aed;
  background: #faf5ff;
}

.btn-small {
  padding: 0.35rem 0.75rem;
  border-radius: 8px;
  background: #faf5ff;
  color: #7c3aed;
  border: 1px solid #e9d5ff;
  font-size: 0.78rem;
  font-weight: 700;
  cursor: pointer;
}

.btn-small:hover {
  background: #7c3aed;
  color: #ffffff;
  border-color: #7c3aed;
}

.table-wrap {
  overflow-x: auto;
}

.audit-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}

.audit-table thead th {
  text-align: left;
  padding: 0.5rem 0.75rem;
  font-size: 0.72rem;
  font-weight: 700;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  border-bottom: 1px solid #e5e7eb;
}

.audit-table tbody td {
  padding: 0.7rem 0.75rem;
  border-bottom: 1px solid #f1f5f9;
  vertical-align: middle;
}

.audit-table tbody tr:last-child td {
  border-bottom: none;
}

.cell-when {
  color: #6b7280;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.user-chip {
  background: #f1f5f9;
  color: #334155;
  padding: 0.15rem 0.55rem;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 600;
}

.cell-doc {
  color: #1f2937;
  font-weight: 500;
}

.cell-change {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  flex-wrap: wrap;
}

.arrow {
  color: #94a3b8;
  flex-shrink: 0;
}

.class-badge {
  display: inline-block;
  padding: 0.2rem 0.55rem;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 700;
  white-space: nowrap;
}

.badge-public {
  background: #ecfdf5;
  color: #065f46;
  border: 1px solid #a7f3d0;
}
.badge-internal {
  background: #eff6ff;
  color: #1e40af;
  border: 1px solid #bfdbfe;
}
.badge-sensitive {
  background: #fffbeb;
  color: #92400e;
  border: 1px solid #fde68a;
}
.badge-confidential {
  background: #fef2f2;
  color: #991b1b;
  border: 1px solid #fecaca;
}
.badge-none {
  background: #f3f4f6;
  color: #6b7280;
  border: 1px solid #e5e7eb;
}

.review-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.review-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.6rem 0.75rem;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #fffbf5;
  gap: 0.75rem;
}

.review-main {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  min-width: 0;
  flex: 1;
}

.review-icon {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  background: #fef3c7;
  color: #d97706;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.review-body {
  min-width: 0;
}

.review-name {
  margin: 0;
  font-size: 0.85rem;
  font-weight: 600;
  color: #1f2937;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.review-meta {
  margin: 0.15rem 0 0;
  font-size: 0.72rem;
  color: #94a3b8;
}

.empty-state,
.empty-review {
  text-align: center;
  padding: 1.5rem;
  color: #94a3b8;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.85rem;
}

.empty-review {
  flex-direction: row;
  justify-content: center;
  padding: 2rem 1rem;
  color: #059669;
  font-weight: 600;
}

@media (max-width: 1024px) {
  .compliance-grid {
    grid-template-columns: 1fr;
  }
  .hero-card {
    grid-template-columns: 1fr;
    gap: 1rem;
  }
}
</style>
