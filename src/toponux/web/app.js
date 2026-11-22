const $ = (id) => document.getElementById(id);
let cy;
let snapshot = {};
let graph = {};

const cssVar = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

const graphStyle = [
  { selector: 'node', style: { label: 'data(label)', 'text-wrap': 'wrap', 'text-max-width': 170, 'font-size': 11, color: cssVar('--graph-label'), 'text-valign': 'center', 'text-halign': 'center', width: 150, height: 66, 'background-color': cssVar('--graph-node-bg'), 'border-width': 1, 'border-color': cssVar('--graph-node-border'), padding: 8 } },
  { selector: 'node[kind="host"]', style: { 'background-color': cssVar('--graph-host-bg'), 'border-color': cssVar('--graph-host-border'), width: 190, height: 90, 'font-size': 15, 'font-weight': 700, shape: 'round-rectangle' } },
  { selector: 'node[kind="interface"]', style: { 'background-color': cssVar('--graph-interface-bg'), 'border-color': cssVar('--graph-host-border'), shape: 'round-rectangle' } },
  { selector: 'node[kind="bridge"]', style: { 'background-color': cssVar('--graph-bridge-bg'), 'border-color': cssVar('--graph-bridge-border'), shape: 'round-rectangle' } },
  { selector: 'node[kind="bond"]', style: { 'background-color': cssVar('--graph-bond-bg'), 'border-color': cssVar('--graph-bond-border'), shape: 'hexagon' } },
  { selector: 'node[kind="vlan"]', style: { 'background-color': cssVar('--graph-vlan-bg'), 'border-color': cssVar('--graph-vlan-border'), 'border-style': 'dashed', shape: 'round-rectangle' } },
  { selector: 'node[kind="gateway"]', style: { 'background-color': cssVar('--graph-gateway-bg'), 'border-color': cssVar('--graph-gateway-border'), shape: 'diamond', width: 130, height: 90 } },
  { selector: 'node[kind="neighbor"]', style: { 'background-color': cssVar('--graph-neighbor-bg'), 'border-color': cssVar('--graph-neighbor-border'), shape: 'ellipse', width: 126, height: 46, 'font-size': 10 } },
  { selector: 'node[kind="neighbor"][?docker]', style: { 'border-style': 'dashed' } },
  { selector: 'edge', style: { width: 2, 'line-color': cssVar('--graph-edge'), 'target-arrow-color': cssVar('--graph-arrow'), 'target-arrow-shape': 'triangle', 'curve-style': 'bezier', label: 'data(label)', 'font-size': 9, color: cssVar('--graph-edge-label'), 'text-background-color': cssVar('--graph-edge-label-bg'), 'text-background-opacity': 1, 'text-background-padding': 3 } },
  { selector: ':selected', style: { 'border-width': 3, 'border-color': cssVar('--graph-selected') } },
];

