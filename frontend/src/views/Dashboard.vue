<template>
  <div class="space-y-6">
    <DocumentList v-if="!selectedId" @ask="handleAsk" />
    <ChatPdfViewer
      v-else
      :documentId="selectedId"
      :path="selectedPath"
      @back="reset"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import DocumentList from '../components/DocumentList.vue'
import { useRoute, useRouter } from 'vue-router'
import ChatPdfViewer from '../components/ChatPdfViewer.vue'

const route = useRoute()
const router = useRouter()

const selectedId = computed(() => {
  const p = route.params.docId
  return (typeof p === 'string' && p !== 'undefined' && p !== 'null') ? p : ''
})
const selectedPath = computed(() => route.query.path as string || null)

const handleAsk = ({ documentId, path }: { documentId: string; path: string }) => {
  if (!documentId) return
  router.push({ path: `/dashboard/${documentId}`, query: { path } })
}

const reset = () => {
  router.push('/dashboard')
}
</script>
