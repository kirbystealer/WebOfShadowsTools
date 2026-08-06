<template>
  <div ref="container" class="cy"></div>
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount } from "vue";
import cytoscape from "cytoscape";
import fcose from "cytoscape-fcose";

// import dagre from '@dagrejs/dagre'
import cytoscapeDagre from "cytoscape-dagre";

cytoscape.use(cytoscapeDagre);

cytoscape.use(fcose);

const props = defineProps({
  graph: {
    type: Object,
    default: null,
  },
});

const container = ref(null);

let cy = null;

defineExpose({
  getCy: () => cy,
});

const style = [
  {
    selector: ".container",
    style: {
      shape: "round-rectangle",
      "background-color": "#d1d5db",
      "background-opacity": 0.35,
      "border-width": 2,
      "border-color": "#6b7280",
      padding: 40,

      label: "data(displayLabel)",
      "font-size": 12,
      "font-weight": "bold",
      "text-valign": "top",
      "text-halign": "center",
    },
  },

  {
    selector: ".unknown",
    style: {
      "background-color": "#fef3c7",
      "border-color": "#d97706",
      "border-style": "dashed",
    },
  },

  {
    selector: ".file",
    style: {
      shape: "rectangle",
      width: 70,
      height: 45,

      label: "data(displayLabel)",
      "font-size": 9,
      "text-wrap": "wrap",
      "text-max-width": 65,
      "text-valign": "center",
      "text-halign": "center",

      "background-color": "#60a5fa",
      "border-width": 1,
      "border-color": "#1e40af",
    },
  },

  // TEX
  {
    selector: 'node[type="tex"]',
    style: {
      shape: "hexagon",
      "background-color": "#fbbf24",
    },
  },

  // MAT
  {
    selector: 'node[type="mat"]',
    style: {
      shape: "round-rectangle",
      "background-color": "#fb923c",
    },
  },

  // MESH
  {
    selector: 'node[type="mesh"]',
    style: {
      shape: "rectangle",
      "background-color": "#34d399",
    },
  },

  // ANIM
  {
    selector: 'node[type="anim"]',
    style: {
      shape: "diamond",
      "background-color": "#4ade80",
    },
  },

  // EFXB
  {
    selector: 'node[type="efxb"]',
    style: {
      shape: "star",
      "background-color": "#a78bfa",
    },
  },

  // FX + SANM
  {
    selector: 'node[type="fx"], node[type="sanm"]',
    style: {
      shape: "triangle",
      "background-color": "#c084fc",
    },
  },

  // SKEL + ASKL
  {
    selector: 'node[type="skel"], node[type="askl"]',
    style: {
      shape: "ellipse",
      "background-color": "#22d3ee",
    },
  },

  // MORH
  {
    selector: 'node[type="morh"]',
    style: {
      shape: "tag",
      "background-color": "#94a3b8",
    },
  },

  // FONT
  {
    selector: 'node[type="font"]',
    style: {
      shape: "ellipse",
      "background-color": "#e5e7eb",
    },
  },

  {
    selector: ".external",
    style: {
      opacity: 0.8,
      "border-style": "dashed",
    },
  },

  {
    selector: "edge",
    style: {
      width: 2,
      "curve-style": "bezier",
      "target-arrow-shape": "triangle",
      "line-color": "#94a3b8",
      "target-arrow-color": "#94a3b8",
    },
  },

  {
    selector: 'edge[refType="global"]',
    style: {
      "line-style": "dashed",
      "line-color": "#dc2626",
      "target-arrow-color": "#dc2626",
    },
  },
];

onMounted(() => {
  cy = cytoscape({
    container: container.value,
    elements: [],
    style,

    layout: {
      name: "preset",
    },

    hideEdgesOnViewport: true,
    textureOnViewport: true,
  });

  loadGraph();
});

watch(
  () => props.graph,
  () => loadGraph(),
);

function loadGraph() {
  if (!cy || !props.graph) return;

  cy.elements().remove();

  cy.add([...props.graph.nodes, ...props.graph.edges]);

  cy.layout({
    name: "dagre",

    rankDir: "TB", // top-to-bottom DAG
    ranker: "network-simplex",

    nodeSep: 50, // horizontal separation
    rankSep: 80, // vertical separation
    edgeSep: 20,

    animate: false,
  }).run();
}

onBeforeUnmount(() => {
  cy?.destroy();
});
</script>

<style scoped>
.cy {
  width: 100%;
  height: 100%;
}
</style>
