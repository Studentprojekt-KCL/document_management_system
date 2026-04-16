<script setup>
/**
 * IntelligenceView.vue - Analytics dashboard for the DMIS.
 * Visualizes document indexing stats, classification breakdown,
 * source distribution, top searches, and recent activity.
 *
 * All charts are built with pure SVG/CSS — no chart library dependency.
 *
 * NOTE: This view currently uses mock data. Wire to backend endpoints
 * (e.g. /api/analytics/overview) once they are available.
 */
import { ref, computed } from 'vue'
import { BarChart3, FileText, Search, Sparkles, TrendingUp, Clock, ArrowUpRight, ArrowDownRight } from 'lucide-vue-next'

/* ── TODO: Replace with real backend data ── */
const stats = ref([
  { id: 'docs', label: 'Documents indexed', value: 1_284, delta: 12, icon: FileText },
  { id: 'searches', label: 'Searches (7d)', value: 3_420, delta: 8, icon: Search },
  { id: 'summaries', label: 'AI summaries generated', value: 217, delta: 34, icon: Sparkles },
  { id: 'response', label: 'Avg response time', value: '142ms', delta: -6, icon: Clock }
])

const classificationBreakdown = ref([
  { label: 'Public', count: 412, color: '#059669' },
  { label: 'Internal', count: 538, color: '#2563eb' },
  { label: 'Sensitive', count: 221, color: '#d97706' },
  { label: 'Confidential', count: 113, color: '#dc2626' }
])

const totalClassified = computed(() => classificationBreakdown.value.reduce((s, b) => s + b.count, 0))

const sources = ref([
  { label: 'GitLab', count: 724, color: '#7c3aed' },
  { label: 'GitHub', count: 398, color: '#5b21b6' },
  { label: 'Network FS', count: 162, color: '#a78bfa' }
])

const totalSources = computed(() => sources.value.reduce((s, b) => s + b.count, 0))

/* Donut chart math */
const donutSegments = computed(() => {
  const circumference = 2 * Math.PI * 48
  let offset = 0
  return sources.value.map((s) => {
    const portion = s.count / totalSources.value
    const length = portion * circumference
    const seg = { ...s, length, offset, circumference }
    offset += length
    return seg
  })
})

const topSearches = ref([
  { term: 'authentication', count: 342 },
  { term: 'keycloak config', count: 218 },
  { term: 'api reference', count: 187 },
  { term: 'deployment guide', count: 154 },
  { term: 'token refresh', count: 132 },
  { term: 'docker setup', count: 98 }
])

const maxSearchCount = computed(() => Math.max(...topSearches.value.map((s) => s.count)))

const recentActivity = ref([
  { id: 1, type: 'search', text: 'Searched for "keycloak config"', time: '2 min ago' },
  { id: 2, type: 'classify', text: 'Updated classification on auth-guide.pdf → Sensitive', time: '14 min ago' },
  { id: 3, type: 'summary', text: 'Generated AI summary for api-spec.md', time: '28 min ago' },
  { id: 4, type: 'search', text: 'Searched for "token refresh"', time: '41 min ago' },
  { id: 5, type: 'classify', text: 'Updated classification on internal-memo.docx → Internal', time: '1h ago' },
  { id: 6, type: 'search', text: 'Searched for "deployment"', time: '2h ago' }
])

const activityIcon = (type) => {
  if (type === 'search') return Search
  if (type === 'classify') return BarChart3
  if (type === 'summary') return Sparkles
  return FileText
}
</script>

