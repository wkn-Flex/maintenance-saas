<template>
  <div>
    <el-card shadow="never" class="filter-card">
      <el-form :inline="true">
        <el-form-item label="设备型号/编号">
          <el-input v-model="keyword" placeholder="请输入关键词" clearable style="width: 220px" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="getList">查询</el-button>
          <el-button @click="keyword = ''; getList()">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>设备列表</span>
          <el-button type="primary" @click="openDialog()"><el-icon><Plus /></el-icon>新增设备</el-button>
        </div>
      </template>

      <el-table :data="list" border v-loading="loading">
        <el-table-column prop="device_no" label="设备编号" width="160" />
        <el-table-column prop="model" label="设备型号" min-width="180" />
        <el-table-column prop="customer_name" label="所属客户" min-width="200" />
        <el-table-column prop="install_date" label="安装时间" width="120" />
        <el-table-column prop="warranty_expire" label="保修到期" width="120" />
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="scope">
            <el-button type="primary" link size="small" @click="openDialog(scope.row)">编辑</el-button>
            <el-popconfirm title="确定删除该设备吗？" @confirm="deleteItem(scope.row.id)">
              <template #reference>
                <el-button type="danger" link size="small">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="getList"
        />
      </div>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editId ? '编辑设备' : '新增设备'" width="500px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="设备编号" required>
          <el-input v-model="form.device_no" placeholder="如：SB202608001" />
        </el-form-item>
        <el-form-item label="设备型号" required>
          <el-input v-model="form.model" />
        </el-form-item>
        <el-form-item label="所属客户" required>
          <el-select v-model="form.customer_id" placeholder="请选择客户" style="width: 100%">
            <el-option v-for="c in customerList" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="安装时间">
          <el-date-picker v-model="form.install_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="保修到期">
          <el-date-picker v-model="form.warranty_expire" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '../utils/request'

const loading = ref(false)
const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const keyword = ref('')
const dialogVisible = ref(false)
const editId = ref(null)
const customerList = ref([])
const form = reactive({ device_no: '', model: '', customer_id: null, install_date: '', warranty_expire: '' })

const getList = async () => {
  loading.value = true
  try {
    const res = await request.get('/api/devices/list', { params: { page: page.value, page_size: pageSize.value, keyword: keyword.value } })
    list.value = res.data
    total.value = res.total
  } finally {
    loading.value = false
  }
}

const getCustomers = async () => {
  const res = await request.get('/api/customers')
  customerList.value = res.data
}

const openDialog = (row) => {
  if (row) {
    editId.value = row.id
    Object.assign(form, row)
  } else {
    editId.value = null
    Object.assign(form, { device_no: '', model: '', customer_id: null, install_date: '', warranty_expire: '' })
  }
  dialogVisible.value = true
}

const submitForm = async () => {
  if (!form.device_no || !form.model || !form.customer_id) {
    ElMessage.warning('请填写必填项')
    return
  }
  if (editId.value) {
    await request.put(`/api/devices/${editId.value}`, form)
    ElMessage.success('修改成功')
  } else {
    await request.post('/api/devices', form)
    ElMessage.success('新增成功')
  }
  dialogVisible.value = false
  getList()
}

const deleteItem = async (id) => {
  await request.delete(`/api/devices/${id}`)
  ElMessage.success('删除成功')
  getList()
}

onMounted(() => {
  getList()
  getCustomers()
})
</script>

<style scoped>
.filter-card { margin-bottom: 16px; }
.pagination { margin-top: 16px; display: flex; justify-content: flex-end; }
</style>
