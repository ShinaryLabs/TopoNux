const $ = (id) => document.getElementById(id);
let cy;
let snapshot = {};
let graph = {};

const graphStyle = [
  { selector: 'node', style: { label: 'data(label)', 'text-wrap': 'wrap', 'text-max-width': 170, 'font-size': 11, color: '#e5e7eb', 'text-valign': 'center', 'text-halign': 'center', width: 150, height: 66, 'background-color': '#334155', 'border-width': 1, 'border-color': '#64748b', padding: 8 } },
  { selector: 'node[kind="host"]', style: { 'background-color': '#1e3a8a', 'border-color': '#60a5fa', width: 190, height: 90, 'font-size': 15, 'font-weight': 700, shape: 'round-rectangle' } },
  { selector: 'node[kind="interface"]', style: { 'background-color': '#1d4ed8', 'border-color': '#60a5fa', shape: 'round-rectangle' } },
  { selector: 'node[kind="bridge"]', style: { 'background-color': '#047857', 'border-color': '#34d399', shape: 'round-rectangle' } },
  { selector: 'node[kind="gateway"]', style: { 'background-color': '#92400e', 'border-color': '#fbbf24', shape: 'diamond', width: 130, height: 90 } },
  { selector: 'edge', style: { width: 2, 'line-color': '#64748b', 'target-arrow-color': '#94a3b8', 'target-arrow-shape': 'triangle', 'curve-style': 'bezier', label: 'data(label)', 'font-size': 9, color: '#94a3b8', 'text-background-color': '#111c2e', 'text-background-opacity': 1, 'text-background-padding': 3 } },
  { selector: ':selected', style: { 'border-width': 3, 'border-color': '#f8fafc' } },
];

