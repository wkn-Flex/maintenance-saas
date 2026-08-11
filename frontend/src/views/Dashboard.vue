<template>
  <div v-loading="loading">
    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stat-row">
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-item">
            <div class="stat-info">
              <p class="stat-label">总工单</p>
              <p class="stat-value">{{ stats.total || 0 }}</p>
            </div>
            <el-icon size="40" color="#1890ff"><Tickets /></el-icon>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-item">
            <div class="stat-info">
              <p class="stat-label">待派单</p>
              <p class="stat-value" style="color: #ff4d4f">{{ stats.pending_dispatch || 0 }}</p>
            </div>
            <el-icon size="40" color="#ff4d4f"><Bell /></el-icon>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-item">
            <div class="stat-info">
              <p class="stat-label">处理中</p>
              <p class="stat-value" style="color: #faad14">{{ stats.processing || 0 }}</p>
            </div>
            <el-icon size="40" color="#faad14"><Loading /></el-icon>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-item">
            <div class="stat-info">
              <p class="stat-label">已完成</p>
              <p class="stat-value" style="color: #52c41a">{{ stats.finished || 0 }}</p>
            </div>
            <el-icon size="40" color="#52c41a"><CircleCheck /></el-icon>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20">
      <!-- 工单状态饼图 -->
      <el-col :span="12">
        <el-card shadow="never">
          <template #header>工单状态分布</template>
          <div ref="chartRef" style="height: 350px"></div>
        </el-card>
      </el-col>
      <!-- 待办工单 -->
      <el-col :span="12">
        <el-card shadow="never">
          <template #header>待处理工单</template>
          <el-table :data="todoList" size="small">
            <el-table-column prop="order_no" label="工单编号" width="160" />
            <el-table-column prop="customer_name" label="客户" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="scope">
                <el-tag size="small" :type="scope.row.status === '待派单' ? 'danger' : 'warning'">{{ scope.row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="创建时间" width="100" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import request from '../utils/request'

const loading = ref(false)
const stats = ref({})
const todoList = ref([])
const chartRef = ref(null)
let chartInstance = null

const initChart = () => {
  chartInstance = echarts.init(chartRef.value)
  const option = {
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    series: [
      {
        name: '工单状态',
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
        label: { show: false },
        emphasis: { label: { show: true, fontSize: 16, fontWeight: 'bold' } },
        data: stats.value.status_stats || []
      }
    ],
    color: ['#ff4d4f', '#faad14', '#1890ff', '#722ed1', '#52c41a', '#bfbfbf']
  }
  chartInstance.setOption(option)
}

const getStats = async () => {
  loading.value = true
  try {
    const res = await request.get('/api/dashboard/stats')
    stats.value = res.overview
    todoList.value = res.todo_list
    await nextTick()
    initChart()
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  getStats()
  window.addEventListener('resize', () => chartInstance?.resize())
})
</script>

<style scoped>
.stat-row {
  margin-bottom: 20px;
}
.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.stat-label {
  font-size: 14px;
  color: #909399;
  margin-bottom: 8px;
}
.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
}
</style>
