<template>
  <div>
    <!-- 筛选栏 -->
    <el-card class="filter-card" shadow="never">
      <el-form :inline="true" :model="queryParams">
        <el-form-item label="工单状态">
          <el-select v-model="queryParams.status" placeholder="全部" clearable style="width: 150px">
            <el-option label="待派单" value="待派单" />
            <el-option label="待接单" value="待接单" />
            <el-option label="已接单" value="已接单" />
            <el-option label="维修中" value="维修中" />
            <el-option label="待验收" value="待验收" />
            <el-option label="已完成" value="已完成" />
            <el-option label="已取消" value="已取消" />
          </el-select>
        </el-form-item>
        <el-form-item label="故障类型">
          <el-select v-model="queryParams.faultType" placeholder="全部" clearable style="width: 150px">
            <el-option label="电气故障" value="电气故障" />
            <el-option label="机械故障" value="机械故障" />
            <el-option label="管路故障" value="管路故障" />
            <el-option label="定期保养" value="定期保养" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="getOrderList">查询</el-button>
          <el-button @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 表格卡片 -->
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>工单列表</span>
          <el-button type="primary" @click="createDialogVisible = true">
            <el-icon><Plus /></el-icon>新建工单
          </el-button>
        </div>
      </template>

      <el-table :data="orderList" border stripe v-loading="loading">
        <el-table-column prop="order_no" label="工单编号" width="160" />
        <el-table-column prop="customer_name" label="客户名称" min-width="180" />
        <el-table-column prop="device_no" label="设备编号" width="140" />
        <el-table-column prop="fault_type" label="故障类型" width="100" />
        <el-table-column prop="priority" label="优先级" width="80">
          <template #default="scope">
            <el-tag :type="priorityType(scope.row.priority)" size="small">{{ scope.row.priority }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="scope">
            <el-tag :type="statusType(scope.row.status)" size="small">{{ scope.row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="engineer_name" label="负责工程师" width="100">
          <template #default="scope">
            {{ scope.row.engineer_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160" />
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="scope">
            <el-button v-if="scope.row.status === '待派单'" type="primary" link size="small" @click="openDispatchDialog(scope.row)">派单</el-button>
            <el-button type="primary" link size="small" @click="$router.push(`/orders/${scope.row.id}`)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination">
        <el-pagination
          v-model:current-page="queryParams.page"
          v-model:page-size="queryParams.page_size"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @size-change="getOrderList"
          @current-change="getOrderList"
        />
      </div>
    </el-card>

    <!-- 新建工单弹窗 -->
    <el-dialog v-model="createDialogVisible" title="新建工单" width="600px">
      <el-form :model="createForm" label-width="100px">
        <el-form-item label="客户名称" required>
          <el-select v-model="createForm.customer_id" placeholder="请选择客户" style="width: 100%" @change="onCustomerChange">
            <el-option v-for="c in customerList" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="故障设备" required>
          <el-select v-model="createForm.device_id" placeholder="请先选择客户" style="width: 100%">
            <el-option v-for="d in deviceList" :key="d.id" :label="`${d.device_no} ${d.model}`" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="故障类型" required>
          <el-select v-model="createForm.fault_type" placeholder="请选择" style="width: 100%">
            <el-option label="电气故障" value="电气故障" />
            <el-option label="机械故障" value="机械故障" />
            <el-option label="管路故障" value="管路故障" />
            <el-option label="定期保养" value="定期保养" />
          </el-select>
        </el-form-item>
        <el-form-item label="优先级" required>
          <el-select v-model="createForm.priority" style="width: 100%">
            <el-option label="低" value="低" />
            <el-option label="中" value="中" />
            <el-option label="高" value="高" />
            <el-option label="紧急" value="紧急" />
          </el-select>
        </el-form-item>
        <el-form-item label="故障描述" required>
          <el-input v-model="createForm.description" type="textarea" :rows="3" placeholder="请描述故障现象" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitCreate" :loading="submitLoading">确定提交</el-button>
      </template>
    </el-dialog>

    <!-- 派单弹窗 -->
    <el-dialog v-model="dispatchDialogVisible" title="分配工程师" width="500px">
      <el-radio-group v-model="dispatchForm.engineer_id" class="engineer-list">
        <el-radio v-for="e in engineerList" :key="e.id" :value="e.id" class="engineer-item">
          {{ e.name }}
        </el-radio>
      </el-radio-group>
      <template #footer>
        <el-button @click="dispatchDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitDispatch" :loading="submitLoading">确认派单</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '../utils/request'

const loading = ref(false)
const submitLoading = ref(false)
const orderList = ref([])
const total = ref(0)
const customerList = ref([])
const deviceList = ref([])
const engineerList = ref([])

const queryParams = reactive({
  status: '',
  faultType: '',
  page: 1,
  page_size: 10
})

const createDialogVisible = ref(false)
const dispatchDialogVisible = ref(false)
const currentOrderId = ref(null)

const createForm = reactive({
  customer_id: null,
  device_id: null,
  fault_type: '',
  priority: '中',
  description: ''
})

const dispatchForm = reactive({
  engineer_id: null
})

// 获取工单列表
const getOrderList = async () => {
  loading.value = true
  try {
    const res = await request.get('/api/orders', { params: queryParams })
    orderList.value = res.data
    total.value = res.total
  } finally {
    loading.value = false
  }
}

// 重置筛选
const resetQuery = () => {
  queryParams.status = ''
  queryParams.faultType = ''
  queryParams.page = 1
  getOrderList()
}

// 获取下拉数据
const getBaseData = async () => {
  const [customers, engineers] = await Promise.all([
    request.get('/api/customers'),
    request.get('/api/engineers')
  ])
  customerList.value = customers.data
  engineerList.value = engineers.data
}

// 选择客户后加载设备
const onCustomerChange = async (customerId) => {
  createForm.device_id = null
  const res = await request.get('/api/devices', { params: { customer_id: customerId } })
  deviceList.value = res.data
}

// 提交新建工单
const submitCreate = async () => {
  if (!createForm.customer_id || !createForm.device_id || !createForm.fault_type || !createForm.description) {
    ElMessage.warning('请填写完整信息')
    return
  }
  submitLoading.value = true
  try {
    await request.post('/api/orders', createForm)
    ElMessage.success('工单创建成功')
    createDialogVisible.value = false
    Object.assign(createForm, { customer_id: null, device_id: null, fault_type: '', priority: '中', description: '' })
    getOrderList()
  } finally {
    submitLoading.value = false
  }
}

// 打开派单弹窗
const openDispatchDialog = (row) => {
  currentOrderId.value = row.id
  dispatchForm.engineer_id = null
  dispatchDialogVisible.value = true
}

// 提交派单
const submitDispatch = async () => {
  if (!dispatchForm.engineer_id) {
    ElMessage.warning('请选择工程师')
    return
  }
  submitLoading.value = true
  try {
    await request.post(`/api/orders/${currentOrderId.value}/dispatch`, dispatchForm)
    ElMessage.success('派单成功')
    dispatchDialogVisible.value = false
    getOrderList()
  } finally {
    submitLoading.value = false
  }
}

// 标签颜色
const statusType = (status) => {
  const map = {
    '待派单': 'danger',
    '待接单': 'warning',
    '已接单': 'primary',
    '维修中': 'primary',
    '待验收': 'info',
    '已完成': 'success',
    '已取消': 'info'
  }
  return map[status] || ''
}

const priorityType = (priority) => {
  const map = { '高': 'danger', '紧急': 'danger', '中': 'warning', '低': 'info' }
  return map[priority] || ''
}

onMounted(() => {
  getOrderList()
  getBaseData()
})
</script>

<style scoped>
.filter-card {
  margin-bottom: 16px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.pagination {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
.engineer-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.engineer-item {
  margin-right: 0;
  padding: 8px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
}
</style>
