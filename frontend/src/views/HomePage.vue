<template>
  <div class="home-page">
    <div class="left-panel">
      <SubmitTask />
    </div>
    <div class="right-panel">
      <TaskList />
    </div>
  </div>
</template>

<script setup>
import SubmitTask from './SubmitTask.vue'
import TaskList from './TaskList.vue'
</script>

<style scoped>
.home-page {
  display: flex;
  height: calc(100vh - 60px); /* 减去 header 高度 */
  gap: 0;
}

.left-panel {
  width: 42%;
  background: #fff;
  border-right: 1px solid #e4e7ed;
  overflow-y: auto;
  padding: 16px;
}

.right-panel {
  width: 58%;
  background: #f5f7fa;
  overflow-y: auto;
  padding: 16px;
}
</style>