function countRules(rules = {}) { return (Array.isArray(rules.ipv4) ? rules.ipv4.length : 0) + (Array.isArray(rules.ipv6) ? rules.ipv6.length : 0); }
function allRoutes() { return Object.entries(snapshot.routes || {}).flatMap(([family, routes]) => (Array.isArray(routes) ? routes : []).map(route => ({ family, ...route }))); }
function interfaceAddresses(iface) { return (iface.addr_info || []).map(a => `${a.local}/${a.prefixlen}`); }
function escapeHtml(value) { return String(value ?? '—').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
function showDetails(data) {
  $('detail-hint').textContent = data.kind === 'host' ? 'Machine locale' : data.name || data.kind;
  $('details').textContent = data.details || 'Aucun détail supplémentaire.';
}
function renderGraph() {
  if (cy) cy.destroy();
  cy = cytoscape({ container: $('cy'), elements: [...(graph.nodes || []), ...(graph.edges || [])], style: graphStyle,
    layout: { name: 'breadthfirst', directed: true, roots: '#host', spacingFactor: 1.35, padding: 45, animate: false }, minZoom: .25, maxZoom: 3 });
  cy.on('tap', 'node', event => showDetails(event.target.data()));
  cy.on('tap', event => { if (event.target === cy) { $('detail-hint').textContent = 'Sélectionne un élément du graphe.'; $('details').textContent = 'Aucun élément sélectionné.'; } });
}
function renderInterfaces() {
  const filter = $('interface-filter').value.toLowerCase();
  const rows = (snapshot.interfaces || []).filter(i => JSON.stringify(i).toLowerCase().includes(filter));
  $('interfaces-body').innerHTML = rows.map(i => `<tr><td><strong>${escapeHtml(i.ifname)}</strong><small>${escapeHtml(i.link_type || '—')}</small></td><td>${escapeHtml(i.link_type)}</td><td><span class="state ${String(i.operstate).toLowerCase()}">${escapeHtml(i.operstate)}</span></td><td>${interfaceAddresses(i).map(escapeHtml).join('<br>') || '—'}</td><td>${escapeHtml(i.mtu)}</td><td>${escapeHtml(i.master || '—')}</td></tr>`).join('') || '<tr><td colspan="6" class="empty">Aucune interface correspondante.</td></tr>';
}
function renderRoutes() {
  const filter = $('route-filter').value.toLowerCase();
  const rows = allRoutes().filter(r => JSON.stringify(r).toLowerCase().includes(filter));
  $('routes-body').innerHTML = rows.map(r => `<tr><td>${escapeHtml(r.family.toUpperCase())}</td><td><strong>${escapeHtml(r.dst || 'default')}</strong></td><td>${escapeHtml(r.gateway || '—')}</td><td>${escapeHtml(r.dev || '—')}</td><td>${escapeHtml(r.table || 'main')}</td><td>${escapeHtml([r.type, ...(r.flags || [])].filter(Boolean).join(' · ') || r.scope || '—')}</td><td>${escapeHtml(r.metric ?? '—')}</td></tr>`).join('') || '<tr><td colspan="7" class="empty">Aucune route correspondante.</td></tr>';
  const rules = snapshot.policy_rules || {};
  $('rules-list').innerHTML = Object.entries(rules).map(([family, items]) => `<div class="rule-family"><h3>${escapeHtml(family.toUpperCase())}</h3>${(Array.isArray(items) ? items : []).map(r => `<div class="rule-row"><b>Priorité ${escapeHtml(r.priority)}</b><span>source ${escapeHtml(r.src || 'all')}</span><span>table ${escapeHtml(r.table || '—')}</span></div>`).join('') || '<p>Aucune règle.</p>'}</div>`).join('');
}
function renderFirewall() {
  const fw = snapshot.firewall || {};
  const available = Boolean(fw.backend && fw.backend !== 'unavailable' && fw.rules != null);
  $('firewall-status').textContent = available ? fw.backend : 'Indisponible';
  $('firewall-sub').textContent = available ? 'Règles accessibles' : 'Permissions insuffisantes ou backend absent';
  $('firewall-badge').textContent = available ? fw.backend : 'Non accessible';
  $('firewall-badge').className = `status-badge ${available ? 'ok' : 'warn'}`;
  let message = available
    ? `Backend détecté : ${fw.backend}. Les règles ci-dessous sont consultables en lecture seule.`
    : `Toponux n'a pas pu lire le firewall. ${fw.error || fw.nft_error || 'Aucune information disponible.'}`;
  if (available && fw.nft_error) message += ` nftables indisponible (${fw.nft_error}) : repli sur iptables.`;
  $('firewall-message').textContent = message;
  $('firewall-raw').textContent = fw.rules != null ? JSON.stringify(fw.rules, null, 2) : 'Aucune règle exploitable retournée par le collecteur.';
}
function renderSnapshot() {
  const interfaces = snapshot.interfaces || [];
  const routes = allRoutes();
  $('interface-count').textContent = interfaces.length;
  $('interface-sub').textContent = `${interfaces.filter(i => i.operstate === 'UP').length} actives · ${interfaces.filter(i => i.operstate !== 'UP').length} autres`;
  $('route-count').textContent = routes.length;
  $('rule-count').textContent = countRules(snapshot.policy_rules || {});
  $('timestamp').textContent = `Collecté le ${new Date(snapshot.collected_at).toLocaleString('fr-FR')}`;
  $('footer-time').textContent = new Date(snapshot.collected_at).toLocaleTimeString('fr-FR');
  $('errors').textContent = Object.keys(snapshot.errors || {}).length ? JSON.stringify(snapshot.errors, null, 2) : 'Aucune erreur signalée.';
  $('raw-json').textContent = JSON.stringify(snapshot, null, 2);
  renderFirewall(); renderInterfaces(); renderRoutes(); renderGraph();
}
async function refresh() {
  $('refresh').disabled = true; $('refresh').textContent = 'Collecte…';
  try {
    const response = await fetch('/api/graph', { cache: 'no-store' });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const result = await response.json(); snapshot = result.snapshot; graph = result.graph; renderSnapshot();
  } catch (error) { $('errors').textContent = String(error); }
  finally { $('refresh').disabled = false; $('refresh').textContent = 'Actualiser'; }
}

document.querySelectorAll('.tab').forEach(button => button.addEventListener('click', () => {
  document.querySelectorAll('.tab').forEach(b => b.classList.toggle('active', b === button));
  document.querySelectorAll('.tab-content').forEach(panel => panel.classList.toggle('active', panel.id === `tab-${button.dataset.tab}`));
  if (button.dataset.tab === 'overview' && cy) cy.resize();
}));
$('interface-filter').addEventListener('input', renderInterfaces);
$('route-filter').addEventListener('input', renderRoutes);
$('refresh').addEventListener('click', refresh);
refresh();


async function postDiagnostic(path, payload, outputId, button) {
  const output = $(outputId); button.disabled = true; output.textContent = 'Diagnostic en cours…';
  try {
    const response = await fetch(path, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)});
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
    output.textContent = data.output || data.interpretation || data.error || JSON.stringify(data, null, 2);
    if (data.route?.output) output.textContent += `\n\nRoute locale sélectionnée :\n${data.route.output}`;
    if (data.interpretation) output.textContent += `\n\n${data.interpretation}`;
  } catch (error) { output.textContent = `Erreur : ${error.message}`; }
  finally { button.disabled = false; }
}
$('run-ping').addEventListener('click', () => postDiagnostic('/api/tools/ping', {target:$('path-target').value, count:Number($('ping-count').value)}, 'path-result', $('run-ping')));
$('run-trace').addEventListener('click', () => postDiagnostic('/api/tools/trace', {target:$('path-target').value, max_hops:Number($('trace-hops').value)}, 'path-result', $('run-trace')));
$('port-form').addEventListener('submit', event => { event.preventDefault(); postDiagnostic('/api/tools/port', {target:$('port-target').value, port:Number($('port-number').value), timeout:Number($('port-timeout').value)}, 'port-result', $('port-form').querySelector('button')); });
