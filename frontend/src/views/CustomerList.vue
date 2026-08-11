<template>
  <div>
    <el-card shadow="never" class="filter-card">
      <el-form :inline="true">
        <el-form-item label="客户名称">
          <el-input v-model="keyword" placeholder="请输入客户名称" clearable style="width: 200px" />
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
          <span>客户列表</span>
          <el-button type="primary" @click="openDialog()"><el-icon><Plus /></el-icon>新增客户</el-button>
        </div>
      </template>

      <el-table :data="list" border v-loading="loading">
        <el-table-column prop="name" label="客户名称" min-width="200" />
        <el-table-column prop="contact_person" label="联系人" width="120" />
        <el-table-column prop="phone" label="联系电话" width="150" />
        <el-table-column prop="address" label="地址" min-width="250" />
        <el-table-column prop="device_count" label="设备数量" width="100" />
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="scope">
            <el-button type="primary" link size="small" @click="openDialog(scope.row)">编辑</el-button>
            <el-popconfirm title="确定删除该客户吗？" @confirm="deleteItem(scope.row.id)">
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

    <el-dialog v-model="dialogVisible" :title="editId ? '编辑客户' : '新增客户'" width="500px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="客户名称" required>
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="联系人" required>
          <el-input v-model="form.contact_person" />
        </el-form-item>
        <el-form-item label="联系电话" required>
          <el-input v-model="form.phone" />
        </el-form-item>
        <el-form-item label="地址" required>
          <el-input v-model="form.address" type="textarea" :rows="2" />
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
const form = reactive({ name: '', contact_person: '', phone: '', address: '' })

const getList = async () => {
  loading.value = true
  try {
    const res = await request.get('/api/customers/list', { params: { page: page.value, page_size: pageSize.value, keyword: keyword.value } })
    list.value = res.data
    total.value = res.total
  } finally {
    loading.value = false
  }
}

const openDialog = (row) => {
  if (row) {
    editId.value = row.id
    Object.assign(form, row)
  } else {
    editId.value = null
    Object.assign(form, { name: '', contact_person: '', phone: '', address: '' })
  }
  dialogVisible.value = true
}

const submitForm = async () => {
  if (!form.name || !form.contact_person || !form.phone || !form.address) {
    ElMessage.warning('请填写完整信息')
    return
  }
  if (editId.value) {
    await request.put(`/api/customers/${editId.value}`, form)
    ElMessage.success('修改成功')
  } else {
    await request.post('/api/customers', form)
    ElMessage.success('新增成功')
  }
  dialogVisible.value = false
  getList()
}

const deleteItem = async (id) => {
  await request.delete(`/api/customers/${id}`)
  ElMessage.success('删除成功')
  getList()
}

onMounted(() => getList())
</script>

<style scoped>
.filter-card { margin-bottom: 16px; }
.pagination { margin-top: 16px; display: flex; justify-content: flex-end; }
</style>
