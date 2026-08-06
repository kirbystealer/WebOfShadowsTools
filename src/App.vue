<script setup>
import { ref, watch, onMounted } from "vue";
import GraphCanvas from "./components/GraphCanvas.vue";
import NodeFinder from "./components/NodeFinder.vue";
import VirtualFileGrid from "./components/VirtualFileGrid.vue";

const graph = ref(null);
const graphRef = ref(null);
const selectedGraph = ref(null);
const selectedUid = ref(null);
const flatNodes = ref([]);
const filterExpression = ref("");

let toNodes = new Map();
let fromNodes = new Map();
let nodeMap = new Map();
let edgeMap = new Map();

const getCy = () => graphRef.value?.getCy();

const resetView = () => {
  const cy = getCy();
  cy.zoom(1);
  cy.pan({ x: 0, y: 0 });
};

const fitView = () => {
  getCy()?.fit();
};

const takeScreenshot = () => {
  const cy = getCy();
  const png = cy.png({ full: true, bg: "white" });

  const a = document.createElement("a");
  a.href = png;
  a.download = "graph.png";
  a.click();
};

function createToFromNodes(graph) {
  nodeMap = new Map(graph.value.nodes.map((n) => [n.data.id, n]));

  edgeMap = new Map(graph.value.edges.map((edge) => [edge.data.id, edge]));

  for (const e of graph.value.edges) {
    const { source, target } = e.data;

    if (!toNodes.has(source)) toNodes.set(source, []);
    toNodes.get(source).push(target);

    if (!fromNodes.has(target)) fromNodes.set(target, []);
    fromNodes.get(target).push(source);
  }
}

function createFlatNodes(graph, filterExpression) {
  // derive flat list once
  let flatNodes = graph.value.nodes.map((n) => [
    `${n.data.parent}/${n.data.id}`,
    {
      uid: `${n.data.parent}/${n.data.id}`,
      id: n.data.id,
      name: n.data.label,
      parent: n.data.parent ? n.data.parent.toUpperCase() : "NONE",
      type: n.data.type,
      classes: n.classes,
      hash: n.data.id.split(".")[0],
      container: n.data.parent || "none",
    },
  ]);

  flatNodes = Array.from(new Map(flatNodes).values());

  flatNodes = flatNodes
    .filter((n) => n.classes.includes("file"))
    .filter((n) => !n.id.includes("0x00000000"));

  if (filterExpression) {
    for (let p of filterExpression.split(/\s+/)) {
      flatNodes = flatNodes.filter(
        (n) => `${n.parent}.${n.name}.${n.uid}`.indexOf(p) != -1,
      );
    }
  }
  return flatNodes;
}

onMounted(async () => {
  const response = await fetch(`${import.meta.env.BASE_URL}data/graph.json`);
  graph.value = await response.json();
  createToFromNodes(graph);

  flatNodes.value = createFlatNodes(graph, undefined);
});

watch(filterExpression, (newFilter) => {
  // update/recalculate virtual grid nodes  
  flatNodes.value = createFlatNodes(graph, newFilter);
});

function selectNode(node) {
  selectedUid.value = node.uid;
  selectedGraph.value = generateNodeGraph(node.id);
}

function getToFrom(nodeId) {
  let to = toNodes.get(nodeId) || [];
  let from = fromNodes.get(nodeId) || [];
  return { to, from };
}

function generateNodeGraph(startId) {
  const nodes = new Map();
  const edges = new Map();

  let visited = new Set();
  let queue = [startId];

  while (queue.length) {
    const currentId = queue.shift();
    const node = nodeMap.get(currentId);
    visited.add(currentId);

    if (node) {
      nodes.set(currentId, node);
    }

    // nodes this node points to
    const targets = toNodes.get(currentId) || [];

    for (const targetId of targets) {
      if (!visited.has(targetId)) {
        queue.push(targetId);
      }

      const edgeId = `${currentId}->${targetId}`;
      const edge = edgeMap.get(edgeId);

      if (edge) {
        edges.set(edgeId, edge);
      }
    }
  }

  visited = new Set();
  queue = [startId];

  while (queue.length) {
    const currentId = queue.shift();
    const node = nodeMap.get(currentId);
    visited.add(currentId);

    console.log(currentId, node.data.id, node.data.label);
    if (node) {
      nodes.set(currentId, node);
    }

    // nodes that point to this node
    const sources = fromNodes.get(currentId) || [];

    for (const sourceId of sources) {
      if (!visited.has(sourceId)) {
        queue.push(sourceId);
      }

      const edgeId = `${sourceId}->${currentId}`;
      const edge = edgeMap.get(edgeId);

      if (edge) {
        edges.set(edgeId, edge);
      }
    }
  }

  return {
    nodes: Array.from(nodes.values()),
    edges: Array.from(edges.values()),
  };
}
</script>

<template>
  <div class="app">
    <aside class="sidebar">
      <NodeFinder v-model="filterExpression" />

      <VirtualFileGrid
        :items="flatNodes"
        :selected-uid="selectedUid"
        @select="selectNode"
      />
    </aside>

    <main class="graph-panel">
      <div class="graph-wrapper">
        <GraphCanvas ref="graphRef" :graph="selectedGraph" />
        <div class="graph-controls">
          <button @click="resetView">Reset</button>
          <button @click="fitView">Fit</button>
          <button @click="takeScreenshot">PNG</button>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.app {
  display: grid;
  grid-template-columns: 620px 1fr;
  height: 100vh;
  width: 100vw;
  gap: 12px;
  padding: 12px;
  box-sizing: border-box;
  background: #e5e7eb;
}

.sidebar {
  display: flex;
  flex-direction: column;

  height: 100%;
  min-height: 0;

  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: #ffffff;

  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.graph-panel {
  position: relative;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: #ffffff;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.graph-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
}

.graph-controls {
  position: absolute;
  top: 10px;
  right: 10px;
  display: flex;
  gap: 6px;
  z-index: 10;
}

.graph-controls button {
  background: rgba(30, 30, 30, 0.7);
  color: white;
  border: none;
  padding: 6px 8px;
  cursor: pointer;
}
</style>
