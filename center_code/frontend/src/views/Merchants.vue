<template>
  <div class="merchants-page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <h3>商家管理</h3>
          <el-button type="primary" @click="handleCreate">
            <el-icon><Plus /></el-icon>
            新建商家
          </el-button>
        </div>
      </template>

      <!-- 筛选条件 -->
      <div class="filters">
        <el-input
          v-model="filters.search"
          placeholder="搜索商家名称"
          style="width: 250px; margin-right: 10px;"
          clearable
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-select v-model="filters.status" placeholder="选择状态" clearable style="width: 150px; margin-right: 10px;">
          <el-option label="启用" value="active" />
          <el-option label="禁用" value="inactive" />
        </el-select>
        <el-button type="primary" @click="loadMerchants">查询</el-button>
        <el-button @click="resetFilters">重置</el-button>
      </div>

      <!-- 表格 -->
      <el-table :data="merchants" v-loading="loading" stripe style="width: 100%; margin-top: 20px;">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="merchant_name" label="商家名称" min-width="200" />
        <el-table-column prop="contact_person" label="联系人" width="120" />
        <el-table-column prop="contact_phone" label="联系电话" width="150" />
        <el-table-column prop="contact_email" label="邮箱" width="200" />
        <el-table-column prop="address" label="地址" min-width="200" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'">
              {{ row.status === 'active' ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ row.created_at ? new Date(row.created_at).toLocaleString('zh-CN') : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button link type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination">
        <el-pagination
          :current-page="pagination.page"
          :page-size="pagination.size"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>

    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="600px"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="120px">
        <el-form-item label="商家名称" prop="merchant_name">
          <el-input v-model="form.merchant_name" placeholder="请输入商家名称" />
        </el-form-item>
        <el-form-item label="联系人" prop="contact_person">
          <el-input v-model="form.contact_person" placeholder="请输入联系人" />
        </el-form-item>
        <el-form-item label="联系电话" prop="contact_phone">
          <el-input v-model="form.contact_phone" placeholder="请输入联系电话" />
        </el-form-item>
        <el-form-item label="邮箱" prop="contact_email">
          <el-input v-model="form.contact_email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="地址" prop="address">
          <el-input v-model="form.address" type="textarea" :rows="3" placeholder="请输入地址" />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-select v-model="form.status" placeholder="请选择状态" style="width: 100%;">
            <el-option label="启用" value="active" />
            <el-option label="禁用" value="inactive" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getMerchants, createMerchant, updateMerchant, deleteMerchant } from '../api/merchants'

const loading = ref(false)
const merchants = ref([])
const formRef = ref(null)

const filters = ref({
  search: '',
  status: ''
})

const pagination = ref({
  page: 1,
  size: 20,
  total: 0
})

const dialogVisible = ref(false)
const form = ref({
  id: null,
  merchant_name: '',
  contact_person: '',
  contact_phone: '',
  contact_email: '',
  address: '',
  status: 'active'
})

const rules = {
  merchant_name: [
    { required: true, message: '请输入商家名称', trigger: 'blur' },
    { min: 2, max: 50, message: '长度在 2 到 50 个字符', trigger: 'blur' }
  ],
  contact_email: [
    { type: 'email', message: '请输入正确的邮箱地址', trigger: 'blur' }
  ]
}

const dialogTitle = computed(() => {
  return form.value.id ? '编辑商家' : '新建商家'
})

const loadMerchants = async () => {
  try {
    loading.value = true
    const params = {
      search: filters.value.search || undefined,
      status: filters.value.status || undefined,
      limit: pagination.value.size,
      offset: (pagination.value.page - 1) * pagination.value.size
    }
    
    const response = await getMerchants(params)
    if (response.code === 200) {
      merchants.value = response.data.merchants
      pagination.value.total = response.data.total
    }
  } catch (error) {
    ElMessage.error('加载商家列表失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

const resetFilters = () => {
  filters.value = {
    search: '',
    status: ''
  }
  loadMerchants()
}

const handleSizeChange = (size) => {
  pagination.value.size = size
  pagination.value.page = 1
  loadMerchants()
}

const handlePageChange = (page) => {
  pagination.value.page = page
  loadMerchants()
}

const handleCreate = () => {
  form.value = {
    id: null,
    merchant_name: '',
    contact_person: '',
    contact_phone: '',
    contact_email: '',
    address: '',
    status: 'active'
  }
  dialogVisible.value = true
  // 重置表单校验
  if (formRef.value) {
    formRef.value.clearValidate()
  }
}

const handleEdit = (row) => {
  form.value = {
    id: row.id,
    merchant_name: row.merchant_name,
    contact_person: row.contact_person,
    contact_phone: row.contact_phone,
    contact_email: row.contact_email,
    address: row.address,
    status: row.status
  }
  dialogVisible.value = true
  // 重置表单校验
  if (formRef.value) {
    formRef.value.clearValidate()
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除该商家吗？删除后不可恢复。', '删除确认', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    const response = await deleteMerchant(row.id)
    if (response.code === 200) {
      ElMessage.success('删除成功')
      // 如果当前页只有一条数据且不是第一页，则跳转到上一页
      if (merchants.value.length === 1 && pagination.value.page > 1) {
        pagination.value.page--
      }
      loadMerchants()
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
      console.error(error)
    }
  }
}

const handleSubmit = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid, fields) => {
    if (valid) {
      try {
        const data = {
          merchant_name: form.value.merchant_name,
          contact_person: form.value.contact_person,
          contact_phone: form.value.contact_phone,
          contact_email: form.value.contact_email,
          address: form.value.address,
          status: form.value.status
        }
        
        let response
        if (form.value.id) {
          response = await updateMerchant(form.value.id, data)
        } else {
          response = await createMerchant(data)
        }
        
        if (response.code === 200 || response.code === 201) {
          ElMessage.success(form.value.id ? '更新成功' : '创建成功')
          dialogVisible.value = false
          loadMerchants()
        } else {
            ElMessage.error(response.message || (form.value.id ? '更新失败' : '创建失败'))
        }
      } catch (error) {
        ElMessage.error(error.message || (form.value.id ? '更新失败' : '创建失败'))
        console.error(error)
      }
    } else {
      console.log('error submit!', fields)
    }
  })
}

onMounted(() => {
  loadMerchants()
})
</script>

<style scoped>
.merchants-page {
  padding: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filters {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>
