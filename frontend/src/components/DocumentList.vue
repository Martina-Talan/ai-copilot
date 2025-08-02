<template>
  <div class="container py-4">
    <!-- Top bar -->
    <div class="d-flex align-items-center justify-content-between flex-wrap gap-3 header-topbar">
      <div class="d-flex align-items-center gap-2">
        <img src="/img/ai-logo.svg" alt="Logo" class="aiva-logo" />
        <span class="fw-bold aiva-accent">AIVA</span>
      </div>

      <!-- Search -->
      <form @submit.prevent class="search-form flex-grow-1 mx-3">
        <div class="input-group search-wrapper">
          <span class="input-group-text bg-white border-end-0">
            <i class="bi bi-search text-muted"></i>
          </span>
          <input
            type="text"
            class="form-control border-start-0 search-input"
            placeholder="Search"
          />
        </div>
      </form>

      <!-- Right buttons -->
      <div class="d-flex align-items-center gap-2">
        <button class="btn btn-upgrade px-3 py-2">
          <i class="bi bi-stars me-1"></i> Upgrade
        </button>
        <div class="btn btn-upgrade px-3 py-2 d-flex align-items-center gap-2">
          <span class="fw-semibold user-email">{{ userName }}</span>
          <i class="bi bi-chevron-down small"></i>
        </div>
      </div>
    </div>

    <h2 class="fw-bold mb-4 mt-5 fs-3 text-dark">All Files</h2>

    <!-- Upload Box -->
    <div class="upload-box border-dashed rounded text-center p-4 p-md-5 mb-5">
      <div class="d-flex flex-column align-items-center justify-content-center">
        <form @submit.prevent="handleUpload" class="d-inline-block">
          <label for="fileInput" class="upload-link d-inline-flex align-items-center gap-2 mb-3 fs-4">
            <i class="bi bi-upload upload-icon"></i>
            <span>Upload a file</span>
          </label>
          <input
            id="fileInput"
            type="file"
            accept="application/pdf"
            @change="handleFileChange"
            class="d-none"
          />
          <button
            type="submit"
            class="btn btn-primary d-none"
          >
            Upload
          </button>
        </form>

        <p class="text-muted file-types-text">PDF, DOCX, DOC, PPTX, PPT, or TXT</p>
        <p v-if="uploading" class="uploading-status mt-3 d-flex align-items-center gap-2">
          <div class="spinner-border text-custom custom-small" role="status">
            <span class="visually-hidden">Loading...</span>
          </div>
            <span class="uploading-text">Uploading file...</span>
        </p>

      </div>
    </div>


    <!-- File List -->
    <div class="row py-2 border-bottom fw-semibold">
      <div class="col-md-5">Name</div>
      <div class="col-md-3">Date created</div>
      <div class="col-md-3">Uploaded by</div>
      <div class="col-md-1 text-end"></div>
    </div>

    <div
      v-for="doc in documents"
      :key="doc.id"
      class="row align-items-center py-3 border-bottom file-row file-card"
    >

    <!-- Icon -->
    <div class="col-md-5 d-flex align-items-center gap-3">
      <i class="bi bi-file-earmark fs-4 text-custom"></i>

    <div>
      <p class="mb-1 file-name">{{ doc.filename }}</p>
    </div>
  </div>

  <!-- Datum -->
  <div class="col-md-3 text-muted small">
    {{ formatDate(doc.createdAt || doc.uploadedAt) }}
  </div>

  <!-- User-->
  <div class="col-md-3 d-flex align-items-center gap-2">
    <div class="d-flex flex-column">
      <span class="small text-muted">{{ userName }}</span>
    </div>
  </div>

  <!-- Ask/Delete -->
  <div class="col-md-1 text-end">
    <div class="d-flex justify-content-end align-items-center gap-2">
      <button
        class="btn btn-ask btn-sm"
        @click="$emit('ask', { id: doc.id, path: doc.path })"
      >
        Ask
      </button>
      <button
        class="btn btn-m text-custom"
        @click="handleDelete(doc.id)"
      >
        <i class="bi bi-trash"></i>
      </button>
    </div>
  </div>
</div>

  </div>
  <div
    class="modal fade"
    id="confirmDeleteModal"
    tabindex="-1"
    aria-labelledby="confirmDeleteModalLabel"
    aria-hidden="true"
  > 
  <div class="modal-dialog modal-dialog-centered">
    <div class="modal-content border-0">
      <div class="modal-header bg-custom text-white">
        <h5 class="modal-title" id="confirmDeleteModalLabel">Are you sure?</h5>
        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
      </div>
      <div class="modal-body">
        This action cannot be undone. Do you really want to delete this file?
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-cancel" data-bs-dismiss="modal">Cancel</button>
        <button type="button" class="btn btn-delete" @click="confirmDelete">Yes, delete</button>
      </div>
      </div>
    </div>
  </div>
</template>