<template>
  <section class="intel-view">
    <header class="view-header">
      <h1>Intelligence</h1>
      <p class="subtitle">Analytics and usage insights across your document system.</p>
    </header>

    <!-- ── Stat cards ── -->
    <div class="stat-grid">
      <article v-for="stat in stats" :key="stat.id" class="stat-card">
        <div class="stat-icon"><component :is="stat.icon" :size="18" /></div>
        <p class="stat-label">{{ stat.label }}</p>
        <p class="stat-value">{{ stat.value.toLocaleString?.() ?? stat.value }}</p>
        <p :class="['stat-delta', stat.delta >= 0 ? 'up' : 'down']">
          <ArrowUpRight v-if="stat.delta >= 0" :size="12" />
          <ArrowDownRight v-else :size="12" />
          {{ Math.abs(stat.delta) }}% vs last week
        </p>
      </article>
    </div>

    <div class="chart-grid">
      <!-- ── Classification breakdown (horizontal bars) ── -->
      <article class="panel">
        <header class="panel-header">
          <h2>Classification breakdown</h2>
          <span class="panel-count">{{ totalClassified.toLocaleString() }} documents</span>
        </header>

        <ul class="bar-list">
          <li v-for="item in classificationBreakdown" :key="item.label" class="bar-item">
            <div class="bar-labels">
              <span class="bar-name">
                <span class="bar-swatch" :style="{ background: item.color }"></span>
                {{ item.label }}
              </span>
              <span class="bar-count">
                {{ item.count.toLocaleString() }}
                <span class="bar-pct">({{ Math.round((item.count / totalClassified) * 100) }}%)</span>
              </span>
            </div>
            <div class="bar-track">
              <div class="bar-fill" :style="{ width: `${(item.count / totalClassified) * 100}%`, background: item.color }"></div>
            </div>
          </li>
        </ul>
      </article>

      <!-- ── Source distribution (SVG donut) ── -->
      <article class="panel">
        <header class="panel-header">
          <h2>Source distribution</h2>
          <span class="panel-count">{{ totalSources.toLocaleString() }} docs</span>
        </header>

        <div class="donut-wrap">
          <svg viewBox="0 0 120 120" class="donut-svg">
            <circle cx="60" cy="60" r="48" fill="none" stroke="#f1f5f9" stroke-width="16" />
            <circle
              v-for="seg in donutSegments"
              :key="seg.label"
              cx="60"
              cy="60"
              r="48"
              fill="none"
              :stroke="seg.color"
              stroke-width="16"
              :stroke-dasharray="`${seg.length} ${seg.circumference}`"
              :stroke-dashoffset="-seg.offset"
              transform="rotate(-90 60 60)"
            />
            <text x="60" y="56" text-anchor="middle" class="donut-center-value">{{ totalSources }}</text>
            <text x="60" y="72" text-anchor="middle" class="donut-center-label">total</text>
          </svg>

          <ul class="donut-legend">
            <li v-for="s in sources" :key="s.label">
              <span class="legend-swatch" :style="{ background: s.color }"></span>
              <span class="legend-label">{{ s.label }}</span>
              <span class="legend-count">{{ s.count.toLocaleString() }}</span>
            </li>
          </ul>
        </div>
      </article>

      <!-- ── Top searches ── -->
      <article class="panel">
        <header class="panel-header">
          <h2>Top search terms</h2>
          <span class="panel-count"><TrendingUp :size="13" /> Last 7 days</span>
        </header>

        <ul class="search-list">
          <li v-for="(s, i) in topSearches" :key="s.term" class="search-row">
            <span class="rank">#{{ i + 1 }}</span>
            <div class="search-body">
              <p class="search-term">{{ s.term }}</p>
              <div class="search-bar-track">
                <div class="search-bar-fill" :style="{ width: `${(s.count / maxSearchCount) * 100}%` }"></div>
              </div>
            </div>
            <span class="search-count">{{ s.count }}</span>
          </li>
        </ul>
      </article>

      <!-- ── Recent activity ── -->
      <article class="panel">
        <header class="panel-header">
          <h2>Recent activity</h2>
          <span class="panel-count">{{ recentActivity.length }} events</span>
        </header>

        <ul class="activity-list">
          <li v-for="evt in recentActivity" :key="evt.id" class="activity-row">
            <span :class="['activity-icon', `activity-${evt.type}`]">
              <component :is="activityIcon(evt.type)" :size="14" />
            </span>
            <div class="activity-body">
              <p class="activity-text">{{ evt.text }}</p>
              <p class="activity-time">{{ evt.time }}</p>
            </div>
          </li>
        </ul>
      </article>
    </div>
  </section>
</template>

<style scoped>
.intel-view {
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

/* ── Stat cards ── */
.stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 0.85rem;
  margin-bottom: 1.25rem;
}

.stat-card {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  padding: 1rem;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
  position: relative;
}

.stat-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: linear-gradient(135deg, #5b21b6 0%, #7c3aed 100%);
  color: #ffffff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 0.65rem;
}

