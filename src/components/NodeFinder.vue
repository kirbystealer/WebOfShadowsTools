<script setup>
import { ref, watch } from "vue";

const filterExpression = defineModel();

const localFilter = ref(filterExpression.value ?? "");

let timeout;

watch(localFilter, (value) => {
  clearTimeout(timeout);

  timeout = setTimeout(() => {
    filterExpression.value = value;
  }, 300);
});

watch(filterExpression, (value) => {
  localFilter.value = value ?? "";
});
</script>

<template>
  <div class="controls">
    <h3>Filter Nodes</h3>

    <input v-model="localFilter" placeholder="Search nodes..." />
  </div>
</template>

<style scoped>
.controls {
  padding: 0 16px;
}
</style>