<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { deleteDocument, getAllDocuments, uploadDocument } from '../api/document.api'
import { useUserStore } from '../store/user'
import { Modal } from 'bootstrap'
import { useChatStore } from '../store/chat'

const chatStore = useChatStore()

let deleteId = ref<number | null>(null)

function handleDelete(id: number) {
  deleteId.value = id
  const modalEl = document.getElementById('confirmDeleteModal')
  const modal = new Modal(modalEl!)
  modal.show()
}

async function confirmDelete() {
  if (deleteId.value !== null) {
    try {
      await deleteDocument(deleteId.value)
      chatStore.clearHistory(deleteId.value)
      await fetchDocuments()
    } catch (err) {
      console.error('Error:', err)
    }
  }
  deleteId.value = null
  const modalEl = document.getElementById('confirmDeleteModal')
  const modal = Modal.getInstance(modalEl!)
  modal?.hide()
}


const emit = defineEmits(['ask'])
const documents = ref<any[]>([])
const selectedFile = ref<File | null>(null)
const uploading = ref(false)

const userStore = useUserStore()

const userName = computed(() => userStore.username || '')

onMounted(fetchDocuments)

async function fetchDocuments() {
  documents.value = await getAllDocuments()
}

async function handleFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  if (input.files?.length) {
    selectedFile.value = input.files[0]
    await handleUpload()
  }
}

async function handleUpload() {
  if (!selectedFile.value) return
  try {
    uploading.value = true
    await uploadDocument(selectedFile.value)
    selectedFile.value = null
    await fetchDocuments()
  } catch (err) {
    console.error('Upload error:', err)
  } finally {
    uploading.value = false
  }
}

function formatDate(dateStr: string) {
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-GB', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}
</script>

<style scoped>
.text-custom {
  color: rgb(133, 102, 82);
}

.text-custom:hover {
  color: rgb(102, 82, 65);
}

.upload-box {
  border: 0.125rem dashed rgb(133, 102, 82);
  background-color: rgb(255, 255, 255);
  color: rgb(33, 37, 41);
  min-height: 15rem;
}

.upload-link {
  color: rgb(133, 102, 82);
  text-decoration: underline;
  cursor: pointer;
  font-weight: 600;
}

.upload-link:hover {
  color: rgb(102, 82, 65);
}

.upload-icon {
  font-size: 2rem;
}

.aiva-logo {
  height: 3rem;
  filter: invert(61%) sepia(39%) saturate(532%) hue-rotate(339deg) brightness(90%) contrast(85%);
}

.aiva-accent {
  color: rgb(133, 102, 82);
  font-size: 2rem;
}

.search-input {
  padding: 0.6rem 1rem;
  font-size: 1rem;
  border-radius: 0 0.5rem 0.5rem 0;
  border: 1px solid rgb(222, 226, 230);
  background-color: rgb(255, 255, 255);
  color: rgb(33, 37, 41);
}

.search-input:focus {
  outline: none; 
  box-shadow: none; 
}

.input-group-text {
  border-radius: 0.5rem 0 0 0.5rem;
  border: 1px solid rgb(222, 226, 230);
}

.btn-upgrade, .btn-ask {
  background-color: rgb(250, 236, 229);
  color: rgb(102, 51, 26);
  font-weight: 600;
  border: 1px solid rgb(240, 205, 185);
}

.btn-upgrade:hover, .btn-ask:hover {
  background-color: rgb(102, 51, 26);
  color: rgb(250, 236, 229);
  font-weight: 600;
  border: 1px solid rgb(240, 205, 185);
}

.file-name {
  font-size: 1rem;
  color: rgb(33, 37, 41);
}

.pdf-icon {
  width: 32px;
  height: auto;
}

.file-row {
  transition: background-color 0.2s ease;
}

.file-row:hover {
  background-color: #f9f9f9;
}

.file-name {
  word-break: break-all;
}

.spinner-border.text-custom {
  border-color: rgb(133, 102, 82) transparent rgb(133, 102, 82) transparent;
}

.spinner-border.custom-small {
  width: 1.2rem;
  height: 1.2rem;
  border-width: 0.15em;
}

.uploading-text {
  color: rgb(133, 102, 82);
  font-weight: 500;
  font-size: 1.2rem;
}

.btn-cancel {
  border: 1px solid rgb(179, 137, 110);
}

.btn-cancel:hover {
  border: 1px solid rgb(102, 51, 26);
}

.btn-delete {
  background-color: rgb(179, 137, 110);
  color: rgb(255, 255, 255);
  border: none;
}

.btn-delete:hover {
  background-color:rgb(102, 51, 26); 
  color: rgb(255, 255, 255);
  border: none;
}

/* Responsive */
@media (max-width: 768px) {
  .row.py-2.border-bottom.fw-semibold {
    display: none;
  }

  .header-topbar {
    flex-direction: column;
    align-items: stretch;
  }

  .search-form {
    width: 100%;
  }

}
</style>