.stat-label {
  margin: 0;
  font-size: 0.78rem;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.stat-value {
  margin: 0.25rem 0 0.35rem;
  font-size: 1.75rem;
  font-weight: 700;
  color: #0f172a;
  font-variant-numeric: tabular-nums;
}

.stat-delta {
  margin: 0;
  font-size: 0.78rem;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 0.2rem;
}

.stat-delta.up {
  color: #059669;
}
.stat-delta.down {
  color: #dc2626;
}

/* ── Panels ── */
.chart-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(380px, 1fr));
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
  align-items: center;
  margin-bottom: 1rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid #f1f5f9;
}

.panel-header h2 {
  margin: 0;
  font-size: 1rem;
  font-weight: 700;
  color: #1f2937;
}

.panel-count {
  font-size: 0.78rem;
  font-weight: 600;
  color: #6b7280;
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
}

/* ── Bar list ── */
.bar-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
}

.bar-labels {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.35rem;
  font-size: 0.85rem;
}

.bar-name {
  font-weight: 600;
  color: #1f2937;
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
}

.bar-swatch {
  width: 10px;
  height: 10px;
  border-radius: 3px;
  display: inline-block;
}

.bar-count {
  font-weight: 700;
  color: #0f172a;
  font-variant-numeric: tabular-nums;
}

.bar-pct {
  color: #94a3b8;
  font-weight: 500;
  margin-left: 0.25rem;
}

.bar-track {
  height: 8px;
  background: #f1f5f9;
  border-radius: 999px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  border-radius: 999px;
  transition: width 0.4s ease;
}

/* ── Donut ── */
.donut-wrap {
  display: grid;
  grid-template-columns: 160px 1fr;
  gap: 1.25rem;
  align-items: center;
}

.donut-svg {
  width: 100%;
  max-width: 160px;
}

.donut-center-value {
  font-size: 14px;
  font-weight: 700;
  fill: #0f172a;
}

.donut-center-label {
  font-size: 6.5px;
  font-weight: 600;
  fill: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.donut-legend {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
}

.donut-legend li {
  display: grid;
  grid-template-columns: 14px 1fr auto;
  align-items: center;
  gap: 0.55rem;
  font-size: 0.88rem;
}

.legend-swatch {
  width: 10px;
  height: 10px;
  border-radius: 3px;
}

.legend-label {
  color: #1f2937;
  font-weight: 600;
}

.legend-count {
  color: #475569;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

/* ── Top searches ── */
.search-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
}

.search-row {
  display: grid;
  grid-template-columns: 28px 1fr auto;
  align-items: center;
  gap: 0.75rem;
}

.rank {
  color: #94a3b8;
  font-size: 0.8rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.search-body {
  min-width: 0;
}

.search-term {
  margin: 0 0 0.3rem;
  font-size: 0.88rem;
  font-weight: 600;
  color: #1f2937;
}

.search-bar-track {
  height: 5px;
  background: #f1f5f9;
  border-radius: 999px;
  overflow: hidden;
}

.search-bar-fill {
  height: 100%;
  background: linear-gradient(135deg, #5b21b6 0%, #7c3aed 100%);
  border-radius: 999px;
}

.search-count {
  color: #0f172a;
  font-weight: 700;
  font-size: 0.85rem;
  font-variant-numeric: tabular-nums;
}

/* ── Activity feed ── */
.activity-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.activity-row {
  display: grid;
  grid-template-columns: 32px 1fr;
  gap: 0.7rem;
  padding: 0.55rem 0;
  border-bottom: 1px solid #f1f5f9;
}

.activity-row:last-child {
  border-bottom: none;
}

.activity-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.activity-search {
  background: #eff6ff;
  color: #2563eb;
}

.activity-classify {
  background: #faf5ff;
  color: #7c3aed;
}

.activity-summary {
  background: #fffbeb;
  color: #d97706;
}

.activity-text {
  margin: 0;
  font-size: 0.85rem;
  color: #1f2937;
  line-height: 1.4;
}

.activity-time {
  margin: 0.15rem 0 0;
  font-size: 0.75rem;
  color: #94a3b8;
}

@media (max-width: 768px) {
  .donut-wrap {
    grid-template-columns: 1fr;
    justify-items: center;
  }
}
</style>
