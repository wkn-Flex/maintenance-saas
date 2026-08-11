<template>
  <div v-loading="loading">
    <el-page-header @back="$router.back()" title="返回" content="工单详情" style="margin-bottom: 20px" />
    
    <el-row :gutter="20">
      <el-col :span="16">
        <el-card shadow="never">
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center">
              <div>
                <span style="font-size: 16px; font-weight: 500; margin-right: 10px">{{ orderInfo.order_no }}</span>
                <el-tag :type="statusType(orderInfo.status)">{{ orderInfo.status }}</el-tag>
                <el-tag :type="priorityType(orderInfo.priority)" style="margin-left: 8px">{{ orderInfo.priority }}优先级</el-tag>
              </div>
              <div>
                <el-button v-if="orderInfo.status === '待派单'" type="primary" @click="dispatchDialog = true">派单</el-button>
                <el-button v-if="nextActions.length" type="success" @click="showStatusDialog = true">更新状态</el-button>
              </div>
            </div>
          </template>

          <el-descriptions :column="2" border>
            <el-descriptions-item label="客户名称">{{ orderInfo.customer_name }}</el-descriptions-item>
            <el-descriptions-item label="联系人">{{ orderInfo.contact_person }} {{ orderInfo.customer_phone }}</el-descriptions-item>
            <el-descriptions-item label="设备编号">{{ orderInfo.device_no }}</el-descriptions-item>
            <el-descriptions-item label="设备型号">{{ orderInfo.device_model }}</el-descriptions-item>
            <el-descriptions-item label="故障类型">{{ orderInfo.fault_type }}</el-descriptions-item>
            <el-descriptions-item label="负责工程师">{{ orderInfo.engineer_name || '未分配' }}</el-descriptions-item>
            <el-descriptions-item label="客户地址" :span="2">{{ orderInfo.customer_address }}</el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ orderInfo.created_at }}</el-descriptions-item>
            <el-descriptions-item label="故障描述" :span="2">{{ orderInfo.description }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card shadow="never">
          <template #header>工单进度</template>
          <el-timeline>
            <el-timeline-item
              v-for="(item, index) in timeline"
              :key="index"
              :type="item.done ? 'success' : 'info'"
              :timestamp="item.time"
            >
              {{ item.name }}
            </el-timeline-item>
          </el-timeline>
        </el-card>
      </el-col>
    </el-row>

    <!-- 派单弹窗 -->
    <el-dialog v-model="dispatchDialog" title="分配工程师" width="450px">
      <el-radio-group v-model="engineerId">
        <el-radio v-for="e in engineerList" :key="e.id" :value="e.id" style="display: block; margin-bottom: 12px; padding: 10px; border: 1px solid #dcdfe6; border-radius: 4px">
          {{ e.name }}
        </el-radio>
      </el-radio-group>
      <template #footer>
        <el-button @click="dispatchDialog = false">取消</el-button>
        <el-button type="primary" @click="submitDispatch">确认派单</el-button>
      </template>
    </el-dialog>

    <!-- 更新状态弹窗 -->
    <el-dialog v-model="showStatusDialog" title="更新工单状态" width="400px">
      <p style="margin-bottom: 15px">当前状态：<el-tag>{{ orderInfo.status }}</el-tag></p>
      <el-select v-model="targetStatus" placeholder="请选择新状态" style="width: 100%">
        <el-option v-for="s in nextActions" :key="s" :label="s" :value="s" />
      </el-select>
      <template #footer>
        <el-button @click="showStatusDialog = false">取消</el-button>
        <el-button type="primary" @click="submitUpdateStatus">确认更新</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import request from '../utils/request'

const route = useRoute()
const loading = ref(false)
const orderInfo = ref({})
const engineerList = ref([])
const dispatchDialog = ref(false)
const showStatusDialog = ref(false)
const engineerId = ref(null)
const targetStatus = ref('')

// 状态流转顺序
const statusFlow = ['待派单', '待接单', '已接单', '维修中', '待验收', '已完成']
const transitionMap = {
  '待派单': ['待接单', '已取消'],
  '待接单': ['已接单', '已取消'],
  '已接单': ['维修中', '已取消'],
  '维修中': ['待验收', '已取消'],
  '待验收': ['已完成', '维修中'],
  '已完成': [],
  '已取消': []
}

const nextActions = computed(() => transitionMap[orderInfo.value.status] || [])

const timeline = computed(() => {
  const currentIndex = statusFlow.indexOf(orderInfo.value.status)
  const list = []
  statusFlow.forEach((s, i) => {
    list.push({
      name: s,
      done: i <= currentIndex && orderInfo.value.status !== '已取消',
      time: i <= currentIndex ? (i === 0 ? orderInfo.value.created_at : '') : ''
    })
  })
  if (orderInfo.value.status === '已取消') {
    list.push({ name: '已取消', done: true, time: '' })
  }
  return list
})

const getOrderDetail = async () => {
  loading.value = true
  try {
    const res = await request.get(`/api/orders/${route.params.id}`)
    orderInfo.value = res.data
  } finally {
    loading.value = false
  }
}

const getEngineers = async () => {
  const res = await request.get('/api/engineers')
  engineerList.value = res.data
}

const submitDispatch = async () => {
  if (!engineerId.value) {
    ElMessage.warning('请选择工程师')
    return
  }
  await request.post(`/api/orders/${route.params.id}/dispatch`, { engineer_id: engineerId.value })
  ElMessage.success('派单成功')
  dispatchDialog.value = false
  getOrderDetail()
}

const submitUpdateStatus = async () => {
  if (!targetStatus.value) {
    ElMessage.warning('请选择状态')
    return
  }
  await request.put(`/api/orders/${route.params.id}/status`, { status: targetStatus.value })
  ElMessage.success('状态更新成功')
  showStatusDialog.value = false
  getOrderDetail()
}

const statusType = (status) => {
  const map = { '待派单': 'danger', '待接单': 'warning', '维修中': 'primary', '待验收': 'info', '已完成': 'success', '已取消': 'info' }
  return map[status] || ''
}
const priorityType = (p) => ({ '高': 'danger', '紧急': 'danger', '中': 'warning', '低': 'info' }[p] || '')

onMounted(() => {
  getOrderDetail()
  getEngineers()
})
</script>