function countRules(rules = {}) { return (Array.isArray(rules.ipv4) ? rules.ipv4.length : 0) + (Array.isArray(rules.ipv6) ? rules.ipv6.length : 0); }
function allRoutes() { return Object.entries(snapshot.routes || {}).flatMap(([family, routes]) => (Array.isArray(routes) ? routes : []).map(route => ({ family, ...route }))); }
function interfaceAddresses(iface) { return (iface.addr_info || []).map(a => `${a.local}/${a.prefixlen}`); }
function formatBytes(value) {
  if (value == null || Number.isNaN(Number(value))) return '—';
  const units = ['B', 'KiB', 'MiB', 'GiB', 'TiB'];
  let amount = Number(value);
  let unit = 0;
  while (amount >= 1024 && unit < units.length - 1) { amount /= 1024; unit += 1; }
  return `${amount.toFixed(unit ? 1 : 0)} ${units[unit]}`;
}
function interfaceTraffic(iface) {
  const stats = iface.stats || {};
  return `↓ ${formatBytes(stats.rx_bytes)}<br>↑ ${formatBytes(stats.tx_bytes)}`;
}
function interfaceHealth(iface) {
  const stats = iface.stats || {};
  const errors = (stats.rx_errors || 0) + (stats.tx_errors || 0);
  const dropped = (stats.rx_dropped || 0) + (stats.tx_dropped || 0);
  if (!errors && !dropped) return '—';
  return `${errors} errors<br>${dropped} dropped`;
}
function interfaceHaystack(iface) {
  return [iface.ifname, iface.link_type, iface.operstate, iface.master, iface.mtu, ...interfaceAddresses(iface)]
    .filter(value => value != null).join(' ').toLowerCase();
}
function l2Index() {
  const links = snapshot.l2 && Array.isArray(snapshot.l2.links) ? snapshot.l2.links : [];
  return Object.fromEntries(links.filter(link => link.ifname).map(link => [link.ifname, link]));
}
function l2Label(iface, index = l2Index()) {
  const link = index[iface.ifname] || iface;
  const info = link.linkinfo || {};
  const data = info.info_data || {};
  if (info.info_kind === 'vlan') return `vlan ${data.id ?? '?'} on ${data.link || '?'}`;
  if (info.info_kind === 'bond') return `bond ${data.mode || ''}`.trim();
  if (info.info_kind === 'bridge') return 'bridge';
  return iface.master ? `master ${iface.master}` : '';
}
function routeHaystack(route) {
  const { family, dst, gateway, dev, table, type, scope, metric, flags } = route;
  return [family, dst, gateway, dev, table, type, scope, metric, ...(Array.isArray(flags) ? flags : [])]
    .filter(value => value != null).join(' ').toLowerCase();
}
function escapeHtml(value) { return String(value ?? '—').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
function showDetails(data) {
  $('detail-hint').textContent = data.kind === 'host' ? 'Local machine' : data.name || data.kind;
  $('details').textContent = data.details || 'No extra details.';
}
function visibleGraphElements() {
  const showIpv6 = $('graph-ipv6').checked;
  const showDocker = $('graph-docker').checked;
  const nodes = (graph.nodes || []).filter(node => {
    const data = node.data || {};
    if (!showIpv6 && data.family === 'ip6') return false;
    if (!showDocker && data.docker) return false;
    return true;
  });
  const ids = new Set(nodes.map(node => node.data.id));
  const edges = (graph.edges || []).filter(edge => ids.has(edge.data.source) && ids.has(edge.data.target));
  return [...nodes, ...edges];
}
function renderGraph() {
  if (cy) cy.destroy();
  cy = cytoscape({ container: $('cy'), elements: visibleGraphElements(), style: graphStyle,
    layout: { name: 'breadthfirst', directed: true, roots: '#host', spacingFactor: 1.35, padding: 45, animate: false }, minZoom: .25, maxZoom: 3 });
  cy.on('tap', 'node', event => showDetails(event.target.data()));
  cy.on('tap', event => { if (event.target === cy) { $('detail-hint').textContent = 'Select an element in the graph.'; $('details').textContent = 'Nothing selected.'; } });
}
function renderNeighbors() {
  const filter = ($('neighbor-filter')?.value || '').trim().toLowerCase();
  const rows = (snapshot.neighbors_view || []).filter(n => {
    if (!filter) return true;
    const haystack = [n.mac, n.oui, n.vendor, n.interface, n.state, ...(n.addresses || [])].join(' ').toLowerCase();
    return haystack.includes(filter);
  });
  $('neighbors-body').innerHTML = rows.map(n => `<tr><td><strong>${escapeHtml(n.mac)}</strong></td><td>${escapeHtml(n.vendor)}<small>${escapeHtml(n.oui)}</small></td><td>${escapeHtml(n.interface)}${n.docker ? ' <small>Docker</small>' : ''}</td><td>${escapeHtml(n.state)}</td><td>${(n.addresses || []).map(escapeHtml).join('<br>') || '—'}</td></tr>`).join('') || '<tr><td colspan="5" class="empty">No neighbour entries.</td></tr>';
}
function socketProcesses(item) {
  return (item.processes || []).map(process => `${process.name} (${process.pid})`).join(', ') || '—';
}
function socketEndpoint(item, addressKey, portKey) {
  const port = item[portKey];
  return `${item[addressKey] || '—'}${port == null ? '' : `:${port}`}`;
}
function socketHaystack(item) {
  return [item.protocol, item.state, item.local_address, item.local_port, item.peer_address, item.peer_port, ...(item.processes || []).flatMap(process => [process.name, process.pid])]
    .filter(value => value != null).join(' ').toLowerCase();
}
function renderPorts() {
  const view = snapshot.sockets_view || { available: false, listeners: [], connections: [], error: 'Socket inventory unavailable.' };
  const message = $('ports-message');
  if (!view.available) {
    message.textContent = `Socket inventory unavailable: ${view.error || 'ss could not be read.'}`;
  } else {
    message.textContent = `${(view.listeners || []).length} listening socket(s) · ${(view.connections || []).length} established connection(s) to remote peers.`;
  }
  const listenerFilter = $('listener-filter').value.trim().toLowerCase();
  const connectionFilter = $('connection-filter').value.trim().toLowerCase();
  const listeners = (view.listeners || []).filter(item => !listenerFilter || socketHaystack(item).includes(listenerFilter));
  const connections = (view.connections || []).filter(item => !connectionFilter || socketHaystack(item).includes(connectionFilter));
  $('listeners-body').innerHTML = listeners.map(item => `<tr><td>${escapeHtml(String(item.protocol).toUpperCase())}</td><td>${escapeHtml(item.local_address)}</td><td>${escapeHtml(item.local_port ?? '—')}</td><td>${escapeHtml(socketProcesses(item))}</td></tr>`).join('') || '<tr><td colspan="4" class="empty">No listening socket.</td></tr>';
  $('connections-body').innerHTML = connections.map(item => `<tr><td>${escapeHtml(String(item.protocol).toUpperCase())}</td><td>${escapeHtml(socketEndpoint(item, 'local_address', 'local_port'))}</td><td>${escapeHtml(socketEndpoint(item, 'peer_address', 'peer_port'))}</td><td>${escapeHtml(item.state)}</td><td>${escapeHtml(socketProcesses(item))}</td></tr>`).join('') || '<tr><td colspan="5" class="empty">No established connection to a remote peer.</td></tr>';
}
function renderInterfaces() {
  const filter = $('interface-filter').value.trim().toLowerCase();
  const l2 = l2Index();
  const rows = (snapshot.interfaces || []).filter(i => !filter || interfaceHaystack(i).includes(filter) || l2Label(i, l2).toLowerCase().includes(filter));
  $('interfaces-body').innerHTML = rows.map(i => `<tr><td><strong>${escapeHtml(i.ifname)}</strong><small>${escapeHtml([i.link_type, l2Label(i, l2)].filter(Boolean).join(' · '))}</small></td><td>${escapeHtml(i.link_type)}</td><td><span class="state ${String(i.operstate).toLowerCase()}">${escapeHtml(i.operstate)}</span></td><td>${interfaceAddresses(i).map(escapeHtml).join('<br>') || '—'}</td><td>${interfaceTraffic(i)}</td><td>${interfaceHealth(i)}</td><td>${escapeHtml(i.mtu)}</td><td>${escapeHtml(i.master || '—')}</td></tr>`).join('') || '<tr><td colspan="8" class="empty">No matching interface.</td></tr>';
}
function renderRoutes() {
  const filter = $('route-filter').value.trim().toLowerCase();
  const rows = allRoutes().filter(r => !filter || routeHaystack(r).includes(filter));
  $('routes-body').innerHTML = rows.map(r => `<tr><td>${escapeHtml(r.family.toUpperCase())}</td><td><strong>${escapeHtml(r.dst || 'default')}</strong></td><td>${escapeHtml(r.gateway || '—')}</td><td>${escapeHtml(r.dev || '—')}</td><td>${escapeHtml(r.table || 'main')}</td><td>${escapeHtml([r.type, ...(r.flags || [])].filter(Boolean).join(' · ') || r.scope || '—')}</td><td>${escapeHtml(r.metric ?? '—')}</td></tr>`).join('') || '<tr><td colspan="7" class="empty">No matching route.</td></tr>';
  const rules = snapshot.policy_rules || {};
  $('rules-list').innerHTML = Object.entries(rules).map(([family, items]) => `<div class="rule-family"><h3>${escapeHtml(family.toUpperCase())}</h3>${(Array.isArray(items) ? items : []).map(ruleRow).join('') || '<p>No rules.</p>'}</div>`).join('');
}
function ruleRow(rule) {
  const extras = [['fwmark', rule.fwmark], ['iif', rule.iif], ['oif', rule.oif]]
    .filter(([, value]) => value != null && value !== '')
    .map(([label, value]) => `${label} ${value}`)
    .join(' · ');
  return `<div class="rule-row"><b>Priority ${escapeHtml(rule.priority)}</b><span>source ${escapeHtml(rule.src || 'all')}</span><span>table ${escapeHtml(rule.table || '—')}</span>${extras ? `<span>${escapeHtml(extras)}</span>` : ''}</div>`;
}
const FW_VERDICTS = ['accept', 'drop', 'reject', 'jump', 'nat', 'return', 'log', 'other'];
const FW_IFACE_PATTERN = /br-[0-9a-f]+|docker0|veth[0-9a-z]+/gi;
let fwFilter = '';
let fwVerdict = 'all';
let fwGroup = true;
let fwFamily = 'ip';
let fwCy;

const fwStyle = [
  { selector: 'node', style: { label: 'data(label)', 'font-size': 10, 'text-valign': 'center', 'text-halign': 'center', width: 118, height: 34, 'background-color': cssVar('--graph-node-bg'), 'border-width': 1, 'border-color': cssVar('--graph-node-border'), color: cssVar('--graph-label'), 'text-wrap': 'ellipsis', 'text-max-width': 108 } },
  { selector: 'node[kind="hook"]', style: { 'background-color': cssVar('--graph-host-bg'), 'border-color': cssVar('--graph-host-border'), 'font-weight': 700, width: 138 } },
  { selector: 'node[kind="verdict"]', style: { shape: 'round-rectangle', width: 92, height: 30, 'font-weight': 700 } },
  { selector: 'node[verdict="accept"]', style: { 'background-color': '#064e3b', 'border-color': '#34d399', color: '#a7f3d0' } },
  { selector: 'node[verdict="drop"]', style: { 'background-color': '#7f1d1d', 'border-color': '#f87171', color: '#fecaca' } },
  { selector: 'node[verdict="reject"]', style: { 'background-color': '#7c2d12', 'border-color': '#fb923c', color: '#fed7aa' } },
  { selector: 'node[verdict="jump"]', style: { 'background-color': '#1e3a8a', 'border-color': '#60a5fa', color: '#bfdbfe' } },
  { selector: 'node[verdict="nat"]', style: { 'background-color': '#4c1d95', 'border-color': '#c084fc', color: '#e9d5ff' } },
  { selector: 'node[verdict="return"]', style: { 'background-color': '#78350f', 'border-color': '#fbbf24', color: '#fde68a' } },
  { selector: 'node[verdict="log"]', style: { 'background-color': '#334155', 'border-color': '#94a3b8' } },
  { selector: 'edge', style: { width: 1.5, 'line-color': cssVar('--graph-edge'), 'target-arrow-color': cssVar('--graph-arrow'), 'target-arrow-shape': 'triangle', 'curve-style': 'bezier', 'font-size': 9, color: cssVar('--graph-edge-label'), label: 'data(label)', 'text-background-color': cssVar('--graph-edge-label-bg'), 'text-background-opacity': 1, 'text-background-padding': 2 } },
];

function formatBytes(value) {
  if (!value) return '0 B';
  const units = ['B', 'KiB', 'MiB', 'GiB'];
  let size = value;
  let unit = 0;
  while (size >= 1024 && unit < units.length - 1) { size /= 1024; unit += 1; }
  return `${unit === 0 ? Math.round(size) : size.toFixed(1)} ${units[unit]}`;
}

function verdictLabel(rule) {
  if (rule.verdict === 'jump') return `→ ${rule.target || 'chain'}`;
  if (rule.verdict === 'nat') return rule.target || 'NAT';
  return String(rule.verdict).toUpperCase();
}

function ruleHaystack(rule) {
  return [rule.verdict, rule.target, rule.comment, ...(rule.matches || []).map(m => m.text)].filter(Boolean).join(' ').toLowerCase();
}

function buildFirewallGroups(rules) {
  let groups;
  if (fwGroup) {
    groups = [];
    rules.forEach(rule => {
      const signature = [rule.verdict, rule.target || '', rule.comment || '', (rule.matches || []).map(m => m.text.replace(FW_IFACE_PATTERN, '<iface>')).join('|')].join('‖');
      const last = groups[groups.length - 1];
      if (last && last.signature === signature) { last.count += 1; last.rules.push(rule); }
      else groups.push({ rule, rules: [rule], count: 1, signature });
    });
  } else {
    groups = rules.map(rule => ({ rule, rules: [rule], count: 1, signature: null }));
  }
  let maxPackets = 0;
  groups.forEach(group => {
    const counter = group.rules.reduce((sum, rule) => {
      if (!rule.counter) return sum;
      return { packets: sum.packets + rule.counter.packets, bytes: sum.bytes + rule.counter.bytes };
    }, { packets: 0, bytes: 0 });
    group.counter = counter.packets || counter.bytes ? counter : null;
    maxPackets = Math.max(maxPackets, group.counter ? group.counter.packets : 0);
  });
  groups.forEach(group => { group.maxPackets = maxPackets; });
  return groups;
}

function groupMatchesFilter(group) {
  if (fwVerdict !== 'all' && group.rule.verdict !== fwVerdict) return false;
  if (!fwFilter) return true;
  return group.rules.some(rule => ruleHaystack(rule).includes(fwFilter));
}

function renderFirewallGroup(group) {
  const rule = group.rule;
  const matches = (rule.matches || []).map(match => `<span class="fw-match kind-${escapeHtml(match.kind)}">${escapeHtml(match.text)}</span>`).join('');
  const variants = group.count > 1 ? new Set(group.rules.map(item => (item.matches || []).map(m => m.text).join('|'))).size : 0;
  const title = group.count > 1 ? group.rules.map(item => (item.matches || []).map(m => m.text).join(' ')).join('\n') : '';
  const counter = group.counter;
  const percent = counter && group.maxPackets ? Math.max(3, Math.round((counter.packets / group.maxPackets) * 100)) : 0;
  return `<div class="fw-rule v-${escapeHtml(rule.verdict)}">
    <div class="fw-rule-main">
      <span class="fw-verdict v-${escapeHtml(rule.verdict)}">${escapeHtml(verdictLabel(rule))}</span>
      <span class="fw-matches">${matches || '<span class="fw-match">any</span>'}</span>
      ${rule.comment ? `<span class="fw-comment">${escapeHtml(rule.comment)}</span>` : ''}
      ${group.count > 1 ? `<span class="fw-mult" title="${escapeHtml(title)}">×${group.count}${variants > 1 ? ' variants' : ''}</span>` : ''}
    </div>
    <div class="fw-rule-meta">
      ${rule.handle != null ? `<span>#${escapeHtml(rule.handle)}</span>` : ''}
      ${counter ? `<span>${counter.packets.toLocaleString()} pkts · ${formatBytes(counter.bytes)}</span><span class="fw-bar"><i style="width:${percent}%"></i></span>` : ''}
    </div>
  </div>`;
}

function renderFirewallChain(chain) {
  const nameMatch = Boolean(fwFilter && chain.name.toLowerCase().includes(fwFilter));
  const groups = buildFirewallGroups(chain.rules || []).filter(group => groupMatchesFilter(group) || nameMatch);
  if (!groups.length && !nameMatch) return '';
  const policy = chain.policy ? `<span class="fw-policy ${escapeHtml(chain.policy)}">policy ${escapeHtml(chain.policy)}</span>` : '';
  const hook = chain.hook
    ? `<span class="fw-hook">hook ${escapeHtml(chain.hook)}${chain.type ? ` · ${escapeHtml(chain.type)}` : ''}${chain.priority != null ? ` · prio ${escapeHtml(chain.priority)}` : ''}</span>`
    : '<span class="fw-hook">user chain</span>';
  const shown = groups.reduce((sum, group) => sum + group.count, 0);
  return `<div class="fw-chain">
    <div class="fw-chain-head"><div><strong>${escapeHtml(chain.name)}</strong>${hook}</div><div>${policy}<span class="fw-count">${shown}/${chain.stats.rules} rules</span></div></div>
    <div class="fw-rules">${groups.map(renderFirewallGroup).join('') || '<p class="empty">No rule matches the filter.</p>'}</div>
  </div>`;
}

function renderFirewallTable(table) {
  const chains = (table.chains || []).map(renderFirewallChain).filter(Boolean).join('');
  return `<section class="panel fw-table">
    <div class="fw-table-head"><h2>${escapeHtml(table.name)}</h2><span class="fw-table-meta">${escapeHtml(table.family)} · ${table.stats.chains} chains · ${table.stats.rules} rules</span></div>
    ${chains || '<p class="empty">No chain contains rules for the current filter.</p>'}
  </section>`;
}

function renderFirewallTables(view) {
  const all = view.tables || [];
  const matching = all.filter(table => table.family === fwFamily);
  const tables = matching.length ? matching : all;
  $('firewall-tables').innerHTML = tables.map(renderFirewallTable).join('') || '<p class="empty">No firewall table available.</p>';
}

function renderFirewallKpis(view) {
  const totals = view.totals || {};
  const chainCount = (view.tables || []).reduce((sum, table) => sum + (table.chains || []).length, 0);
  $('firewall-kpis').innerHTML = `<span class="fw-kpi"><b>${totals.rules || 0}</b> rules</span><span class="fw-kpi"><b>${(view.tables || []).length}</b> tables</span><span class="fw-kpi"><b>${chainCount}</b> chains</span>`;
  const chips = [`<button class="fw-chip ${fwVerdict === 'all' ? 'active' : ''}" data-verdict="all" aria-pressed="${fwVerdict === 'all'}">ALL <span>${totals.rules || 0}</span></button>`];
  FW_VERDICTS.filter(verdict => totals[verdict]).forEach(verdict => {
    chips.push(`<button class="fw-chip v-${verdict} ${fwVerdict === verdict ? 'active' : ''}" data-verdict="${verdict}" aria-pressed="${fwVerdict === verdict}">${verdict.toUpperCase()} <span>${totals[verdict]}</span></button>`);
  });
  $('firewall-verdicts').innerHTML = chips.join('');
}

function renderFirewallFlow(view) {
  const tables = (view.tables || []).filter(table => table.family === fwFamily);
  const nodes = [];
  const edges = new Map();
  const seen = new Set();
  const addNode = (id, label, kind, extra = {}) => {
    if (seen.has(id)) return;
    seen.add(id);
    nodes.push({ data: { id, label, kind, ...extra } });
  };
  tables.forEach(table => {
    const prefix = `${table.family}:${table.name}`;
    (table.chains || []).forEach(chain => {
      if (!chain.stats.rules && !chain.hook) return;
      const source = `c:${prefix}:${chain.name}`;
      addNode(source, chain.name, chain.hook ? 'hook' : 'chain', { chain: chain.name });
      (chain.rules || []).forEach(rule => {
        if (rule.verdict === 'jump' && rule.target) {
          const target = `c:${prefix}:${rule.target}`;
          addNode(target, rule.target, 'chain', { chain: rule.target });
          addEdge(edges, source, target);
        } else if (['accept', 'drop', 'reject', 'return', 'nat', 'log', 'other'].includes(rule.verdict)) {
          const suffix = rule.verdict === 'nat' ? `:${rule.target || 'NAT'}` : '';
          const target = `v:${rule.verdict}${suffix}`;
          addNode(target, rule.verdict === 'nat' ? (rule.target || 'NAT') : rule.verdict.toUpperCase(), 'verdict', { verdict: rule.verdict });
          addEdge(edges, source, target);
        }
      });
    });
  });
  const hooks = nodes.filter(node => node.data.kind === 'hook').map(node => node.data.id);
  const edgeList = [...edges.entries()].map(([key, count], index) => {
    const [source, target] = key.split('>');
    return { data: { id: `e${index}`, source, target, label: count > 1 ? `×${count}` : '' } };
  });
  if (fwCy) { fwCy.destroy(); fwCy = null; }
  const container = $('fw-graph');
  if (!nodes.length) { container.innerHTML = '<p class="empty">No rule to draw for this family.</p>'; return; }
  container.innerHTML = '';
  fwCy = cytoscape({ container, elements: [...nodes, ...edgeList], style: fwStyle,
    layout: { name: 'breadthfirst', directed: true, roots: hooks, spacingFactor: 1.2, padding: 20, animate: false },
    minZoom: .2, maxZoom: 2.5 });
  fwCy.on('tap', 'node', event => {
    const chain = event.target.data('chain');
    if (!chain) return;
    fwFilter = String(chain).toLowerCase();
    $('firewall-filter').value = chain;
    renderFirewallTables(snapshot.firewall_view || {});
  });
}

function addEdge(edges, source, target) {
  const key = `${source}>${target}`;
  edges.set(key, (edges.get(key) || 0) + 1);
}

function renderFirewall() {
  const view = snapshot.firewall_view || { backend: 'unavailable', available: false, tables: [], totals: {}, warnings: [] };
  const available = Boolean(view.available);
  $('firewall-status').textContent = available ? view.backend : 'Unavailable';
  $('firewall-sub').textContent = available ? `${view.totals.rules || 0} rules readable` : 'Insufficient permissions or missing backend';
  $('firewall-badge').textContent = available ? view.backend : 'Not accessible';
  $('firewall-badge').className = `status-badge ${available ? 'ok' : 'warn'}`;
  let message = available
    ? `Backend detected: ${view.backend}. Rules are read-only and nothing can be modified from this page.`
    : `Toponux could not read the firewall. ${(view.warnings || [])[0] || 'No information available.'}`;
  if (available && (view.warnings || []).length) message += ` Notes: ${view.warnings.join(' · ')}`;
  $('firewall-message').textContent = message;
  $('firewall-raw').textContent = snapshot.firewall && snapshot.firewall.rules != null
    ? JSON.stringify(snapshot.firewall.rules, null, 2)
    : 'No usable rules returned by the collector.';
  if (!available) {
    $('firewall-kpis').innerHTML = '';
    $('firewall-verdicts').innerHTML = '';
    $('firewall-tables').innerHTML = '';
    $('fw-graph').innerHTML = '<p class="empty">Firewall rules are not readable.</p>';
    if (fwCy) { fwCy.destroy(); fwCy = null; }
    return;
  }
  renderFirewallKpis(view);
  renderFirewallTables(view);
  renderFirewallFlow(view);
}
function renderSnapshot() {
  const interfaces = snapshot.interfaces || [];
  const routes = allRoutes();
  $('interface-count').textContent = interfaces.length;
  $('interface-sub').textContent = `${interfaces.filter(i => i.operstate === 'UP').length} up · ${interfaces.filter(i => i.operstate !== 'UP').length} other`;
  $('route-count').textContent = routes.length;
  $('rule-count').textContent = countRules(snapshot.policy_rules || {});
  $('timestamp').textContent = `Collected ${new Date(snapshot.collected_at).toLocaleString()}`;
  $('footer-time').textContent = new Date(snapshot.collected_at).toLocaleTimeString();
  $('errors').textContent = Object.keys(snapshot.errors || {}).length ? JSON.stringify(snapshot.errors, null, 2) : 'No errors reported.';
  $('raw-json').textContent = JSON.stringify(snapshot, null, 2);
  renderFirewall(); renderInterfaces(); renderNeighbors(); renderPorts(); renderRoutes(); renderGraph();
}
let activeDiagnostic = null;

async function readJson(response) {
  const text = await response.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch { data = null; }
  if (!response.ok) throw new Error(data?.detail || `HTTP ${response.status}`);
  return data ?? {};
}

async function refresh() {
  $('refresh').disabled = true; $('refresh').textContent = 'Collecting…';
  try {
    const result = await readJson(await fetch('/api/graph', { cache: 'no-store' }));
    snapshot = result.snapshot; graph = result.graph; renderSnapshot();
    return true;
  } catch (error) { $('errors').textContent = String(error); return false; }
  finally { $('refresh').disabled = false; $('refresh').textContent = 'Refresh'; }
}
function setScanState(busy, message, isError = false) {
  const button = $('scan-subnet');
  const status = $('scan-status');
  button.disabled = busy;
  button.classList.toggle('busy', busy);
  button.setAttribute('aria-busy', String(busy));
  status.textContent = message;
  status.classList.toggle('error', isError);
}
async function scanSubnet() {
  setScanState(true, 'Scanning local IPv4 subnets…');
  try {
    const result = await readJson(await fetch('/api/tools/scan', { method: 'POST' }));
    if (!result.available) throw new Error(result.error || 'Subnet scan is unavailable.');
    setScanState(true, `${result.message} Refreshing the neighbour cache…`);
    const refreshed = await refresh();
    setScanState(false, refreshed ? `${result.message} Graph refreshed.` : `${result.message} Graph refresh failed.`, !refreshed);
  } catch (error) {
    setScanState(false, `Scan failed: ${error.message}`, true);
  }
}

document.querySelectorAll('.tab').forEach(button => button.addEventListener('click', () => {
  document.querySelectorAll('.tab').forEach(b => {
    const active = b === button;
    b.classList.toggle('active', active);
    b.setAttribute('aria-selected', String(active));
  });
  document.querySelectorAll('.tab-content').forEach(panel => panel.classList.toggle('active', panel.id === `tab-${button.dataset.tab}`));
  if (button.dataset.tab === 'overview' && cy) cy.resize();
  if (button.dataset.tab === 'firewall' && fwCy) { fwCy.resize(); fwCy.fit(undefined, 30); }
}));
$('interface-filter').addEventListener('input', renderInterfaces);
$('neighbor-filter').addEventListener('input', renderNeighbors);
$('listener-filter').addEventListener('input', renderPorts);
$('connection-filter').addEventListener('input', renderPorts);
$('route-filter').addEventListener('input', renderRoutes);
$('firewall-filter').addEventListener('input', event => {
  fwFilter = event.target.value.trim().toLowerCase();
  renderFirewallTables(snapshot.firewall_view || {});
});
$('firewall-group').addEventListener('change', event => {
  fwGroup = event.target.checked;
  renderFirewallTables(snapshot.firewall_view || {});
});
$('firewall-verdicts').addEventListener('click', event => {
  const chip = event.target.closest('[data-verdict]');
  if (!chip) return;
  fwVerdict = chip.dataset.verdict;
  renderFirewallKpis(snapshot.firewall_view || {});
  renderFirewallTables(snapshot.firewall_view || {});
});
$('firewall-families').addEventListener('click', event => {
  const button = event.target.closest('[data-family]');
  if (!button) return;
  fwFamily = button.dataset.family;
  document.querySelectorAll('#firewall-families [data-family]').forEach(item => {
    const active = item === button;
    item.classList.toggle('active', active);
    item.setAttribute('aria-pressed', String(active));
  });
  renderFirewallTables(snapshot.firewall_view || {});
  renderFirewallFlow(snapshot.firewall_view || {});
});
$('refresh').addEventListener('click', refresh);
$('scan-subnet').addEventListener('click', scanSubnet);
['graph-ipv6', 'graph-docker'].forEach(id => $(id).addEventListener('change', renderGraph));
refresh();


function renderIpv6Report(data) {
  const lines = [
    `Address     ${data.address}`,
    `Expanded    ${data.exploded}`,
    `Type        ${data.type}`,
  ];
  if (data.zone) lines.push(`Zone        ${data.zone}`);
  if (data.prefixlen != null) lines.push(`Prefix      /${data.prefixlen} · network ${data.network}`);
  if (data.well_known.length) lines.push(`Well-known  ${data.well_known.join(', ')}`);
  lines.push('', `Header      ${data.binary} …`);
  for (const flag of data.flags) lines.push(`  ${flag.name.padEnd(6)} ${flag.value}  ${flag.meaning}`);
  if (data.multicast_scope) lines.push(`  Scope value ${data.multicast_scope}`);
  const properties = Object.entries(data.properties).filter(([, value]) => value).map(([name]) => name.replaceAll('_', ' '));
  lines.push('', `Properties  ${properties.join(', ') || 'none'}`, `Reverse DNS ${data.reverse_dns}`);
  return lines.join('\n');
}

async function postDiagnostic(path, payload, outputId, button) {
  const output = $(outputId);
  if (activeDiagnostic) activeDiagnostic.abort();
  const controller = new AbortController();
  activeDiagnostic = controller;
  button.disabled = true; output.textContent = 'Diagnostic running…';
  try {
    const response = await fetch(path, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload), signal: controller.signal});
    const data = await readJson(response);
    output.textContent = data.output || data.interpretation || data.error || JSON.stringify(data, null, 2);
    if (data.route?.output) output.textContent += `\n\nSelected local route:\n${data.route.output}`;
    if (data.interpretation) output.textContent += `\n\n${data.interpretation}`;
  } catch (error) {
    output.textContent = error.name === 'AbortError' ? 'Diagnostic cancelled.' : `Error: ${error.message}`;
  } finally {
    button.disabled = false;
    if (activeDiagnostic === controller) activeDiagnostic = null;
  }
}
function downloadText(filename, content, type) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function firewallRulesCsv(view) {
  const rows = [['table', 'family', 'chain', 'handle', 'verdict', 'target', 'matches', 'comment', 'packets', 'bytes']];
  for (const table of view.tables || []) {
    for (const chain of table.chains || []) {
      for (const rule of chain.rules || []) {
        const counter = rule.counter || {};
        rows.push([
          table.name, table.family, chain.name, rule.handle ?? '', rule.verdict || '', rule.target || '',
          (rule.matches || []).map(match => match.text).join('; '), rule.comment || '',
          counter.packets ?? '', counter.bytes ?? '',
        ]);
      }
    }
  }
  return rows.map(row => row.map(value => `"${String(value).replaceAll('"', '""')}"`).join(',')).join('\n');
}

$('fw-copy-command').addEventListener('click', async () => {
  const view = snapshot.firewall_view || {};
  const command = view.command || (view.backend === 'iptables' ? 'iptables-save' : 'nft -j list ruleset');
  try {
    await navigator.clipboard.writeText(command);
    $('firewall-message').textContent = `Copied: ${command}`;
  } catch (error) {
    $('firewall-message').textContent = command;
  }
});
$('fw-export-json').addEventListener('click', () => {
  downloadText('toponux-firewall.json', JSON.stringify(snapshot.firewall_view || {}, null, 2), 'application/json');
});
$('fw-export-csv').addEventListener('click', () => {
  downloadText('toponux-firewall.csv', firewallRulesCsv(snapshot.firewall_view || {}), 'text/csv');
});
$('run-trace').addEventListener('click', () => postDiagnostic('/api/tools/trace', {target:$('path-target').value, max_hops:Number($('trace-hops').value)}, 'path-result', $('run-trace')));
$('port-form').addEventListener('submit', event => { event.preventDefault(); postDiagnostic('/api/tools/port', {target:$('port-target').value, port:Number($('port-number').value), timeout:Number($('port-timeout').value)}, 'port-result', $('port-form').querySelector('button')); });
$('ipv6-form').addEventListener('submit', async event => {
  event.preventDefault();
  const output = $('ipv6-result');
  const button = event.target.querySelector('button');
  button.disabled = true; output.textContent = 'Inspecting…';
  try {
    const response = await fetch('/api/tools/ipv6', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({target:$('ipv6-target').value})});
    output.textContent = renderIpv6Report(await readJson(response));
  } catch (error) {
    output.textContent = `Error: ${error.message}`;
  } finally {
    button.disabled = false;
  }
});
