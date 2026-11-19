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
  { selector: 'node[kind="gateway"]', style: { 'background-color': cssVar('--graph-gateway-bg'), 'border-color': cssVar('--graph-gateway-border'), shape: 'diamond', width: 130, height: 90 } },
  { selector: 'edge', style: { width: 2, 'line-color': cssVar('--graph-edge'), 'target-arrow-color': cssVar('--graph-arrow'), 'target-arrow-shape': 'triangle', 'curve-style': 'bezier', label: 'data(label)', 'font-size': 9, color: cssVar('--graph-edge-label'), 'text-background-color': cssVar('--graph-edge-label-bg'), 'text-background-opacity': 1, 'text-background-padding': 3 } },
  { selector: ':selected', style: { 'border-width': 3, 'border-color': cssVar('--graph-selected') } },
];

function countRules(rules = {}) { return (Array.isArray(rules.ipv4) ? rules.ipv4.length : 0) + (Array.isArray(rules.ipv6) ? rules.ipv6.length : 0); }
function allRoutes() { return Object.entries(snapshot.routes || {}).flatMap(([family, routes]) => (Array.isArray(routes) ? routes : []).map(route => ({ family, ...route }))); }
function interfaceAddresses(iface) { return (iface.addr_info || []).map(a => `${a.local}/${a.prefixlen}`); }
function interfaceHaystack(iface) {
  return [iface.ifname, iface.link_type, iface.operstate, iface.master, iface.mtu, ...interfaceAddresses(iface)]
    .filter(value => value != null).join(' ').toLowerCase();
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
function renderGraph() {
  if (cy) cy.destroy();
  cy = cytoscape({ container: $('cy'), elements: [...(graph.nodes || []), ...(graph.edges || [])], style: graphStyle,
    layout: { name: 'breadthfirst', directed: true, roots: '#host', spacingFactor: 1.35, padding: 45, animate: false }, minZoom: .25, maxZoom: 3 });
  cy.on('tap', 'node', event => showDetails(event.target.data()));
  cy.on('tap', event => { if (event.target === cy) { $('detail-hint').textContent = 'Select an element in the graph.'; $('details').textContent = 'Nothing selected.'; } });
}
function renderInterfaces() {
  const filter = $('interface-filter').value.trim().toLowerCase();
  const rows = (snapshot.interfaces || []).filter(i => !filter || interfaceHaystack(i).includes(filter));
  $('interfaces-body').innerHTML = rows.map(i => `<tr><td><strong>${escapeHtml(i.ifname)}</strong><small>${escapeHtml(i.link_type || '—')}</small></td><td>${escapeHtml(i.link_type)}</td><td><span class="state ${String(i.operstate).toLowerCase()}">${escapeHtml(i.operstate)}</span></td><td>${interfaceAddresses(i).map(escapeHtml).join('<br>') || '—'}</td><td>${escapeHtml(i.mtu)}</td><td>${escapeHtml(i.master || '—')}</td></tr>`).join('') || '<tr><td colspan="6" class="empty">No matching interface.</td></tr>';
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
function renderFirewall() {
  const fw = snapshot.firewall || {};
  const available = Boolean(fw.backend && fw.backend !== 'unavailable' && fw.rules != null);
  $('firewall-status').textContent = available ? fw.backend : 'Unavailable';
  $('firewall-sub').textContent = available ? 'Rules readable' : 'Insufficient permissions or missing backend';
  $('firewall-badge').textContent = available ? fw.backend : 'Not accessible';
  $('firewall-badge').className = `status-badge ${available ? 'ok' : 'warn'}`;
  let message = available
    ? `Backend detected: ${fw.backend}. The rules below are readable in read-only mode.`
    : `Toponux could not read the firewall. ${fw.error || fw.nft_error || 'No information available.'}`;
  if (available && fw.nft_error) message += ` nftables unavailable (${fw.nft_error}): falling back to iptables.`;
  $('firewall-message').textContent = message;
  $('firewall-raw').textContent = fw.rules != null ? JSON.stringify(fw.rules, null, 2) : 'No usable rules returned by the collector.';
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
  renderFirewall(); renderInterfaces(); renderRoutes(); renderGraph();
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
  } catch (error) { $('errors').textContent = String(error); }
  finally { $('refresh').disabled = false; $('refresh').textContent = 'Refresh'; }
}

document.querySelectorAll('.tab').forEach(button => button.addEventListener('click', () => {
  document.querySelectorAll('.tab').forEach(b => {
    const active = b === button;
    b.classList.toggle('active', active);
    b.setAttribute('aria-selected', String(active));
  });
  document.querySelectorAll('.tab-content').forEach(panel => panel.classList.toggle('active', panel.id === `tab-${button.dataset.tab}`));
  if (button.dataset.tab === 'overview' && cy) cy.resize();
}));
$('interface-filter').addEventListener('input', renderInterfaces);
$('route-filter').addEventListener('input', renderRoutes);
$('refresh').addEventListener('click', refresh);
refresh();


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
$('run-ping').addEventListener('click', () => postDiagnostic('/api/tools/ping', {target:$('path-target').value, count:Number($('ping-count').value)}, 'path-result', $('run-ping')));
$('run-trace').addEventListener('click', () => postDiagnostic('/api/tools/trace', {target:$('path-target').value, max_hops:Number($('trace-hops').value)}, 'path-result', $('run-trace')));
$('port-form').addEventListener('submit', event => { event.preventDefault(); postDiagnostic('/api/tools/port', {target:$('port-target').value, port:Number($('port-number').value), timeout:Number($('port-timeout').value)}, 'port-result', $('port-form').querySelector('button')); });
