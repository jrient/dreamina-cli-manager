<!-- frontend/src/components/AccountSelector.vue -->
<template>
  <div class="account-selector">
    <el-select
      v-model="selectedId"
      placeholder="选择账号"
      style="width: 160px"
      @change="onAccountChange"
    >
      <el-option
        v-for="acc in accounts"
        :key="acc.id"
        :label="acc.id"
        :value="acc.id"
      />
    </el-select>
    <el-button
      :loading="loadingCredit"
      :disabled="!selectedId"
      text
      type="primary"
      @click="fetchCredit"
    >
      {{ credit !== null ? `余额: ${credit}` : '查询余额' }}
    </el-button>
  </div>
</template>

<script setup>
import { ref, onMounted, inject } from 'vue'
import { api } from '../api/index.js'
import { ElMessage } from 'element-plus'

// Inject the selected account ID provided by App.vue
const selectedId = inject('selectedAccountId')

const accounts = ref([])
const credit = ref(null)
const loadingCredit = ref(false)

onMounted(async () => {
  try {
    accounts.value = await api.listAccounts()
    if (accounts.value.length > 0) selectedId.value = accounts.value[0].id
  } catch (e) {
    ElMessage.error('加载账号失败: ' + e.message)
  }
})

function onAccountChange() {
  credit.value = null
}

async function fetchCredit() {
  if (!selectedId.value) return
  loadingCredit.value = true
  try {
    const res = await api.getCredit(selectedId.value)
    credit.value = res.credit
  } catch (e) {
    ElMessage.error('查询余额失败: ' + e.message)
  } finally {
    loadingCredit.value = false
  }
}
</script>

<style scoped>
.account-selector { display: flex; align-items: center; gap: 8px; }
</style>