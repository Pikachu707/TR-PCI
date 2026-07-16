#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import http.server
import socketserver
import json
import os
import glob
import sys
import math
import random
import time

# Try importing graph libraries
try:
    import igraph as ig

    LEIDEN_AVAILABLE = True
except ImportError:
    print("[-] Warning: 'igraph' not found. Algorithms will be disabled.")
    LEIDEN_AVAILABLE = False

# ============================================================================
# 1. Frontend Template (Bidirectional Context Isolation)
# ============================================================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8"><title>Topology-Regularized Reverse Causal Inference
for Points of Interest (POI) Identification</title>
    <script src="https://cdn.staticfile.org/vis-network/9.1.2/dist/vis-network.min.js"></script>
    <style type="text/css">
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #121212; color: #e0e0e0; margin: 0; overflow: hidden; display: flex; height: 100vh; }
        #sidebar-left { width: 300px; background: #1e1e1e; border-right: 1px solid #333; display: flex; flex-direction: column; z-index: 20; box-shadow: 4px 0 15px rgba(0,0,0,0.5); }
        .sidebar-header { padding: 15px; background: #252526; border-bottom: 1px solid #333; }
        .view-selector { width: 100%; padding: 8px; background: #121212; color: #fff; border: 1px solid #444; border-radius: 4px; outline: none; font-family: monospace; font-size: 12px; cursor: pointer; }
        .info-box { padding: 15px; font-size: 12px; color: #888; border-bottom: 1px solid #333; }
        #main-area { flex: 1; position: relative; background: #121212; }
        #mynetwork { width: 100%; height: 100%; }
        .controls { position: absolute; top: 15px; right: 20px; z-index: 10; display: flex; gap: 10px; }
        .btn { background: #2d2d30; border: 1px solid #444; color: #ccc; padding: 6px 12px; cursor: pointer; border-radius: 4px; font-size: 12px; font-weight: 600; transition: all 0.2s; }
        .btn:hover { background: #3e3e42; color: #fff; border-color: #61dafb; }
        .btn-active { background: #0e639c; border-color: #1177bb; color: white; }

        /* LEGEND STYLES */
        .legend { position: absolute; bottom: 20px; right: 20px; background: rgba(30, 30, 30, 0.9); padding: 12px; border-radius: 6px; border: 1px solid #444; pointer-events: none; display: flex; flex-direction: column; gap: 8px; backdrop-filter: blur(4px); box-shadow: 0 4px 10px rgba(0,0,0,0.5); }
        .l-item { display: flex; align-items: center; font-size: 11px; color: #ccc; }
        .shape { display: inline-block; margin-right: 10px; vertical-align: middle; }

        .shape.proc { width: 10px; height: 10px; border-radius: 50%; background: #3498db; }
        .shape.file { width: 10px; height: 10px; border-radius: 2px; background: #f1c40f; }
        .shape.net  { width: 8px; height: 8px; transform: rotate(45deg); background: #2ecc71; }
        .shape.c2   { width: 12px; height: 12px; transform: rotate(45deg); background: #ff0000; border: 2px solid #fff; }

        .shape.line-solid { width: 25px; height: 3px; background: #00d2d3; }
        .shape.line-attack { width: 25px; height: 3px; background: #9b59b6; } 

        /* Threat Lines */
        .shape.line-memfd  { width: 25px; height: 0; border-bottom: 2px dashed #e67e22; } 
        .shape.line-ptrace { width: 25px; height: 0; border-bottom: 2px dashed #e74c3c; } 
        .shape.line-mmap   { width: 25px; height: 3px; background: #e74c3c; } 

        #detail-panel { position: fixed; top: 0; right: -450px; width: 450px; height: 100vh; background: #1e1e1e; border-left: 1px solid #444; transition: right 0.3s cubic-bezier(0.16, 1, 0.3, 1); z-index: 30; display: flex; flex-direction: column; }
        #detail-panel.open { right: 0; }
        .detail-content { flex: 1; overflow-y: auto; padding: 25px; }
        .close-btn { position: absolute; top: 15px; right: 20px; cursor: pointer; color: #666; font-size: 24px; }
        h2 { color: #61dafb; border-bottom: 1px solid #444; padding-bottom: 10px; margin-top: 0; word-break: break-all; }
        .field-label { font-size: 10px; color: #666; margin-top: 12px; font-weight: bold; text-transform: uppercase; letter-spacing: 0.5px; }
        .field-value { font-family: 'Consolas', monospace; font-size: 12px; color: #d4d4d4; background: #121212; padding: 8px; border: 1px solid #333; border-radius: 4px; word-break: break-all; margin-top: 4px; white-space: pre-wrap; }
        .poi-box { background: rgba(155, 89, 182, 0.15); border: 1px solid #9b59b6; padding: 10px; margin-bottom: 15px; border-radius: 4px; }

        .file-list { list-style-type: none; padding: 0; margin: 0; }
        .file-list li { padding: 4px 0; border-bottom: 1px solid #333; color: #ccc; }
        .file-list li:last-child { border-bottom: none; }

        /* Filter Indicator */
        #filter-indicator { position: absolute; top: 60px; right: 20px; background: rgba(155, 89, 182, 0.2); border: 1px solid #9b59b6; color: #fff; padding: 8px 12px; border-radius: 4px; font-size: 12px; pointer-events: none; display: none; backdrop-filter: blur(4px); }
    </style>
</head>
<body>

<div id="sidebar-left">
    <div class="sidebar-header">
        <div style="font-size:14px; font-weight:bold; color:#61dafb; margin-bottom:10px;">Topology-Regularized Reverse Causal Inference</div>
        <select id="view-selector" class="view-selector" onchange="switchView()"></select>
    </div>
    <div class="info-box">
        <div><strong>TR-PCI:</strong> Causal Backbone Inference</div>
        <div style="margin-top:5px"><strong>R-CSDA:</strong> Hybrid Semantic Analysis</div>
        <div style="margin-top:10px; color:#61dafb">★ Click Node: Isolate Context<br>★ Click Empty: Reset View</div>
    </div>
</div>

<div id="main-area">
    <div class="controls">
        <button class="btn" onclick="fitGraph()">🔍 Fit Graph</button>
        <button class="btn" id="btn-physics" onclick="togglePhysics()">▶️ Resume Physics</button>
    </div>
    <div id="filter-indicator">⚠️ FULL CONTEXT ISOLATION ACTIVE</div>
    <div id="mynetwork"></div>

    <div class="legend">
        <div class="l-item"><div class="shape c2"></div><strong>Suspected C2 Node</strong></div>
        <div class="l-item"><div class="shape line-attack"></div><strong>Attack Traceback</strong></div>
        <div class="l-item"><div class="shape line-solid"></div><strong>Causal Backbone</strong></div>
        <div style="margin: 5px 0; border-top: 1px solid #444;"></div>
        <div class="l-item"><div class="shape proc"></div>Process (Blue)</div>
        <div class="l-item"><div class="shape file"></div>File/Cluster (Yellow)</div>
        <div class="l-item"><div class="shape net"></div>Network (Green)</div>
        <div style="margin: 5px 0; border-top: 1px solid #444;"></div>
        <div class="l-item"><div class="shape line-memfd"></div>MemFD (Fileless)</div>
        <div class="l-item"><div class="shape line-ptrace"></div>Ptrace (Injection)</div>
        <div class="l-item"><div class="shape line-mmap"></div>Shellcode (RWX)</div>
    </div>
</div>

<div id="detail-panel">
    <div class="close-btn" onclick="closeDetail()">×</div>
    <div class="detail-content" id="detail-content"></div>
</div>

<script type="text/javascript">
    var snapshots = __SNAPSHOTS_JSON__;
    var network = null;
    var nodesDataSet = new vis.DataSet([]);
    var edgesDataSet = new vis.DataSet([]);
    var physicsEnabled = false;
    var isFiltered = false; 

    var selector = document.getElementById('view-selector');
    var keys = Object.keys(snapshots).sort();

    if (keys.length === 0) {
        selector.innerHTML = "<option>No Data Available</option>";
    } else {
        keys.forEach(key => {
            var opt = document.createElement("option");
            opt.value = key;
            opt.text = "📄 " + key;
            selector.appendChild(opt);
        });
        loadView(keys[0]);
    }

    function switchView() { loadView(document.getElementById('view-selector').value); }

    function loadView(key) {
        var data = snapshots[key];
        if (!data) return;

        nodesDataSet.clear(); 
        edgesDataSet.clear();
        nodesDataSet.add(data.nodes);
        edgesDataSet.add(data.edges);

        isFiltered = false;
        document.getElementById('filter-indicator').style.display = 'none';

        var container = document.getElementById('mynetwork');
        var options = {
            nodes: { 
                font: { color: '#e0e0e0', size: 14, face: 'Segoe UI' }, 
                borderWidth: 2,
                shapeProperties: { interpolation: false } 
            },
            // ==========================================
            // Frontend fix: use enabled: true together with roundness: 0.0.
            // This keeps edges between nodes straight while still rendering
            // self-loop circles correctly.
            // ==========================================
            edges: { 
                arrows: 'to', 
                smooth: {
                    enabled: true,
                    type: 'continuous',
                    roundness: 0.0
                }
            },
            physics: { 
                enabled: false,
                solver: 'forceAtlas2Based', 
                forceAtlas2Based: { gravitationalConstant: -50, springLength: 100, avoidOverlap: 0.5 },
                stabilization: { iterations: 100 }
            },
            interaction: { hover: true, navigationButtons: false, hideEdgesOnDrag: true }
        };

        if (network) network.destroy();
        network = new vis.Network(container, { nodes: nodesDataSet, edges: edgesDataSet }, options);

        network.on("click", function (params) {
            if (params.nodes.length > 0) {
                var nodeId = params.nodes[0];
                var node = nodesDataSet.get(nodeId);
                showDetail(node);
                isolateContextVis(nodeId);
            } else if (params.edges.length > 0) {
                var edgeId = params.edges[0];
                var edge = edgesDataSet.get(edgeId);
                if (edge.extra) showEdgeDetail(edge);
                else { closeDetail(); resetVis(); }
            } else {
                closeDetail();
                resetVis();
            }
        });
        physicsEnabled = false;
        updatePhysicsBtn();
    }

    // --- Bidirectional Context Isolation ---
    function isolateContextVis(rootId) {
        var allEdges = edgesDataSet.get();
        var parentMap = {}; 
        var childMap = {};  

        allEdges.forEach(e => {
            if(!parentMap[e.to]) parentMap[e.to] = [];
            parentMap[e.to].push(e.from);
            if(!childMap[e.from]) childMap[e.from] = [];
            childMap[e.from].push(e.to);
        });

        var keep = new Set([rootId]);

        // 1. Ancestors
        var stack = [rootId];
        while(stack.length > 0){
            var curr = stack.pop();
            var parents = parentMap[curr] || [];
            parents.forEach(p => {
                if(!keep.has(p)){
                    keep.add(p);
                    stack.push(p);
                }
            });
        }

        // 2. Descendants
        stack = [rootId];
        while(stack.length > 0){
            var curr = stack.pop();
            var children = childMap[curr] || [];
            children.forEach(c => {
                if(!keep.has(c)){
                    keep.add(c);
                    stack.push(c);
                }
            });
        }

        // 3. Filter
        var nodeUpdates = nodesDataSet.getIds().map(id => ({
            id: id, 
            hidden: !keep.has(id),
            opacity: keep.has(id) ? 1.0 : 0.05
        }));
        nodesDataSet.update(nodeUpdates);

        var edgeUpdates = allEdges.map(e => ({
            id: e.id, 
            hidden: !(keep.has(e.from) && keep.has(e.to)) 
        }));
        edgesDataSet.update(edgeUpdates);

        isFiltered = true;
        document.getElementById('filter-indicator').style.display = 'block';
    }

    function resetVis() {
        if(!isFiltered) return;
        var nodeUpdates = nodesDataSet.getIds().map(id => ({id: id, hidden: false, opacity: 1.0}));
        nodesDataSet.update(nodeUpdates);
        var edgeUpdates = edgesDataSet.getIds().map(id => ({id: id, hidden: false}));
        edgesDataSet.update(edgeUpdates);
        isFiltered = false;
        document.getElementById('filter-indicator').style.display = 'none';
    }

    function fitGraph() { if(network) network.fit({animation: {duration: 500, easingFunction: 'easeInOutQuad'}}); }

    function togglePhysics() {
        if(!network) return;
        physicsEnabled = !physicsEnabled;
        network.setOptions({ physics: { enabled: physicsEnabled } });
        updatePhysicsBtn();
    }

    function updatePhysicsBtn() {
        var btn = document.getElementById('btn-physics');
        if(physicsEnabled) {
            btn.innerText = "⏸️ Pause Physics";
            btn.classList.remove('btn-active');
        } else {
            btn.innerText = "▶️ Resume Physics";
            btn.classList.add('btn-active');
        }
    }

    function showEdgeDetail(edge) {
        var html = '<h2>Operation Detail</h2>';
        var extra = edge.extra || {};
        var color = (typeof edge.color === 'object') ? edge.color.color : edge.color;
        html += '<div class="field-label">ACTION</div>';
        html += '<div class="field-value" style="color:' + color + '">' + edge.label.replace("\\n", " ") + '</div>';
        for (var key in extra) {
            html += '<div class="field-label">' + key.toUpperCase() + '</div>';
            html += '<div class="field-value">' + extra[key] + '</div>';
        }
        document.getElementById('detail-content').innerHTML = html;
        document.getElementById('detail-panel').classList.add('open');
    }

    function showDetail(node) {
        var html = '<h2>' + node.label.split("\\n")[0] + '</h2>';
        var extra = node.extra || {};

        if (extra.poi_type) {
             html += '<div class="poi-box">';
             html += '<strong style="color:#9b59b6">🛡️ ' + extra.poi_type + '</strong><br>';
             if(extra.path_score) html += '<div style="margin-top:5px"><strong>Chain Score:</strong> ' + extra.path_score.toFixed(2) + '</div>';
             html += '</div>';
        }

        if (extra.cmd) {
            html += '<div class="field-label">Command Line</div>';
            html += '<div class="field-value" style="color:#61dafb">' + extra.cmd + '</div>';
        }

        if (extra.file_list && Array.isArray(extra.file_list)) {
            html += '<div class="field-label">📁 AGGREGATED FILES (' + extra.file_list.length + ')</div>';
            html += '<div class="field-value" style="max-height:200px; overflow-y:auto;">';
            html += '<ul class="file-list">';
            extra.file_list.forEach(function(f) {
                html += '<li>' + f + '</li>';
            });
            html += '</ul></div>';
        }

        for (var key in extra) {
            if (['poi_score', 'tr_pci_mass', 'cmd', 'label', 'poi_type', 'path_score', 'file_list'].indexOf(key) === -1) {
                html += '<div class="field-label">' + key.toUpperCase() + '</div>';
                html += '<div class="field-value">' + extra[key] + '</div>';
            }
        }
        document.getElementById('detail-content').innerHTML = html;
        document.getElementById('detail-panel').classList.add('open');
    }
    function closeDetail() { document.getElementById('detail-panel').classList.remove('open'); }
</script>
</body>
</html>
"""


# ============================================================================
# 2. TR-PCI: Causal Backbone
# ============================================================================
class TRPCI_Engine:
    def __init__(self, nodes, edges):
        self.nodes = nodes
        self.edges = edges
        self.id_map = {n['id']: i for i, n in enumerate(nodes)}
        self.rev_map = {i: n['id'] for i, n in enumerate(nodes)}
        self.g = ig.Graph(directed=True)
        self.g.add_vertices(len(nodes))
        ig_edges = []
        self.edge_indices = []
        for e in edges:
            if e['from'] in self.id_map and e['to'] in self.id_map:
                ig_edges.append((self.id_map[e['from']], self.id_map[e['to']]))
                self.edge_indices.append(e)
        self.g.add_edges(ig_edges)

    def compute_backbone(self, alpha=0.5, beta=0.5, threshold_percentile=70):
        if len(self.nodes) < 2: return {}, []
        try:
            pr = self.g.pagerank()
            cb = self.g.betweenness(directed=True, cutoff=20)
        except Exception:
            return {}, []

        max_pr = max(pr) if pr else 1
        max_cb = max(cb) if cb else 1
        node_mass = {}
        for idx, node_id in self.rev_map.items():
            norm_pr = pr[idx] / max_pr if max_pr > 0 else 0
            norm_cb = cb[idx] / max_cb if max_cb > 0 else 0
            node_mass[node_id] = math.sqrt(alpha * (norm_pr ** 2) + beta * (norm_cb ** 2))

        edge_weights = []
        for e in self.edge_indices:
            u, v = e['from'], e['to']
            if u in node_mass and v in node_mass:
                edge_weights.append(node_mass[u] + node_mass[v])
            else:
                edge_weights.append(0)

        if edge_weights:
            sorted_w = sorted(edge_weights)
            idx = int(len(sorted_w) * (threshold_percentile / 100.0))
            tau = sorted_w[idx] if idx < len(sorted_w) else 0
            backbone_edges = [self.edge_indices[i] for i, w in enumerate(edge_weights) if w >= tau]
            print(f"        [TR-PCI] Backbone Computed: Tau={tau:.4f} (Top {100 - threshold_percentile}%)")
            return node_mass, backbone_edges
        return node_mass, []


# ============================================================================
# 3. R-CSDA: Reverse Context-Aware Semantic Deviation Analysis (Enhanced)
# ============================================================================
class RCSDA_Engine:
    def __init__(self, num_hashes=64):
        self.num_hashes = num_hashes
        self.prime = 4294967311
        self.perms = []
        random.seed(42)
        for _ in range(num_hashes):
            self.perms.append((random.randint(1, self.prime - 1), random.randint(0, self.prime - 1)))

    def _tokenize(self, text, node_extra=None):
        s = str(text).lower().strip()
        tokens = []

        if s and s != 'none':
            if len(s) < 3:
                tokens.append(s)
            else:
                tokens.extend([s[i:i + 3] for i in range(len(s) - 2)])

        if node_extra:
            if node_extra.get('group') == 'net' or str(node_extra.get('id', '')).startswith('net_'):
                tokens.append("<<NETWORK_ACTIVITY>>")
                tokens.append("<<REMOTE_CONN>>")

            if node_extra.get('type') == 'Fileless Storage':
                tokens.append("<<MEMFD_EXECUTION>>")
                tokens.append("<<HIDDEN>>")

            if node_extra.get('attack_type') == 'Process Injection':
                tokens.append("<<INJECTION>>")
                tokens.append("<<PTRACE>>")

            if node_extra.get('risk') == 'SHELLCODE':
                tokens.append("<<RWX_MEMORY>>")

            # ==================================================
            # Additional semantic feature extraction
            # (no special visual treatment applied for these)
            # ==================================================
            if node_extra.get('risk') == 'PRIVESC':
                tokens.append("<<PRIV_ESCALATION>>")
                tokens.append("<<SETUID>>")

            if node_extra.get('action') == 'DELETE':
                tokens.append("<<FILE_DELETION>>")
                tokens.append("<<UNLINK>>")

        return list(set(tokens))

    def _compute_minhash(self, tokens):
        signature = [float('inf')] * self.num_hashes
        for t in tokens:
            h_val = int(hash(t) & 0xffffffff)
            for i, (a, b) in enumerate(self.perms):
                ph = (a * h_val + b) % self.prime
                if ph < signature[i]: signature[i] = ph
        return signature

    def trace_back_c2_paths(self, nodes, backbone_edges, auto_k=True, max_k=10):
        node_map = {n['id']: n for n in nodes}

        def get_semantics(nid):
            n = node_map.get(nid, {})
            extra = n.get('extra', {})

            # 1. Get the command line (may be long and include arguments).
            cmd_text = extra.get('cmd', '').strip()

            # 2. Get the process name / label (usually the file name, with the
            #    trailing PID stripped off after the newline).
            label_text = n.get('label', '').split('\n')[0].strip()

            # 3. Merge both.
            #    Join with a space so that when _tokenize builds 3-grams the
            #    result contains features from both the process name and the
            #    command line. The later set() call deduplicates repeated
            #    tokens, so a simple concatenation is the most robust choice.
            full_text = f"{label_text} {cmd_text}".strip()

            # Fall back to a default if the merged text is empty (very rare)
            # to avoid downstream errors.
            if not full_text:
                full_text = "unknown_process"

            return full_text

        rev_adj = {}
        for e in backbone_edges:
            u, v = e['from'], e['to']
            if v not in rev_adj: rev_adj[v] = []
            rev_adj[v].append(u)

        c2_candidates = []
        for n in nodes:
            if n.get('id', '').startswith('net_') or n.get('group') == 'net':
                if n['id'] in rev_adj:
                    c2_candidates.append(n['id'])

        print(f"        [R-CSDA] Found {len(c2_candidates)} potential C2 anchors.")

        if not c2_candidates: return [], set()

        scored_paths = []
        memo_sim = {}

        def get_similarity(u, v):
            k = (u, v)
            if k in memo_sim: return memo_sim[k]

            p_text = get_semantics(u)
            c_text = get_semantics(v)
            p_extra = node_map.get(u, {}).get('extra', {})
            c_extra = node_map.get(v, {}).get('extra', {})

            tokens_p = self._tokenize(p_text, node_extra=p_extra)
            tokens_c = self._tokenize(c_text, node_extra=c_extra)

            sig_p = self._compute_minhash(tokens_p)
            sig_c = self._compute_minhash(tokens_c)

            matches = sum(1 for k in range(self.num_hashes) if sig_p[k] == sig_c[k])
            res = matches / float(self.num_hashes)
            memo_sim[k] = res
            return res

        for c2_node in c2_candidates:
            queue = [(c2_node, [c2_node], 0.0)]
            max_depth = 12
            best_path_for_node = (0.0, [])

            while queue:
                curr, path, score = queue.pop(0)
                if len(path) > max_depth: continue

                parents = rev_adj.get(curr, [])
                if not parents:
                    if score > best_path_for_node[0]:
                        best_path_for_node = (score, list(path))
                    continue

                for p in parents:
                    if p in path: continue
                    sim = get_similarity(p, curr)
                    step_score = (1.0 - sim)
                    # Score boosting logic below:
                    curr_extra = node_map.get(curr, {}).get('extra', {})
                    curr_tokens = self._tokenize("", curr_extra)

                    # Whenever a high-risk syscall is detected, force a +1.0 boost.
                    if "<<RWX_MEMORY>>" in curr_tokens or "<<INJECTION>>" in curr_tokens or "<<MEMFD_EXECUTION>>" in curr_tokens:
                        step_score += 1.0
                    if curr == c2_node and sim < 0.3: step_score *= 2.0
                    queue.append((p, path + [p], score + step_score))

            if best_path_for_node[0] > 1.2:
                forward_path = best_path_for_node[1][::-1]
                scored_paths.append((best_path_for_node[0], forward_path))

        print(f"        [R-CSDA] Total paths evaluated: {len(scored_paths)}")

        scored_paths.sort(key=lambda x: x[0], reverse=True)
        final_paths = []

        if not scored_paths:
            return [], set()

        if auto_k:
            top_score = scored_paths[0][0]
            print(f"    [*] Smart-K Selection (Max Score: {top_score:.2f})")
            for i, (score, path) in enumerate(scored_paths):
                if len(final_paths) >= max_k: break
                if score < top_score * 0.6:
                    print(f"        [-] Dropped path #{i + 1} (Score {score:.2f} < 60% of max).")
                    break
                if i > 0:
                    prev_score = scored_paths[i - 1][0]
                    drop_ratio = (prev_score - score) / prev_score
                    if drop_ratio > 0.4:
                        print(f"        [-] Cutoff at path #{i + 1} (Significant drop: {drop_ratio * 100:.0f}%).")
                        break
                final_paths.append((score, path))
        else:
            final_paths = scored_paths[:3]

        final_nodes = set()
        final_edges = set()

        print("-" * 60)
        for i, (score, path) in enumerate(final_paths):
            entry_node = node_map.get(path[0])
            c2_node = node_map.get(path[-1])
            entry_txt = get_semantics(path[0])[:50]
            c2_txt = c2_node['label'].replace('\n', ' ')

            print(f"    [+] Path #{i + 1} (Score {score:.2f}):")
            print(f"        Entry: {entry_txt}...")
            print(f"        Dest : {c2_txt}")

            final_nodes.update(path)
            for j in range(len(path) - 1):
                final_edges.add((path[j], path[j + 1]))
        print("-" * 60)

        return list(final_nodes), final_edges


# ============================================================================
# 4. Log Parser
# ============================================================================
class ProvenancePublicDirect:
    def __init__(self, host_ip):
        self.host_ip = host_ip
        self.nodes = {}
        self.edge_map = {}

    def add_node(self, nid, label, group, shape='dot', border='solid', extra_data=None):
        if nid not in self.nodes:
            node = {'id': nid, 'label': label, 'group': group, 'shape': shape, 'extra': extra_data or {}}
            if border == 'dashed': node['shapeProperties'] = {'borderDashes': [5, 5]}
            self.nodes[nid] = node
        else:
            if extra_data:
                for k, v in extra_data.items():
                    if k not in self.nodes[nid]['extra']: self.nodes[nid]['extra'][k] = v

    def add_edge(self, src, dst, label, color="#555", style="solid", extra=None):
        key = (src, dst, label)
        if key not in self.edge_map:
            self.edge_map[key] = {
                'count': 1, 'color': color, 'style': style, 'extra': extra or {}
            }
        else:
            self.edge_map[key]['count'] += 1
            if extra: self.edge_map[key]['extra'].update(extra)

    def _id_proc(self, pid, cg):
        return f"p_{cg}_{pid}"

    def _id_file(self, name, cg):
        return f"f_{hash(name + str(cg))}"

    def ingest(self, fpath):
        count = 0
        skipped = 0
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip(): continue
                    try:
                        self.process_event(json.loads(line))
                        count += 1
                    except:
                        skipped += 1
            print(f"    [>] Ingested: {count} events (Skipped: {skipped})")
        except Exception as e:
            print(f"Error reading {fpath}: {e}")

    def process_event(self, ev):
        pid = ev.get('pid')
        ppid = ev.get('ppid')
        cg = ev.get('cgroup_id', 0)
        subtype = ev.get('subtype')
        comm = ev.get('comm', 'u')

        # Optional comm-based filtering (disabled by default):
        # FILTER_KEYWORDS = ["<process-a>", "<process-b>"]
        # for kw in FILTER_KEYWORDS:
        #     if kw in comm: return

        if not pid: return
        proc_id = self._id_proc(pid, cg)
        parent_id = self._id_proc(ppid, cg)

        raw_args = ev.get('args', '')
        if isinstance(raw_args, list): raw_args = " ".join([str(x) for x in raw_args])
        full_payload = f"{ev.get('cmd', '')} {raw_args}".strip()
        if not full_payload: full_payload = comm

        existing = self.nodes.get(proc_id)
        current_cmd = existing['extra'].get('cmd', '') if existing else ""
        final_cmd = full_payload if len(full_payload) > len(current_cmd) else current_cmd

        # 1. Basic node creation
        self.add_node(proc_id, f"{comm}\n{pid}", 'proc', 'dot', 'solid', {'pid': str(pid), 'cmd': final_cmd})

        if str(ppid) != "0":
            self.add_node(parent_id, f"PID {ppid}", 'proc', 'dot', 'solid', {'pid': str(ppid)})
            self.add_edge(parent_id, proc_id, "spawn")

        # 2. Threat behavior handling.
        #    Key point: also update the node attributes so the R-CSDA engine can
        #    read them back later.

        # --- Fileless Execution (MEMFD) ---
        if subtype == 'MEMFD':
            name = ev.get('name', 'unknown')
            # Note: src and dst are both proc_id, forming a self-loop.
            self.add_edge(proc_id, proc_id, f"MEMFD\n{name}", "#e67e22", "dashed",
                          {'type': 'Fileless Storage', 'name': name})
            self.add_node(proc_id, None, 'proc', None, None, {'type': 'Fileless Storage'})

        # --- Process Injection (PTRACE) ---
        elif subtype == 'INJECT':
            target = ev.get('target_pid')
            tid = self._id_proc(target, cg)
            self.add_node(tid, f"Target\n{target}", 'proc', 'dot', 'solid', {'pid': str(target)})
            self.add_edge(proc_id, tid, f"PTRACE", "#e74c3c", "dashed", {'attack_type': 'Process Injection'})
            # [FIX] Tag the node so tokenizer sees <<INJECTION>>
            self.add_node(proc_id, None, 'proc', None, None, {'attack_type': 'Process Injection'})

        # --- Shellcode Loading (RWX MMAP) ---
        elif subtype == 'MMAP':
            prot = ev.get('prot', '')
            if 'WRITE' in prot and 'EXEC' in prot:
                # Note: src and dst are both proc_id, forming a self-loop.
                self.add_edge(proc_id, proc_id, "RWX", "#e74c3c", "solid", {'risk': 'SHELLCODE'})
                self.add_node(proc_id, None, 'proc', None, None, {'risk': 'SHELLCODE'})

        # ======================================================================
        # Privilege Escalation (SETUID)
        # ======================================================================
        elif subtype == 'SETUID':
            target_uid = ev.get('target_uid')
            # Add a self-loop edge to represent the state change, using gold (#f39c12).
            self.add_edge(proc_id, proc_id, f"SETUID\nUID:{target_uid}", "#f39c12", "solid",
                          {'risk': 'PRIVESC', 'target_uid': target_uid})
            # Tag the node risk so R-CSDA can extract the feature.
            self.add_node(proc_id, None, 'proc', None, None, {'risk': 'PRIVESC'})

        # ======================================================================
        # Anti-Forensics / File Deletion (DELETE)
        # ======================================================================
        elif subtype == 'DELETE':
            fname = ev.get('filename')
            if fname:
                fid = self._id_file(fname, cg)
                # Make sure the file node exists.
                self.add_node(fid, fname.split('/')[-1], 'file', 'box', 'solid', {'path': fname})
                # Add the deletion edge, using a red dotted line (#c0392b, dotted).
                self.add_edge(proc_id, fid, "unlink", "#c0392b", "dotted", {'action': 'DELETE'})

        # --- File / Network Ops ---
        elif subtype == 'OPEN':
            fname = ev.get('filename')
            if fname:
                fid = self._id_file(fname, cg)
                self.add_node(fid, fname.split('/')[-1], 'file', 'box', 'solid', {'path': fname})
                self.add_edge(proc_id, fid, "open")
        elif subtype == 'CONNECT':
            dst = ev.get('dst_ip')
            if dst:
                nid = f"net_{dst}"
                self.add_node(nid, dst, 'net', 'diamond', 'solid', {'ip': dst})
                self.add_edge(proc_id, nid, "connect", "#555", "dashed")

    def fold_files(self, max_files_per_dir=5):
        dir_map = {}
        for nid, node in self.nodes.items():
            if node['group'] == 'file':
                path = node['extra'].get('path', '')
                if path:
                    directory = os.path.dirname(path)
                    if directory not in dir_map: dir_map[directory] = []
                    dir_map[directory].append(nid)
        new_edge_map = {}
        redirect_map = {}
        for directory, nids in dir_map.items():
            if len(nids) > max_files_per_dir:
                cluster_id = f"dir_{hash(directory)}"
                label = f"{directory}/*\n({len(nids)} files)"
                file_list = []
                for old_id in nids:
                    old_node = self.nodes.get(old_id)
                    if old_node:
                        fpath = old_node['extra'].get('path', old_node['label'])
                        file_list.append(fpath)
                self.add_node(cluster_id, label, 'file', 'box', 'dashed', {
                    'path': directory + "/*",
                    'file_list': file_list
                })
                self.nodes[cluster_id]['color'] = '#f1c40f'
                self.nodes[cluster_id]['size'] = 25
                for old_id in nids:
                    redirect_map[old_id] = cluster_id
                    if old_id in self.nodes: del self.nodes[old_id]

        for (src, dst, label), info in self.edge_map.items():
            new_src = redirect_map.get(src, src)
            new_dst = redirect_map.get(dst, dst)

            # =======================================================
            # Important:
            # Skip an edge only if folding turned it into a self-loop that was
            # NOT originally a self-loop. If src and dst were already equal
            # (e.g. RWX / MEMFD), keep it.
            # =======================================================
            if new_src == new_dst and src != dst:
                continue

            key = (new_src, new_dst, label)
            if key not in new_edge_map:
                new_edge_map[key] = info
            else:
                new_edge_map[key]['count'] += info['count']
        self.edge_map = new_edge_map

    def get_graph_data(self):
        final_nodes = list(self.nodes.values())
        final_edges = []
        for (src, dst, label), info in self.edge_map.items():
            edge = {
                'from': src, 'to': dst, 'label': label,
                'color': info['color'], 'font': {'size': 10, 'align': 'middle'},
                'extra': info.get('extra')
            }
            if info.get('style') == 'dashed': edge['dashes'] = True
            if src == dst: edge['smooth'] = {'type': 'curvedCW', 'roundness': 0.4}
            final_edges.append(edge)
        return final_nodes, final_edges


# ============================================================================
# 5. Orchestrator
# ============================================================================
class MultiSliceOrchestrator:
    def __init__(self, output_file, host_ip):
        self.output_file = output_file
        self.host_ip = host_ip
        self.snapshots = {}
        self.STYLE_CONFIG = {
            'proc': {'color': '#3498db', 'shape': 'dot'},
            'file': {'color': '#f1c40f', 'shape': 'box'},
            'net': {'color': '#2ecc71', 'shape': 'diamond'},
        }
        self.C_BACKBONE = "#00d2d3"

    def reduce_graph(self, nodes, edges, backbone_edges, must_keep_ids, max_nodes=1500):
        print(f"    [!] Graph Reduction Triggered: {len(nodes)} nodes -> Target < {max_nodes}")
        keep_ids = set()
        keep_ids.update(must_keep_ids)

        for e in edges:
            extra = e.get('extra', {})
            if extra.get('type') == 'Fileless Storage' or \
                    extra.get('attack_type') == 'Process Injection' or \
                    extra.get('risk') == 'SHELLCODE' or \
                    e.get('to', '').startswith('net_'):
                keep_ids.add(e['from'])
                keep_ids.add(e['to'])

        for e in backbone_edges:
            keep_ids.add(e['from'])
            keep_ids.add(e['to'])

        if len(keep_ids) < max_nodes:
            adj = {}
            for e in edges:
                u, v = e['from'], e['to']
                if u not in adj: adj[u] = []
                if v not in adj: adj[v] = []
                adj[u].append(v)
                adj[v].append(u)
            current_count = len(keep_ids)
            for kid in list(keep_ids):
                if current_count >= max_nodes: break
                neighbors = adj.get(kid, [])
                for nb in neighbors:
                    if nb not in keep_ids:
                        keep_ids.add(nb)
                        current_count += 1
                        if current_count >= max_nodes: break

        final_nodes = [n for n in nodes if n['id'] in keep_ids]
        final_edges = [e for e in edges if e['from'] in keep_ids and e['to'] in keep_ids]
        print(f"    [!] Reduction Complete: {len(final_nodes)} nodes, {len(final_edges)} edges.")
        return final_nodes, final_edges

    def apply_visual_styles(self, nodes, edges, backbone_edges, attack_path_nodes, attack_path_edges):
        bb_set = set((e['from'], e['to']) for e in backbone_edges)
        path_nodes_set = set(attack_path_nodes)
        path_edges_set = attack_path_edges

        # Colors
        C_TRACE_PATH = "#9b59b6"
        C_C2_NODE = "#ff0000"
        C_MEMFD = "#e67e22"
        C_THREAT = "#e74c3c"

        debug_memfd = 0
        debug_ptrace = 0
        debug_shellcode = 0

        # -------------------------------------------------
        # 1. Edge Styling
        # -------------------------------------------------
        for e in edges:
            src, dst = e['from'], e['to']
            extra = e.get('extra', {})

            # Reset to base style
            e['width'] = 1
            e['dashes'] = False
            e['color'] = {'color': '#444444', 'opacity': 0.1, 'inherit': False}

            # ========================================================
            # Force the size and curvature of self-loop edges (RWX / MEMFD).
            # ========================================================
            if src == dst:
                e['smooth'] = {
                    'enabled': True,
                    'type': 'curvedCW',
                    'roundness': 0.8  # Draw a nice semicircle
                }
                e['selfReferenceSize'] = 25
                e['selfReference'] = {
                    'size': 25,
                    'angle': 0.785,  # Place the loop at the top-right of the node (45 degrees)
                    'renderBehindTheNode': False
                }

            # Determine the action type
            edge_is_memfd = extra.get('type') == 'Fileless Storage'
            edge_is_ptrace = extra.get('attack_type') == 'Process Injection'
            edge_is_shellcode = extra.get('risk') == 'SHELLCODE'

            is_threat_line = (edge_is_memfd or edge_is_ptrace or edge_is_shellcode)

            if is_threat_line:
                e['width'] = 4
                e['inherit'] = False

                # Emphasize high-risk edge labels (white text, black outline)
                # and float them above the arc.
                e['font'] = {'color': '#ffffff', 'size': 12, 'strokeWidth': 2, 'strokeColor': '#000000', 'align': 'top'}

                if edge_is_memfd:
                    debug_memfd += 1
                    e['color'] = {'color': C_MEMFD, 'highlight': C_MEMFD, 'hover': C_MEMFD, 'inherit': False}
                    e['dashes'] = True
                elif edge_is_ptrace:
                    debug_ptrace += 1
                    e['color'] = {'color': C_THREAT, 'highlight': C_THREAT, 'hover': C_THREAT, 'inherit': False}
                    e['dashes'] = True
                elif edge_is_shellcode:
                    debug_shellcode += 1
                    e['color'] = {'color': C_THREAT, 'highlight': C_THREAT, 'hover': C_THREAT, 'inherit': False}
                    e['dashes'] = False
                continue

            # Traceback analysis path (thick purple line)
            if (src, dst) in path_edges_set:
                e['color'] = {'color': C_TRACE_PATH, 'highlight': C_TRACE_PATH, 'inherit': False}
                e['width'] = 4
                e['dashes'] = False
                e['arrows'] = {'to': {'scaleFactor': 1.2}}
                e['label'] = e.get('label', '') + "\n[Stealth Trace]"

            # Causal inference backbone (cyan dashed line)
            elif (src, dst) in bb_set:
                e['color'] = {'color': self.C_BACKBONE, 'opacity': 0.8, 'inherit': False}
                e['width'] = 1
                e['dashes'] = True

        print(
            f"    [DEBUG] Visual Styles: MEMFD={debug_memfd}, PTRACE={debug_ptrace}, SHELLCODE(RWX)={debug_shellcode}")

        # -------------------------------------------------
        # 2. Node Styling
        # -------------------------------------------------
        poi_count = 0

        for n in nodes:
            grp = n.get('group', 'proc')
            style = self.STYLE_CONFIG.get(grp, self.STYLE_CONFIG['proc'])

            n['shape'] = style['shape']
            n['color'] = {'background': style['color'], 'border': style['color']}
            n['borderWidth'] = 2
            n['shadow'] = False

            if n['id'] in path_nodes_set:
                poi_count += 1
                n['size'] = 30

                is_c2 = n.get('group') == 'net'
                if is_c2:
                    n['shape'] = 'diamond'
                    n['color']['background'] = C_C2_NODE
                    n['label'] = "Stealth C2 💀\n" + n['label']
                    n['extra']['poi_type'] = "Hidden C2 Sink"
                else:
                    n['color']['border'] = C_TRACE_PATH
                    n['color']['background'] = "#2c3e50"

                    if grp == 'file':
                        n['color']['background'] = "#f1c40f"

                    if "⭐" not in n['label']: n['label'] = "⭐ " + n['label']
                    n['extra']['poi_type'] = "Stealth Chain Node"

            if 'group' in n: del n['group']

        return poi_count

    def process_sequence(self, file_pattern):
        files = glob.glob(file_pattern)
        if not files:
            print(f"[-] No files matched: {file_pattern}")
            return

        for fpath in files:
            slice_name = os.path.basename(fpath)
            print(f"--> Processing {slice_name}...")
            start_time = time.time()

            builder = ProvenancePublicDirect(self.host_ip)
            builder.ingest(fpath)
            builder.fold_files(max_files_per_dir=5)

            nodes, edges = builder.get_graph_data()
            print(f"    [+] Initial Graph: {len(nodes)} nodes, {len(edges)} edges")

            backbone_edges = []
            attack_path_nodes = []
            attack_path_edges = set()

            if LEIDEN_AVAILABLE and len(nodes) > 0:
                print(f"    [*] Running TR-PCI...")
                tr_pci = TRPCI_Engine(nodes, edges)

                # 1. Compute Backbone as usual (to know what is "Normal/High-Traffic")
                node_masses, backbone_edges = tr_pci.compute_backbone()

                for n in nodes:
                    if n['id'] in node_masses: n['extra']['tr_pci_mass'] = node_masses[n['id']]

                # ==========================================================
                # MODIFICATION: Trace from NON-Causal Backbone (Stealth)
                # ==========================================================
                if backbone_edges:
                    rcsda = RCSDA_Engine()

                    # Create a set of IDs for backbone edges for filtering.
                    # Note: we rely on object identity via id() here.
                    # TRPCI returns references to the original edge dicts, so id() works.
                    bb_ids = set(id(e) for e in backbone_edges)

                    # Compute Non-Backbone Edges (The "Noise" or "Stealth" layer)
                    non_backbone_edges = [e for e in edges if id(e) not in bb_ids]

                    print(
                        f"    [!] Logic Inverted: Tracing using {len(non_backbone_edges)} NON-Backbone edges (Stealth Mode)")

                    if non_backbone_edges:
                        # Pass non_backbone_edges instead of backbone_edges
                        attack_path_nodes, attack_path_edges = rcsda.trace_back_c2_paths(nodes, non_backbone_edges,
                                                                                         auto_k=True)
                    else:
                        print("    [-] No non-backbone edges found. Skipping trace.")
                # ==========================================================

            if len(nodes) > 2000:
                nodes, edges = self.reduce_graph(nodes, edges, backbone_edges, attack_path_nodes)
                valid_ids = set(n['id'] for n in nodes)
                # Update backbone reference after reduction just in case
                backbone_edges = [e for e in backbone_edges if e['from'] in valid_ids and e['to'] in valid_ids]

            poi_count = self.apply_visual_styles(nodes, edges, backbone_edges, attack_path_nodes, attack_path_edges)

            if LEIDEN_AVAILABLE:
                print(
                    f"    [+] TR-PCI Backbone: {len(backbone_edges)} | Stealth Trace Nodes: {len(attack_path_nodes)} | POIs: {poi_count}")

            elapsed = time.time() - start_time
            print(f"    [+] Slice Completed in {elapsed:.2f}s")

            self.snapshots[slice_name] = {'nodes': nodes, 'edges': edges}

        self._finalize()

    def _finalize(self):
        json_out = json.dumps(self.snapshots)
        if not self.snapshots: json_out = "{}"
        html_out = HTML_TEMPLATE.replace('__SNAPSHOTS_JSON__', json_out)
        with open(self.output_file, 'w', encoding='utf-8') as f:
            f.write(html_out)
        print(f"[+] Dashboard Generated: {self.output_file}")


class ReportHandler(http.server.SimpleHTTPRequestHandler):
    """
    Custom handler: disable caching so the latest HTML is always served.
    """

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Expires', '0')
        super().end_headers()


def start_web_server(port, host_ip, filename):
    """Start the HTTP server."""
    # Bind to 0.0.0.0 to allow external access.
    bind_address = "0.0.0.0"

    print("=" * 60)
    print(f"    [🌐] WEB SERVER ONLINE")
    print(f"    [+] Binding to: {bind_address}:{port}")
    print(f"    [+] Access URL: http://{host_ip}:{port}/{filename}")
    print("    [!] Press Ctrl+C to stop the server")
    print("=" * 60)

    try:
        with socketserver.TCPServer((bind_address, port), ReportHandler) as httpd:
            httpd.serve_forever()
    except OSError as e:
        print(f"[-] Error: Port {port} is busy or permission denied. ({e})")
    except KeyboardInterrupt:
        print("\n[!] Server stopped.")


if __name__ == "__main__":
    # Configuration
    # Glob pattern for the eBPF audit log(s) to analyze.
    LOG_PATTERN = "./logs/audit_*.json"
    OUT_PATH = "tr-pci-rcsda.html"
    # Host/IP shown in the access URL. Override for your own environment.
    HOST_IP = "127.0.0.1"
    SERVER_PORT = 8000

    if len(sys.argv) > 1: LOG_PATTERN = sys.argv[1]

    # 1. Generate the report
    engine = MultiSliceOrchestrator(OUT_PATH, HOST_IP)
    engine.process_sequence(LOG_PATTERN)

    # 2. Start the web server to host the report.
    #    Only start it once the file has been successfully generated.
    if os.path.exists(OUT_PATH):
        start_web_server(SERVER_PORT, HOST_IP, OUT_PATH)
    else:
        print(f"[-] Error: {OUT_PATH} was not found. Server start aborted.")
