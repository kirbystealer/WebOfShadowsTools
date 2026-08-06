<template>
  <div class="grid-container" ref="container" @scroll="onScroll">
    <div :style="{ height: totalHeight + 'px', position: 'relative' }">
      <div
        v-for="(item, i) in visibleItems"
        :key="item.uid"
        class="row"
        :class="{ selected: item.uid === selectedUid }"
        :style="{ transform: `translateY(${(start + i) * rowHeight}px)` }"
        @click="onRowClick(item)"
      >
        <div class="cell parent">{{ item.parent }}</div>
        <div class="cell type">{{ item.type }}</div>
        <div class="cell hash">{{ item.hash }}</div>
        <div class="cell name">{{ item.name }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";

const props = defineProps({
  items: { type: Array, default: () => [] },
  rowHeight: { type: Number, default: 32 },
  buffer: { type: Number, default: 5 },
  selectedUid: { type: String, default: null },
});

const emit = defineEmits(["select"]);

const container = ref(null);
const scrollTop = ref(0);
const height = ref(0);

function onScroll() {
  scrollTop.value = container.value.scrollTop;
}

function onRowClick(item) {
  emit("select", item);
}

onMounted(() => {
  height.value = container.value.clientHeight;
});

const totalHeight = computed(() => props.items.length * props.rowHeight);

const start = computed(() =>
  Math.max(0, Math.floor(scrollTop.value / props.rowHeight) - props.buffer),
);

const end = computed(() =>
  Math.min(
    props.items.length,
    Math.ceil((scrollTop.value + height.value) / props.rowHeight) +
      props.buffer,
  ),
);

const visibleItems = computed(() => props.items.slice(start.value, end.value));
</script>

<style scoped>
.grid-container {
  height: 100%;
  overflow-y: auto;
  font-family: monospace;
  font-size: 12px;
}

.row {
  position: absolute;
  left: 0;
  right: 0;
  height: 32px;

  display: grid;
  grid-template-columns: 120px 4em 10em 1fr;
  align-items: center;

  border-bottom: 1px solid #e5e7eb;
  cursor: pointer;
}

.row:hover {
  background: #f3f4f6;
}

.row.selected {
  background: #dbeafe;
}

.cell {
  padding: 0 8px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.parent {
  color: #6b7280;
}

.type {
  text-transform: uppercase;
  font-weight: 600;
}

.hash {
  color: #9ca3af;
}

.name {
  font-weight: 500;
}
</style>
